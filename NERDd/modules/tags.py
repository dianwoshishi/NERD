"""
NERD module tags IP according to classification rules which are stored in configuration.
Module also responds to changes of relevant attributes and updates tags assigned to IP.
"""

from core.basemodule import NERDModule

import g
import common.config

from numbers import Number
import re
import logging
import datetime
import os
import jsonpath_rw

class Tags(NERDModule):
    """
    Tags module.
    It is responsible for parsing classification rule, info of each tag. 
    It automatically generates triggers (attributes whose update trigger this module) 
    and changes (attributes the method call may update). It is also responsible for 
    evaluating of classification rule for tags which may be added, updated or removed 
    according to updated attributes in entity record.

    Event flow specification:
    [ip] triggers are generated from configuration -> update_tags() -> changes are generated from configuration 
    """

    def __init__(self):
        self.log = logging.getLogger("Tags")
        #self.log.setLevel("DEBUG")
        
        tags_config_file = os.path.join(g.config_base_path, g.config.get("tags_config")) 
        self.config = common.config.read_config(tags_config_file)
        self.tags_config = self.config.get("tags", {})
        self.tags = {}
       
        # Parse each tag from configuration 
        for tag_id, tag_params in self.tags_config.items():
            tag = {}
            if "condition" not in tag_params:
                self.log.error("Tag \"{}\" doesn't have obligatory key \"condition\" in configuration -> skipping tag.".format(tag_id))
                continue
            
            condition = self.parse_condition(tag_params["condition"])
            if condition is None:
                self.log.error("Error occurred when parsing condition of tag \"{}\" -> skipping tag.".format(tag_id))
                continue
           
            if "info" in tag_params:
                info = self.parse_info(tag_params["info"])
                if info is None:
                    self.log.error("Error occured when parsing info of tag \"{}\" -> skipping tag.".format(tag_id))
                    continue
            else:
                info = None
            
            # create two-tuple from ASTs of tag condition and info and add it to dict
            self.tags[tag_id] = (condition,info)            
            self.log.debug("Tag \"{}\" has been parsed.".format(tag_id))

        self.log.info("{} tags have been parsed.".format(len(self.tags)))
        
        # Create mapping of attributes to list of tags which may be changed when attribute is updated
        # TODO: include variables from JSONPath expressions!!!
        self.triggers = {}
        for tag_id, tag_params in self.tags.items():
            # Get all attributes which have been parsed from tag condition 
            variables = tag_params[0].parser.variables
            for var in variables:
                if var in self.triggers:
                    self.triggers[var].append(tag_id)
                else:
                    self.triggers[var] = [tag_id]
            
        for var, tag_list in self.triggers.items():
            self.log.debug("Attribute {} will trigger evaluation of tags: {}.".format(var, tag_list))
        
        # Create list of attributes which may be changed by this module
        changes = []
        for tag_id, tag_params in self.tags.items():
            changes.append("tags." + tag_id + ".confidence")
            changes.append("tags." + tag_id + ".time_added")
            changes.append("tags." + tag_id + ".time_modified")
            if tag_params[1] is not None:
                changes.append("tags." + tag_id + ".info")
        self.log.debug("Tag module may update attributes: {}.".format(changes))
        

        attribute_triggers = list(self.triggers.keys())
        attribute_triggers.append("!refresh_tags")

        g.um.register_handler(
            self.update_tags,
            'ip',
            attribute_triggers,
            changes
        )

    def parse_condition(self, string):
        """
        Creates lexer, parser and interpreter for tag condition.

        Arguments:
        string -- tag condition

        Return:
        Interpreter if valid AST has been created otherwise returns None
        """
        
        lexer = Lexer(string)
        parser = Parser(lexer)
        interpreter = Interpreter(parser)
        if interpreter.ast is None:
            return None
        else:
            return interpreter

    def parse_info(self, string):
        """
        Creates lexer, parser and interpreter for tag info. Quotes are added to argument 
        so lexer will handle it as a string.

        Arguments:
        string -- tag info

        Return:
        Interpreter if valid AST has been created otherwise returns None
        """
        
        string = '"' + string + '"'
        lexer = Lexer(string)
        parser = Parser(lexer)
        interpreter = Interpreter(parser)
        if interpreter.ast is None:
            return None
        else:
            return interpreter
    
    def update_tags(self, ekey, rec, updates):
        """
        Get set of tags which may be updated according to attributes which triggered this call,
        evaluates their classification rules and if condition is met evaluates confidence and formats info.
        At the end tags dict in entity record is updated according to result of evaluation of each tag from 
        above mentioned set - new tags are added, old tags are either updated if condition is met and confidence 
        or info are changed or removed if condition is not met after attribute changes.  
	
        Arguments:
        ekey -- two-tuple of entity type and key, e.g. ('ip', '192.0.2.42')
        rec -- record currently assigned to the key
        updates -- list of all attributes whose update triggered this call and
                   their new values (or events and their parameters) as a list of
                   2-tuples: [(attr, val), (!event, param), ...]

        Return:
        List of update requests.
        """
        
        etype, key = ekey
        if etype != 'ip':
            return None

        # If event !refresh_tags is set, update all available tags
        refresh_all = False
        for attr,val in updates:
            if attr == "!refresh_tags":
                refresh_all = True
                break
         
        # Create set of tags which may be updated
        tags_for_update = set()
        if refresh_all:
            tags_for_update.update(self.tags.keys())
        else:
            for updated_attr,updated_val in updates:
                if not updated_attr.startswith("!") and updated_attr in self.triggers:
                    tags_for_update.update(self.triggers[updated_attr])
        self.log.debug("Updating tags for IP {}. Tags to be re-evaluated: {}.".format(key, tags_for_update))

        # Evaluate condition for each tag from set. Evaluate confidence and format info if condition is met.
        # Add two-tuple of confidence value and info to updated_tags dict if condition is met
        updated_tags = {}
        for tag_id in tags_for_update:
            condition, info = self.tags[tag_id]
            eval_value = condition.evaluate(rec)
            if condition.evaluate_logical(eval_value):
                eval_confidence = condition.evaluate_mathematical(eval_value)
                eval_info = info.evaluate(rec) if info is not None else None
                updated_tags[tag_id] = (eval_confidence, eval_info)
                self.log.debug("Tag {} satisfies condition for IP {} - confidence: {}, info: \"{}\".".format(tag_id, key, eval_confidence, eval_info))
            else:
                self.log.debug("Tag {} does not satisfy condition for IP {}.".format(tag_id, key))
        
        # Create appropriate update request for each tag which may be updated
        ret = []

        # Remove all obsolete tags if event !refresh_tags is set
        if refresh_all and "tags" in rec:
            for tag_id in rec["tags"]:
                if tag_id not in tags_for_update:
                    ret.append(('remove', 'tags.' + tag_id))
                    self.log.debug("Obsolete tag {} has been deleted from record for IP {}.".format(tag_id,key))

        for tag_id in tags_for_update:
            # Update confidence or info in entity record if these values has been changed, otherwise do nothing
            if tag_id in updated_tags and "tags" in rec and tag_id in rec["tags"]:
                if updated_tags[tag_id][0] != rec["tags"][tag_id]["confidence"] or rec["tags"][tag_id].get("info") != updated_tags[tag_id][1]:
                    ret.append(('set', 'tags.'+ tag_id + '.confidence', updated_tags[tag_id][0]))
                    if updated_tags[tag_id][1] is not None:
                        ret.append(('set', 'tags.' + tag_id + '.info', updated_tags[tag_id][1]))
                    ret.append(('set', 'tags.' + tag_id + '.time_modified', datetime.datetime.utcnow()))
                    self.log.debug("Tag {} has been updated in record for IP {}.".format(tag_id,key))
                else:
                    self.log.debug("Tag {} has been already added to record for IP {} and nothing changed.".format(tag_id,key))
            # Add new tag to entity record
            elif tag_id in updated_tags:
                ret.append(('set', 'tags.'+ tag_id + '.confidence', updated_tags[tag_id][0]))
                if updated_tags[tag_id][1] is not None:
                    ret.append(('set', 'tags.' + tag_id + '.info', updated_tags[tag_id][1]))
                time = datetime.datetime.utcnow()
                ret.append(('set', 'tags.' + tag_id + '.time_added', time))
                ret.append(('set', 'tags.' + tag_id + '.time_modified', time))
                self.log.debug("Tag {} is new for IP {} and has been added to record.".format(tag_id,key))
            # Remove tag which does not satisfy condition after attribute update
            elif "tags" in rec and tag_id in rec["tags"]:
                ret.append(('remove', 'tags.' + tag_id))
                self.log.debug("Tag {} has been deleted from record for IP {}.".format(tag_id,key))

        g.um.update(('ip', key), ret)
        return None

                
"""
Lexer
"""

# Lexem type
IDENT, NUMB, JSONPATH, STRING, PLUS, MINUS, TIMES, DIVIDE, LPAR, RPAR, EQ, NEQ, LT, GT, LTE, GTE, kwOR, kwAND,  kwNOT, kwIN, EOI, ERR = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
)

# Specification of character
LETTER, DOT, BACKTICK, NUMBER, WHITE_SPACE, NO_TYPE = (22, 23, 24, 25, 26, 27)

UNARY, IN, NOTIN = (28, 29, 30)

# Mapping of input word to lexem type
symbol_table = {"in": kwIN, "or": kwOR, "and": kwAND, "not": kwNOT}

# Mapping of lexem type to description of type
const_to_string = {IDENT: "attribute name", NUMB: "number", JSONPATH: "JSONPath", STRING: "string", PLUS: "plus sign", MINUS: "minus sign", TIMES: "times sign", DIVIDE: "divide sign", LPAR: "left parenthesis",
    RPAR: "right parenthesis", EQ: "equal sign", NEQ: "not equal sign", LT: "less than sign", GT: "greater than sign", LTE: "less than or equal sign", GTE: "greater than or equal sign",
    kwOR: "logical or", kwAND: "logical and", kwNOT: "NOT keyword", kwIN: "IN keyword", EOI: "end of input", ERR: "error state"
}

class Lexem:
    """
    Lexical element for purpose of parsing
    """
    def __init__(self, symbol_type, val = ""): 
        self.type = symbol_type
        self.val = val

class Lexer:
    """
    Lexer converts a sequence of characters into sequence of lexem (tokens) 
    """
    
    def __init__(self, string):
        self.string = string
        self.pos = 0
        self.read_input()
        
    def read_input(self):
        """
        Reads actual character from sequence and categorizes it
        """

        if len(self.string) <= self.pos:
             self.input = EOI
             return
        
        self.char = self.string[self.pos]
        
        if self.char.isalpha() or self.char == "_":
            self.input = LETTER

        elif self.char == ".":
            self.input = DOT

        elif self.char == "`":
            self.input = BACKTICK # used to mark JSONPath expressions

        elif self.char.isdigit():
            self.input = NUMBER
        
        elif self.char == " ":
            self.input = WHITE_SPACE
        
        else:
            self.input = NO_TYPE
        
        self.pos += 1

    def key_word(self, word):
        """
        Determines if word is keyword of identification of attribute.

        Arguments:
        word -- challenged word

        Return:
        Constant of corresponding keyword or IDENT constant 
        """
        
        if word in symbol_table:
            return symbol_table[word]
        else:
            return IDENT

    def read_lexem(self):
        """
        Reads unprocessed sequence and returns found lexem.
        Exception is thrown if non valid sequence of characters is detected.

        Return:
        Lexem
        """
        
        while self.input == WHITE_SPACE:
            self.read_input()
        
        if self.input == EOI:
            return Lexem(EOI)            
        
        elif self.char == "+":
            self.read_input()
            return Lexem(PLUS)
        
        elif self.char == "-":
            self.read_input()
            return Lexem(MINUS)
        
        elif self.char == "*":
            self.read_input()
            return Lexem(TIMES)
        
        elif self.char == "/":
            self.read_input()
            return Lexem(DIVIDE)
        
        elif self.char == "(":
            self.read_input()
            return Lexem(LPAR)
        
        elif self.char == ")":
            self.read_input()
            return Lexem(RPAR)
        
        elif self.char == "=":
            self.read_input()
            if self.char == "=":
                self.read_input()
                return Lexem(EQ)
        
        elif self.char == "!":
            self.read_input()
            if self.char == "=":
                self.read_input()
                return Lexem(NEQ)
        
        elif self.char == "<":
            self.read_input()
            if self.char == "=":
                self.read_input()
                return Lexem(LTE)
            return Lexem(LT)
        
        elif self.char == ">":
            self.read_input()
            if self.char == "=":
                self.read_input()
                return Lexem(GTE)
            return Lexem(GT)
        
        elif self.char == "'" or self.char == '"':
            double_quotes = True if self.char == '"' else False
            text = ""
            self.read_input()
            
            while not ((double_quotes is True and self.char == '"') or (double_quotes is False and self.char == "'") or self.input == EOI):
                text += self.char
                self.read_input()

            if self.input == EOI:
                raise Exception("Unexpected end of string")
            self.read_input()
            return Lexem(STRING, text)

        elif self.input == BACKTICK: # JSONPath - read all until second backtick
            expr = ""
            self.read_input()
            while not (self.input == BACKTICK or self.input == EOI):
                expr += self.char
                self.read_input()

            if self.input == EOI:
                raise Exception("Unexpected end of JSONPath expression")
            self.read_input()
            return Lexem(JSONPATH, expr)

        elif  self.input == LETTER:
            ident = self.char
            self.read_input()
            while self.input == LETTER or self.input == NUMBER or self.input == DOT:
                ident += self.char
                self.read_input()
            return Lexem(self.key_word(ident),ident)

        elif self.input == NUMBER or self.input == DOT:
            is_float = True if self.input == DOT else False
            num_string = self.char
            self.read_input()
            while self.input == NUMBER or self.input == DOT:
                if(self.input == DOT):
                    if is_float:
                        raise Exception("Not a valid number at pos {}".format(self.pos))
                    else:
                        is_float = True
                num_string += self.char
                self.read_input()
            number = float(num_string) if is_float else int(num_string) 
            return Lexem(NUMB,number)
        
        raise Exception("{}: syntax error on position {}".format(self.string, self.pos))

"""
AST

Tree representation of abstract syntactic structure created from condition and info
"""

class Expr:
    def eval(self, data):
        """
        Evaluates node according to given data and return evaluated value
        """
        pass

class Var(Expr):
    """
    Var node represents attribute.

    Supports subkeys (e.g. "foo.bar"), but not arrays.
    """
    
    def __init__(self,ident):
        self.ident = ident
    
    def eval(self, data):
        """
        Returns attribute content if attribute exists in provided data otherwise returns None.
        """
        
        key = self.ident
        while '.' in key:
            key,value = key.split('.',1)
            if key not in data:
                return None
            data = data[key]
            key = value
        if key not in data:
            return None
        else:
            return data[key]

class JSONPathExpr(Expr):
    """
    Represents a JSONPath expression. Returns a list of matching values.

    The expression must start with '$' (that's how it's recognized from attribute names).

    See python_json_path_rw_ext package for what exactly is supported in JSONPath.
    """

    def __init__(self,expr):
        #logging.getLogger("TagsInterpreter").info("JSONPathExpr: '{}'".format(expr))
        self.parsed_expr = jsonpath_rw.parse(expr)

    def eval(self, data):
        #logging.getLogger("TagsInterpreter").info("JSONPathExpr: '{}', eval on '{}'".format(self.parsed_expr, data))
        return [match.value for match in self.parsed_expr.find(data)]

class Numb(Expr):
    """
    Numb node represents number. 
    """

    def __init__(self,num):
        self.num = num
    
    def eval(self, data):
        """
        Returns number.
        """
        
        return self.num

class Bop(Expr):
    """
    Bop node represents binary operator. 
    """
    
    def __init__(self,op,left,right):
        self.op = op
        self.left = left
        self.right = right
    
    def eval_operand_to_logical(self, operand):
        if not isinstance(operand,bool):
            if isinstance(operand, Number):
                operand = False if operand == 0 else True
            else:
                operand = True if operand is not None else False
        return operand

    def eval(self, data):
        """
        Returns true/false based on binary operator. If there is None on left or right side and arithmetic operator is used
        it considers None as 0 or if there is string on left or right side of arithmetic operation it considers string as 1.
        """
        
        left_eval = self.left.eval(data)
        if self.op == kwAND:
            #Short circuit evaluation of AND
            left_eval = self.eval_operand_to_logical(left_eval)
            if left_eval is False:
                return False
            right_eval = self.eval_operand_to_logical(self.right.eval(data))
            return left_eval and right_eval
        elif self.op == kwOR:
            #Short circuit evaluation of OR
            left_eval = self.eval_operand_to_logical(left_eval)
            if left_eval is True:
                return True
            right_eval = self.eval_operand_to_logical(self.right.eval(data))
            return left_eval or right_eval
        
        right_eval = self.right.eval(data)
        if self.op in (PLUS, MINUS, TIMES, DIVIDE) and not isinstance(left_eval, Number):
            if left_eval is None:
                left_eval = 0
            elif left_eval == False:
                left_eval = 0
            else:
                left_eval = 1
        if self.op in (PLUS, MINUS, TIMES, DIVIDE) and not isinstance(right_eval, Number):
            if right_eval is None:
                right_eval = 0
            elif right_eval == False:
                right_eval = 0
            else:
                right_eval = 1
        try:
            if self.op == PLUS:
                return left_eval + right_eval
            elif self.op == MINUS:
                return left_eval - right_eval
            elif self.op == TIMES:
                return left_eval * right_eval
            elif self.op == DIVIDE:
                try:
                    return left_eval / right_eval
                except ZeroDivisionError:
                    return 0
            elif self.op == EQ:
                return left_eval == right_eval
            elif self.op == NEQ:
                return left_eval != right_eval
            elif self.op == LT:
                return left_eval < right_eval
            elif self.op == GT:
                return left_eval > right_eval
            elif self.op == LTE:
                return left_eval <= right_eval
            elif self.op == GTE:
                return left_eval >= right_eval
        except Exception:
            return False
class In(Expr):
    """
    In node represents membership operator ("in" and "not in"). 
    """
    
    def __init__(self,item,var,positive=True):
        self.item = item
        self.var = var
        self.positive = positive
    
    def eval(self, data):
        """
        Returns true if item is in list/set/dict or false if item is not in list/set/dict or exception has been thrown during evaluation.
        If evaluates "not in" keyword evaluation works in opposite way.
        """
        
        item_eval = self.item.eval(data)
        var_eval = self.var.eval(data)
        ret = None
        try:
            if self.positive:
                ret = item_eval in var_eval
            else:
                ret = item_eval not in var_eval
        except Exception:
            ret = False
        return ret 

class UnMinus(Expr):
    """
    UnMinus node represents unary minus. 
    """
    
    def __init__(self,expr):
        self.expr = expr
    
    def eval(self, data):
        """
        Returns minus value of expression. It considers None as 0 and string as 1. 
        """
        
        expr_eval = self.expr.eval(data)
        if not isinstance(expr_eval, Number):
            if expr_eval is not None:
                expr_eval = 1
            else:
                expr_eval = 0
        return -expr_eval

class UnNeg(Expr):
    """
    UnNeg node represents unary logical operator "not". 
    """
    
    def __init__(self,expr):
        self.expr = expr
    
    def eval(self, data):
        """
        Returns negated logical value.
        """
        
        expr_eval = self.expr.eval(data)
        return not expr_eval

class String(Expr): 
    """
    String node represents string. 
    """
    
    def __init__(self,string):
        self.string = string
        var_list = set(re.findall('\{(.*?)\}', self.string))
        self.variables = {}
        for var in var_list:
            self.variables[var] = Var(var)
           
    def eval(self, data):
        """
        Returns string with replaced attributes.
        """
        
        formatted_string = self.string
        for key,var in self.variables.items():
            res = var.eval(data)
            if res is not None:
                formatted_string = formatted_string.replace("{"+key+"}", str(res))
        return formatted_string

class UnCond(Expr):
    """
    UnCond node represents part of condition (part between logical operators) which does not have relational operator. 
    """
    
    def __init__(self,expr):
        self.expr = expr
    
    def eval(self, data):
        """
        Returns True/False. It considers 0, None and False as False, everything else if True. 
        """
        
        expr_eval = self.expr.eval(data)
        if expr_eval is True or expr_eval is False:
            return expr_eval
        elif expr_eval == 0 or expr_eval is None:
            return False
        else:
            return True

class Math(Expr):
    """
    Math node represents mathematical expression. 
    """
    
    def __init__(self,expr):
        self.expr = expr
    
    def eval(self, data):
        """
        Returns evaluated mathematical expression. If evaluated expression is not number it considers 
        everything else than None as 1 (None is 0).
        """
        
        expr_eval = self.expr.eval(data)
        if not isinstance(expr_eval, Number):
            if expr_eval is not None:
                expr_eval = 1
            else:
                expr_eval = 0
        return expr_eval

"""
Parser
"""

class Parser:
    """
    Takes sequence of lexems, checks correct syntax and builds AST.
    """
    
    def __init__(self, lexer):
        self.lexer = lexer
        self.variables = set() # List of all variables (json fields or paths to subfields) found in the condition
        self.symbol = self.read_lexem()

    def read_lexem(self):
        """
        Reads next lexem from lexer. If lexem type is variable, adds it to variables set
        """
        lexem = self.lexer.read_lexem()

        if lexem.type == IDENT:
            self.variables.add(lexem.val)
        if lexem.type == JSONPATH:
            # Add fields from JSONPaths to the list of variables/attributes that trigger re-evaluation of the condition
            # NOTE: JSONPath can be very complex, so we extract *only the top-level field name*.
            match = re.search(r'[a-zA-Z0-9_-]+', lexem.val) # find the first alphanumeric sequence (should work in all "normal" cases)
            if match:
                self.variables.add(match.group(0))
            else:
                logging.getLogger("TagsInterpreter").warning("Can't find any variable/attribute name in JSONPath '{}'. (Re)evaluation of the tag won't be hooked on any attribute update.")
        return lexem

    def error_comparison(self, s):
        raise Exception("Error in comparison - expected symbol is {}, but received {}".format(const_to_string[s], const_to_string[self.symbol.type]))
        
    def error_expansion(self, s):
        raise Exception("Error in expansion - expected symbol is {}, but received {}".format(const_to_string[s], const_to_string[self.symbol.type]))
    
    def comparison(self, s): # Check if the next lexem is the expeced one, if yes, return it (and load the next one)
        #logging.getLogger("TagsInterpreter").info("comparison {} {} (expected {} {})".format(self.symbol.type, const_to_string[self.symbol.type], s, const_to_string[s]))
        if self.symbol.type == s:
            if self.symbol.type == IDENT:
                ident = self.symbol.val
                self.symbol = self.read_lexem()
                return ident
            elif self.symbol.type == STRING:
                string = self.symbol.val
                self.symbol = self.read_lexem()
                return string
            elif self.symbol.type == NUMB:
                num = self.symbol.val
                self.symbol = self.read_lexem()
                return num
            elif self.symbol.type == JSONPATH:
                expr = self.symbol.val
                self.symbol = self.read_lexem()
                return expr
            else:
                self.symbol = self.read_lexem()
        else:
            self.error_comparison(s)

    def math_expr(self):
        return self.math_expr_rest(self.math_times())

    def math_expr_rest(self, du):
        if self.symbol.type == PLUS:
            self.symbol = self.read_lexem()
            return self.math_expr_rest(Bop(PLUS, du, self.math_times()))
        elif self.symbol.type == MINUS:
            self.symbol = self.read_lexem()
            return self.math_expr_rest(Bop(MINUS, du, self.math_times()))
        else:
            return du

    def math_times(self):
        return self.math_times_rest(self.operand())

    def math_times_rest(self, du):
        if self.symbol.type == TIMES:
            self.symbol = self.read_lexem()
            return self.math_times_rest(Bop(TIMES, du, self.operand()))
        elif self.symbol.type == DIVIDE:
            self.symbol = self.read_lexem()
            return self.math_times_rest(Bop(DIVIDE, du, self.operand()))
        else:
            return du

    def operand(self):
        if self.symbol.type == IDENT:
            ident = self.comparison(IDENT)
            return Var(ident)
        elif self.symbol.type == STRING:
            string = self.comparison(STRING)
            return String(string)
        elif self.symbol.type == JSONPATH:
            expr = self.comparison(JSONPATH)
            return JSONPathExpr(expr)
        elif self.symbol.type == NUMB:
            num = self.comparison(NUMB)
            return Numb(num)
        elif self.symbol.type == MINUS:
            self.comparison(MINUS)
            return UnMinus(self.operand())
        elif self.symbol.type == LPAR:
            self.comparison(LPAR)
            expr = self.cond_or() 
            self.comparison(RPAR)
            return expr
        else:
            self.error_expansion("Operand")
    
    def cond_or(self):
        return self.cond_or_rest(self.cond_and())

    def cond_or_rest(self, du):
        if self.symbol.type == kwOR:
            self.comparison(kwOR)
            return Bop(kwOR, du, self.cond_or_rest(self.cond_and()))
        else:
            return du
    
    def cond_and(self):
        return self.cond_and_rest(self.cond_part())

    def cond_and_rest(self, du):
        if self.symbol.type == kwAND:
            self.comparison(kwAND)
            return Bop(kwAND, du, self.cond_and_rest(self.cond_part()))
        else:
            return du
    
    def cond_part(self):
        #logging.getLogger("TagsInterpreter").info("CondPart begin")
        if self.symbol.type == kwNOT:
            self.comparison(kwNOT)
            return UnNeg(self.cond_part())
        left = self.math_expr()
        #logging.getLogger("TagsInterpreter").info("CondPart left={}".format(left))
        op = self.compare_operator()
        #logging.getLogger("TagsInterpreter").info("CondPart op={}".format(op))
        if op == UNARY:
            return left
        ret = None
        if op == NOTIN or op == IN:
            # right side can be identifier or JSONPath expression
            if self.symbol.type == IDENT:
                right = Var(self.symbol.val)
            elif self.symbol.type == JSONPATH:
                right = JSONPathExpr(self.symbol.val)
            else:
                raise Exception("Error in comparison - expected symbol is {} or {}, but received {}".format(const_to_string[IDENT], const_to_string[JSONPATH], const_to_string[self.symbol.type]))
            self.symbol = self.read_lexem()
            ret = In(left,right, True if op == IN else False)
        else:
            right = self.math_expr()
            ret = Bop(op, left, right)
        #logging.getLogger("TagsInterpreter").info("CondPart right={}".format(right))
        return ret
   
    def compare_operator(self):
        if self.symbol.type == EQ:
            self.symbol = self.read_lexem()
            return EQ
        elif self.symbol.type == NEQ:
            self.symbol = self.read_lexem()
            return NEQ
        elif self.symbol.type == LT:
            self.symbol = self.read_lexem()
            return LT
        elif self.symbol.type == GT:
            self.symbol = self.read_lexem()
            return GT
        elif self.symbol.type == LTE:
            self.symbol = self.read_lexem()
            return LTE
        elif self.symbol.type == GTE:
            self.symbol = self.read_lexem()
            return GTE
        elif self.symbol.type == kwNOT:
            self.symbol = self.read_lexem()
            if self.symbol.type != kwIN:
                self.error_expansion("keyword IN")
            self.symbol = self.read_lexem()
            return NOTIN
        elif self.symbol.type == kwIN:
            self.symbol = self.read_lexem()
            return IN
        else:
            return UNARY

    def parse(self):
        """
        This function is starting point for parsing.
        """
        
        ast = self.cond_or()
        self.comparison(EOI)
        return ast

"""
Interpreter
"""

class Interpreter:
    """
    Starts parsing process, holds AST and evaluates it.
    """
    
    def __init__(self, parser):
        self.parser = parser
        self.ast = None
        self.log = logging.getLogger("TagsInterpreter")
        #self.log.setLevel("DEBUG")
        
        try:
            self.ast = self.parser.parse()
        except Exception as e:
            self.log.error("{}: {}".format(self.parser.lexer.string, e))

    def evaluate(self, data):
        """
        Starts evaluation. 

        Arguments:
        data -- entity record which is used for evaluation

        Return:
        Evaluated value as is if AST exists otherwise returns None
        """

        if self.ast is None:
            return None
        return self.ast.eval(data)
    
    def evaluate_logical(self, evaluated_value):
        """
        Returns False if evaluated value is False, None or 0 otherwise returns True 

        Arguments:
        evaluated_value -- value which has been evaluated by evaluate function

        Return:
        True or False
        """
        
        if evaluated_value is None or evaluated_value == False or evaluated_value == 0 or evaluated_value == []:
            return False
        else:
            return True

    def evaluate_mathematical(self, evaluated_value):
        """
        Returns evaluated value if it is number or 0 if evaluated value is False/None 
        or 1 if evaluated value is True/not None 

        Arguments:
        evaluated_value-- value which has been evaluated by evaluate function

        Return:
        Number
        """

        if evaluated_value is None or evaluated_value == False:
            return 0
        elif not isinstance(evaluated_value, Number) or evaluated_value == True:
            return 1
        else:
            return evaluated_value
