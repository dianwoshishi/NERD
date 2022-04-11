"""
NERD module for getting data from OTXv2 API.

Note: Base URL can also be https://otx.alienvault.com/api, it seems to be completely equivalent
"""

from core.basemodule import NERDModule
import g

import requests
import logging
import json
import threading

from OTXv2 import OTXv2
from common.otx_utils import ip


#otx_api_lock = threading.Lock()

OTX_SERVER = 'https://otx.alienvault.com/'
class OTX(NERDModule):
    """
    NERD class for getting data from DShield API.
    """

    def __init__(self):
        self.log = logging.getLogger('OTX')
        #self.log.setLevel("DEBUG")

        self.apikey = g.config.get('otx_api_key', None)
        self.otx = OTXv2(self.apikey, server=OTX_SERVER)

        g.um.register_handler(
            self.set_otx_general,  # function (or bound method) to call
            'ip',                # entity type
            ('!NEW', '!every1d'), # tuple/list/set of attributes to watch (their update triggers call of the registered method)
            ('otx.relate_pulses',)    # tuple/list/set of attributes the method may change
        )

    def set_otx_general(self, ekey, rec, updates):
        """
        Gets data from DShield api, parses them and returns them.
        """

        etype, key = ekey

        if etype != 'ip':
            return None

        self.log.debug("Querying OTX for {}".format(key))
        relate_pulses = []
        try:
#            with otx_api_lock:
            relate_pulses= ip(self.otx, key)
        except Exception as e:
            self.log.error("Error occured in OTX {}".format(e))
            return None
        if relate_pulses == []:
            return None
        return [('set', 'otx.relate_pulses', relate_pulses)]
