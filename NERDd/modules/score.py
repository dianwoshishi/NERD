"""
NERD module summarizing all information about an entity into its 
score. (first prototype version)

Should be triggered at least once a day for every address.

author: Wang Ming(dianwoshishi.sina.com)
"""

from core.basemodule import NERDModule
import g
import logging
import math

import datetime


def nonlin(val, coef=0.5, max=10000):
    """Nonlinear transformation of [0,inf) to [0,1)"""
    value = math.log2(val + 1)
    if value > max:
        return 1.0
    else:
        return (1 - coef**value)


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
        self.log = logging.getLogger("Scoremodule")
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
        
        # if 'dshield' not in rec:
        #     return None # No dshield record, nothing to do
        scores = []
        if "dshield" in rec:
            dshield_score = self.dshield(rec['dshield'])
            scores.append(dshield_score)
        else:
            scores.append(0)

        if "bl" in rec:
            bl_score = self.blacklist(rec['bl'])
            scores.append(bl_score)
        else:
            scores.append(0)

        if "otx" in rec:
            if "relate_pulses" in rec['otx']:
                otx_score = self.otx(rec['otx']['relate_pulses'])
                scores.append(otx_score)
            else:
                scores.append(0)
        else:
            scores.append(0)
        
        # if 'shodan' in rec:
        #     shodan_score = self.shodan(rec['shodan'])
        #     scores.append(shodan_score)
        # else:
        #     scores.append(0) 
        if len(scores) == 0:
            return None
        rep = sum(scores)/len(scores)


        actions = []
        actions.append(('set', 'rep', rep))

        data_date = datetime.datetime.utcnow() - datetime.timedelta(days=1) # Downloaded data dump comes from the previous day
        date_str = data_date.strftime("%Y-%m-%d")
        actions.append(('array_upsert', 'rep_history', {'date' : date_str},
                                        [ ('set', 'reputation', rep)  ]))
        # return actions

        g.um.update(("ip", key), actions)
        return None

    # decay function: decay with the time
    def decay(self, delta):
        return 2 ** (-1 * (delta)/self.decay_factor)

    def convert2datetime(self, stime):
        if not stime:
            return None
        return datetime.datetime.strptime(stime,'%Y-%m-%d').date()
    
    def convert2string(self, dtime):
        return dtime.strftime('%Y-%m-%d')
    
    def date_delta_days(self, today, target):
        return (today - target).days

    def shodan(self, data):
        today = datetime.datetime.utcnow().date()
        count = 0
        for tags in data.keys():
            count += 1
        
        rep = 1 - 1/(count+1)
        # self.log.info(f"otx:{rep}")
        return rep 


    def blacklist(self, data):
        today = datetime.datetime.utcnow().date()
        s7days = datetime.timedelta(days=7)
        DATE_RANGE = 7
        num_events = [0 for _ in range(DATE_RANGE)]
        date_set = [today - datetime.timedelta(days=i) for i in range(DATE_RANGE)]
        for bl in data:
            name = bl['n']
            for date in bl['h']:
                date = date.strftime("%Y-%m-%dT%H:%M:%S")
                date = datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))
                d = (today - date).days
                if d >= DATE_RANGE:
                    continue

                num_events[d] += 1

             # Compute reputation score
            sum_weight = 0
            rep = 0
            for d in range(0,DATE_RANGE):
                # reputation at day 'd'
                daily_rep = nonlin(num_events[d]) 
                # total reputation as weighted average with linearly decreasing weight
                weight = float(DATE_RANGE - d) / DATE_RANGE
                sum_weight += weight
                rep += daily_rep * weight
            rep /= sum_weight


            # self.log.info(f"bl:{rep}")   
            return rep
    
    def decay2(self, x):
        return x/(x+15)

    def otx(self, data):
        today = datetime.datetime.utcnow().date()
        reps = []
        max_sub = 0
        for pulse in data:
            try:

                date = datetime.datetime.strptime(pulse['modified'], '%Y-%m-%dT%H:%M:%S.%f').date()
            except Exception as e:
                date = datetime.datetime.strptime(pulse['modified'], '%Y-%m-%dT%H:%M:%S').date()

            d = (today - date).days
            
            reps.append(self.decay2(d) * pulse['subscriber_count'])
            if pulse['subscriber_count'] > max_sub:
                max_sub = pulse['subscriber_count']
        


        rep = sum(reps)/(len(reps) * max_sub)        


        # self.log.info(f"otx:{rep}")
        return rep

    def dshield(self, data):
        today = datetime.datetime.utcnow().date()
        s7days = datetime.timedelta(days=7)
        DATE_RANGE = 7
        num_events = [0 for _ in range(DATE_RANGE)]
        date_set = [today - datetime.timedelta(days=i) for i in range(DATE_RANGE)]
        for day in data:
            date = day['date']
            date = datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))
            d = (today - date).days
            if d >= DATE_RANGE:
                continue

            num_events[d] += day["reports"]

        # Compute reputation score
        sum_weight = 0
        rep = 0
        for d in range(0,DATE_RANGE):
            # reputation at day 'd'
            daily_rep = nonlin(num_events[d]) 
            # total reputation as weighted average with linearly decreasing weight
            weight = float(DATE_RANGE - d) / DATE_RANGE
            sum_weight += weight
            rep += daily_rep * weight
        rep /= sum_weight


        # self.log.info(f"dshield:{rep}")
        # mindate = self.convert2datetime(data['mindate'])
        # maxdate = self.convert2datetime(data['maxdate'])
        # if mindate == None or maxdate == None:
        #     return 0
        # 
        # mindate_delta = self.date_delta_days(today, mindate)
        # maxdate_delta = self.date_delta_days(today, maxdate)
        
        # decay_score = self.decay(maxdate_delta)

        # last_days = mindate_delta -  maxdate_delta# last time 
        # if last_days < 0:
        #     last_days = -last_days
        # # self.log.info(f"{last_days}")

        # score = decay_score * math.log2(1+(reports/(last_days+1)))
        score = rep
        return score



