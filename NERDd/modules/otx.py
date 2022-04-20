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


"""
{
	'id': '5a64f74f0e543738c12bc973',
	'name': 'Webscanners with Bad Requests - HTTP Status 400 - 1/20/2018 thru current day',
	'description': 'Webscanners who&amp;amp;amp;#39;s requests resulted in HTTP Status code 400 due to WAF rules or LB parsing issues',
	'modified': '2022-04-20T03:45:17.938000',
	'created': '2018-01-21T20:25:51.668000',
	'tags': ['webscanner', 'bruteforce', 'badrequest', 'probing', 'webscan'],
	'references': [],
	'public': 1,
	'adversary': '',
	'targeted_countries': [],
	'malware_families': [],
	'attack_ids': [],
	'industries': [],
	'TLP': 'white',
	'cloned_from': None,
	'export_count': 1388,
	'upvotes_count': 0,
	'downvotes_count': 0,
	'votes_count': 0,
	'locked': False,
	'pulse_source': 'web',
	'validator_count': 0,
	'comment_count': 0,
	'follower_count': 0,
	'vote': 0,
	'author': {
		'username': 'david3',
		'id': '2807',
		'avatar_url': '/otxapi/users/avatar_image/media/avatars/david3/resized/80/fireball-dwf.jpg',
		'is_subscribed': False,
		'is_following': False
	},
	'indicator_type_counts': {
		'IPv4': 3231
	},
	'indicator_count': 3231,
	'is_author': False,
	'is_subscribing': None,
	'subscriber_count': 1078,
	'modified_text': '6 minutes ago ',
	'is_modified': True,
	'groups': [],
	'in_group': False,
	'threat_hunter_scannable': True,
	'threat_hunter_has_agents': 1,
	'related_indicator_type': 'IPv4',
	'related_indicator_is_active': 1
}
"""