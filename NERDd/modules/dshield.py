"""
NERD module for getting data from DShield API.

API documentation (with xml response example, but module uses json):
https://isc.sans.edu/api/#ip
XML: https://isc.sans.edu/api/ip/70.91.145.10
vs
JSON: https://isc.sans.edu/api/ip/70.91.145.10?json

Note: Base URL can also be https://www.dshield.org/api/, it seems to be completely equivalent
"""

from core.basemodule import NERDModule
import g

import requests
import logging
import json
import time
from datetime import datetime

from fake_useragent import UserAgent
from faker import Faker

BASE_URL = "https://isc.sans.edu/api"

class DShield(NERDModule):
    """
    NERD class for getting data from DShield API.
    """

    def __init__(self):
        self.log = logging.getLogger('DShield')
        # self.log.setLevel("DEBUG")
        self.fake = Faker()
        # User-Agent string (with contact info) to be sent with each API request, as required by API usage instructions
        # (see https://isc.sans.edu/api)
        self.user_agent = g.config.get('dshield.user_agent', None)
        # if not self.user_agent or "CHANGE_ME" in self.user_agent:
        #     self.log.warning("Missing mandatory configuration (user-agent), DShield module disabled.")
        #     return
        # count the success get count
        self.success_count = 0

        g.um.register_handler(
            self.set_dshield,  # function (or bound method) to call
            'ip',                # entity type
            ('!NEW', '!every1w'), # tuple/list/set of attributes to watch (their update triggers call of the registered method)
            ('dshield_total.reports',
             'dshield_total.targets',
             'dshield_total.mindate',
             'dshield_total.updated',
             'dshield_total.maxdate',
             'dshield_total.latest')    # latest update time
        )         

    def set_dshield(self, ekey, rec, updates):
        """
        Gets data from DShield api, parses them and returns them.
        """

        etype, key = ekey

        if etype != 'ip':
            return None

        # headers= {'user-agent':str(UserAgent().random + ", contact: {}".format(self.fake.ascii_company_email()))}
        #headers= {'user-agent':self.user_agent}
        try:
            headers= {'user-agent':str(UserAgent().random)}
            # get response from server
            response = requests.get(f"{BASE_URL}/ip/{key}?json", timeout=(1,3), headers=headers)
            self.log.debug(f"{BASE_URL}/ip/{key}?json  -->  '{response.text}'")
            if response.text.startswith("<html><body>Too Many Requests"):
                self.log.info(f"Can't get DShield data for IP {key}: Rate-limit exceeded")
                time.sleep(1)
                return None
            data = json.loads(response.content.decode('utf-8'))['ip']

            dshield_record = {
                'reports': 0,
                'targets': 0,
                'mindate': "",
                'updated': "",
                'maxdate': "",
                'latest':datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            }

            # server can return no values, if it has no record of this IP
            if data['count']:
                dshield_record['reports'] = data['count']
            if data['attacks']:
                dshield_record['targets'] = data['attacks']
            if data['mindate']:
                dshield_record['mindate'] = data['mindate']
            if data['maxdate']:
                dshield_record['maxdate'] = data['maxdate']
            if data['updated']:
                dshield_record['updated'] = data['updated']

            # # if some value is missing, DShield have no data for the IP (or the record is damaged), do not store
            # if not (dshield_record['reports'] and dshield_record['targets'] and dshield_record['mindate'] and dshield_record['maxdate'] and dshield_record['updated'] ):
            #     self.log.debug("No data in DShield for IP {}".format(key))
            #     return None

        except Exception as e:
            self.log.error(f"Can't get DShield data for IP {key}: {e}:{headers}:{self.success_count}")
            return None             # could be connection error etc.

        #self.log.debug("DShield record for IP {}: {}".format(key, dshield_record))
        self.success_count += 1

        
        g.um.update(('ip', key), [('set', 'dshield_total', dshield_record)])
        return None
