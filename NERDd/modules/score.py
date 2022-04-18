"""
NERD module summarizing all information about an entity into its 
score. (first prototype version)

Should be triggered at least once a day for every address.

author: Wang Ming(dianwoshishi.sina.com)
"""

from core.basemodule import NERDModule
import g
import math

import datetime


def nonlin(val, coef=0.5, max=20):
    """Nonlinear transformation of [0,inf) to [0,1)"""
    if val > max:
        return 1.0
    else:
        return (1 - coef**val)


class Score(NERDModule):
    """
    Module estimating score of IPs.
    
    TODO better description
    
    Event flow specification:
      !every1d -> estimate_reputation -> rep
    """
    # decay function's factor
    decay_factor = 1

    def __init__(self):
        g.um.register_handler(
            self.estimate_reputation, # function (or bound method) to call
            'ip', # entity type
            ('!NEW','!every1d','!refresh_rep'), # tuple/list/set of attributes to watch (their update triggers call of the registered method)
            ('rep',) # tuple/list/set of attributes the method may change
        )


    def estimate_reputation(self, ekey, rec, updates):
        """
        Handler function to compute the reputation.
        
        Simple method (first prototype):
        - take list of events from last 14 days
        - compute a "daily reputation" for each day as:
          - nonlin(num_of_events) * nonlin(number_of_nodes)
          - where nonlin is a nonlinear transformation: 1 - 1/2^x
        - get total reputation as weighted average of all "daily" ones with
          linearly decreasing weight (weight = (14-n)/14 for n=0..13)
        """
        etype, key = ekey
        if etype != 'ip':
            return None
        
        if 'dshield' not in rec:
            return None # No dshield record, nothing to do

        dshield_score = self.dshield(rec['dshield'])

        rep = dshield_score
        return [('set', 'rep', rep)]
    # decay function: decay with the time
    def decay(self, delta):
        return 2 ** (-1 * (delta)/self.decay_factor)

    def convert2datetime(self, stime):
        if not stime:
            return None
        return datetime.datetime.strptime(stime,'%Y-%m-%d').date()
    
    def date_delta_days(self, today, target):
        return (today - target).days

    def dshield(self, data):

        reports = data['reports']
        targets = data['targets']
        if reports == 0 or targets == 0:
            return 0

        mindate = self.convert2datetime(data['mindate'])
        maxdate = self.convert2datetime(data['maxdate'])
        if mindate == None or maxdate == None:
            return 0
        today = datetime.datetime.utcnow().date()
        mindate_delta = self.date_delta_days(today, mindate)
        maxdate_delta = self.date_delta_days(today, maxdate)
        
        decay_score = self.decay(maxdate_delta)

        last_days = maxdate_delta -  mindate_delta# last time 

        score = decay_score * math.log2((reports/targets))
        return score



