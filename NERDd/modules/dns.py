"""
NERD module resolving hostnames of IP addresses using reverse DNS queries.

Requirements:
- "dnspython" package
"""

from core.basemodule import NERDModule
import g

import logging
from dns import resolver,reversename
from dns.exception import *


class DNSResolver(NERDModule):
    """
    DNS resolver module.
    
    Reoslves newly added IP addresses to hostnames using reverse DNS queries
    (PTR records).
    
    Event flow specification:
      !NEW -> get_hostname -> hostname
    """
    
    def __init__(self):
        self.log = logging.getLogger("DNSResolver")
        self._resolver = resolver.Resolver()
        self._resolver.timeout = g.config.get('dns.timeout', 1)
        self._resolver.lifetime = 3 # Socket is open up to 3 seconds and will perform up to 3 queries in case of 1 second timeout occurence.

        g.um.register_handler(
            self.get_hostname, # function (or bound method) to call
            'ip', # entity type
            ('!NEW','!every1w'), # tuple/list/set of attributes to watch (their update triggers call of the registered method)
            ('hostname',) # tuple/list/set of attributes the method may change
        )
        
    
    def get_hostname(self, ekey, rec, updates):
        """
        Set a 'hostname' attribute as a result of DNS PTR query on the IP 
        address (key).
        If the hostname cannot be resolved (due to NXDOMAIN, timeout or other
        error), None is stored to 'hostname' attribute.
        
        Arguments:
        ekey -- two-tuple of entity type and key, e.g. ('ip', '192.0.2.42')
        rec -- record currently assigned to the key
        updates -- list of all attributes whose update triggered this call and  
          their new values (or events and their parameters) as a list of 
          2-tuples: [(attr, val), (!event, param), ...]
        
        Returns:
        List of update requests (3-tuples describing requested attribute updates
        or events).
        In particular, the following update is requested:
          ('set', 'hostname', hostname_or_none)
        """
        etype, key = ekey
        if etype != 'ip':
            return None
        
        addr = reversename.from_address(key) # create .in-addr.arpa address
        try:
            answer = self._resolver.query(addr,"PTR")
            result = str(answer.rrset[0]) # get first (it should be only) answer
            if result[-1] == '.':
                result = result[:-1] # trim trailing '.'
        except Timeout as e:
            self.log.debug("PTR query for {} timed out".format(key))
            result = None
        except DNSException as e:
            result = None # set result to None if NXDOMAIN, Timeout or other error
        
        g.um.update(('ip', key), [('set', 'hostname', result)])
        return None
        
