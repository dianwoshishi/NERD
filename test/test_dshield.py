"""
NERD module for getting data from DShield API.

API documentation (with xml response example, but module uses json):
https://isc.sans.edu/api/#ip
XML: https://isc.sans.edu/api/ip/70.91.145.10
vs
JSON: https://isc.sans.edu/api/ip/70.91.145.10?json

Note: Base URL can also be https://www.dshield.org/api/, it seems to be completely equivalent
"""



import requests
import logging
import json
from concurrent.futures import ThreadPoolExecutor

from fake_useragent import UserAgent

BASE_URL = "https://isc.sans.edu/api"

class DShield():
    """
    NERD class for getting data from DShield API.
    """

    def __init__(self):
    	pass

    def get_dshield(self, key):
        """
        Gets data from DShield api, parses them and returns them.
        """
        try:
            headers= {'user-agent':str(UserAgent().random)}
            # get response from server
            response = requests.get(f"{BASE_URL}/ip/{key}?json", timeout=(1,3), headers=headers)
            #self.log.debug(f"{BASE_URL}/ip/{key}?json  -->  '{response.text}'")
            if response.text.startswith("<html><body>Too Many Requests"):
                print(f"Can't get DShield data for IP {key}: Rate-limit exceeded")
                return None
            data = json.loads(response.content.decode('utf-8'))['ip']

            dshield_record = {
                'reports': 0,
                'targets': 0,
                'mindate': "",
                'updated': "",
                'maxdate': "",
            }
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

            print(key, json.dumps(dshield_record))

        except Exception as e:
            print(f"Can't get DShield data for IP {key}: {e}")
            return None             # could be connection error etc.

        
        return dshield_record



dshield = DShield()
with open("ip_tags.csv", "r") as f:
	with ThreadPoolExecutor(16) as pool:
		for line in f:
			line = line.strip().split(",")
			ip = line[0]
			pool.submit(dshield.get_dshield,ip)  
    

