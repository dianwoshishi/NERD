import requests
import json
import time
import logging 
import tqdm

import math

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s',
                    level=logging.INFO)

log = logging.getLogger('firehol')
log.setLevel("DEBUG")

def timestamp_datetime(value):
	value = value/1000
	format = "%Y-%m-%d %H:%M:%S"
    # value为传入的值为时间戳(×××)，如：1332888820
	value = time.localtime(value)
    ## 经过localtime转换后变成
    ## time.struct_time(tm_year=2012, tm_mon=3, tm_mday=28, tm_hour=6, tm_min=53, tm_sec=40, tm_wday=2, tm_yday=88, tm_isdst=0)
    # 最后再经过strftime函数转换为正常日期格式。
	dt = time.strftime(format, value)
	return dt
 
def datetime_timestamp(dt):
     #dt为字符串
     #中间过程，一般都需要将字符串转化为时间数组
     time.strptime(dt, '%Y-%m-%d %H:%M:%S')
     ## time.struct_time(tm_year=2012, tm_mon=3, tm_mday=28, tm_hour=6, tm_min=53, tm_sec=40, tm_wday=2, tm_yday=88, tm_isdst=-1)
     #将"2012-03-28 06:53:40"转化为时间戳
     s = time.mktime(time.strptime(dt, '%Y-%m-%d %H:%M:%S'))
     return int(s)


# get all ipset

blacklist_count = 0
base_url = 'http://iplists.firehol.org/'
class blacklist(object):
	
	def __init__(self, _id, _name, _descr, _firehol_link, _provider_link, _url, _time):
		self.id = _id
		self.name = _name.replace("\"", "").replace("\'", "")
		self.descr = _descr.replace("\"", "").replace("\'", "")
		self.firehol_link = _firehol_link
		self.provider_link = _provider_link
		self.url = _url
		self.time = _time

	def format_output(self):
		global blacklist_count
		blacklist_count += 1
		print(f"- id: {self.id}")
		print(f"  name: \'{self.name}\'")
		print(f"  descr: \'{self.descr}\'")
		print(f"  firehol_link: {self.firehol_link}")
		print(f"  provider_link: {self.provider_link}")
		print(f"  url: {self.url}")
		print(f"  regex: \"^(\\\\P)\"")
		print(f"  time:")
		print(f"    hour: \"{self.time}\"") #一天两次
		print(f"    minute: {blacklist_count%60}")
		print("\n")

def url_get(json_filename):
	# print(f'getting {json_filename}')
	try:
		response = requests.get(base_url + json_filename)
		return json.loads(response.content.decode('utf-8'))
	except Exception as e:
		print(f'{e}')
		return None

ipset_all = url_get('all-ipsets.json')

count = 0

print("""
# This file is generate from http://iplists.firehol.org/ by script in script/gen_primary_blacklist_configuration_file.py
#
# NERD config - primary blacklists
# used by blacklists.py script
---

# List specification:
#   id (used as key in records),
#   name (for humans),
#   url (http(s):// or file://, if local file is used, it should be updated by external cron script)
#   regex to parse the file (should match on IP address) or empty if there are only IP addresses, one per line (lines beginning with '#' are ignored),
#       or just fill regex with searching for IP, IP prefix or domain without group, if the whole blacklist is on one line or has multiple records on on line
#       - you can use special substitutions for IP address or CIDR IP address
#         - "//A" can be used for IP address, in interal part it will be substituted for IP regex
#         - "//CA" can be used for CIDR prefix (192.168.0.0/16)
#       IP address regex example, where IP address starts on every line:
#         "^(//A)"
#   refresh time (cron-like specification of when the list should be updated (in UTC), see https://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html for details)
#   other params (optional)
#
#   The last parameter is a dictionary of other parameters. The following keys are recognized:
#     url_params - dict of key-value pairs to pass as GET parameters in URL
#     headers - dict of key-value pairs specyfing additional HTTP headers
#   Example of url_params and headers usage can be viewed below in Abuse IP DB blacklist specification.
# 

""")

print("iplists:")
for item in tqdm.tqdm(ipset_all):
	# print(item["ipset"])
	ipset = item['ipset']
# {
# 		"ipset": "alienvault_reputation",
# 		"category": "reputation",
# 		"maintainer": "Alien Vault",
# 		"started": 1434691854000,
# 		"updated": 1636726250000,
# 		"checked": 1649915142000,
# 		"clock_skew": 0,
# 		"ips": 609,
# 		"errors": 0
# 	},
	single_ipset_json = url_get(ipset + '.json')
	# print(single_ipset_json['name'])
	id = single_ipset_json['name']
	name = "[{}]{} by {}.".format(single_ipset_json['category'], single_ipset_json['name'], single_ipset_json['maintainer'])
	descr = "{}. source url is {} ".format(single_ipset_json['info'], single_ipset_json['source'])
	firehol_link  = "http://iplists.firehol.org/?ipset={}".format(single_ipset_json['name'])
	provider_link = single_ipset_json['maintainer_url']
	# url = single_ipset_json['source']
	url = single_ipset_json['file_local']
	if url == "":
		continue
	
	print(f"# {name}:{descr}")
	monitoring_since = timestamp_datetime(single_ipset_json['started'])
	last_time_updated_by_its_maintainers = timestamp_datetime(single_ipset_json['updated'])
	print(f"# {last_time_updated_by_its_maintainers} \t last_time_updated_by_its_maintainers")
	last_time_processed_by_us = timestamp_datetime(single_ipset_json['processed'])
	print(f"# {last_time_processed_by_us} \t last_time_processed_by_us ")
	last_time_we_checked = timestamp_datetime(single_ipset_json['checked'])
	print(f"# {last_time_we_checked} \t last_time_we_checked")
	
	check_frequency = single_ipset_json['frequency']/60 # hour
	print(f"# check_frequency \t{check_frequency}")
	average_update_frequency = single_ipset_json['average_update']/60 # hour
	print(f"# average_update_frequency \t{average_update_frequency}")
	print(f"# ips \t{single_ipset_json['ips']}")
	print(f"# ips_min \t{single_ipset_json['ips_min']}")
	print(f"# ips_max \t{single_ipset_json['ips_max']}")
	print(f"# ipv \t{single_ipset_json['ipv']}")
	print(f"# hash \t{single_ipset_json['hash']}")
	print(f"# errors \t{item['errors']}")

	errors = item['errors']
	if errors > 0:
		time_hour = "5" #when errors occur, set the time to 5:XX every day 
	else: 
		average_update_frequency = math.ceil(average_update_frequency)
		if average_update_frequency >= 12: #when update frequency larger than 12 , set the time to 4:XX every day
			time_hour = "5"
		elif average_update_frequency > 4: #when update frequency between 4 - 12, set the time  */{average_update_frequency} 
			time_hour = f"*/{average_update_frequency}"
		else:
			time_hour = "*/4" # #when update frequency < 4,  set the time to */4

	bl = blacklist(id, name, descr, firehol_link, provider_link, url, time_hour)
	bl.format_output()

	count += 1

print(f"# {count} blacklist process done")

# {
# 	"name": "alienvault_reputation",
# 	"entries": 609,
# 	"entries_min": 458,
# 	"entries_max": 1623,
# 	"ips": 609,
# 	"ips_min": 458,
# 	"ips_max": 1623,
# 	"ipv": "ipv4",
# 	"hash": "ip",
# 	"frequency": 360,
# 	"aggregation": 0,
# 	"started": 1434691854000,
# 	"updated": 1636726250000,
# 	"processed": 1636732345000,
# 	"checked": 1636726250000,
# 	"clock_skew": 0,
# 	"category": "reputation",
# 	"maintainer": "Alien Vault",
# 	"maintainer_url": "https://www.alienvault.com/",
# 	"info": "<a href=\"https://www.alienvault.com/\">AlienVault.com</a>  IP reputation database ",
# 	"source": "https://reputation.alienvault.com/reputation.generic",
# 	"file": "alienvault_reputation.ipset",
# 	"history": "alienvault_reputation_history.csv",
# 	"geolite2": "alienvault_reputation_geolite2_country.json",
# 	"ipdeny": "alienvault_reputation_ipdeny_country.json",
# 	"ip2location": "alienvault_reputation_ip2location_country.json",
# 	"ipip": "alienvault_reputation_ipip_country.json",
# 	"comparison": "alienvault_reputation_comparison.json",
# 	"file_local": "https://iplists.firehol.org/files/alienvault_reputation.ipset",
# 	"commit_history": "https://github.com/firehol/blocklist-ipsets/commits/master/alienvault_reputation.ipset",
# 	"license": "unknown",
# 	"grade": "unknown",
# 	"protection": "unknown",
# 	"intended_use": "unknown",
# 	"false_positives": "unknown",
# 	"poisoning": "unknown",
# 	"services": [ "unknown" ],
# 	"errors": 0,
# 	"version": 4236,
# 	"average_update": 459,
# 	"min_update": 30,
# 	"max_update": 49501,
# 	"downloader": "geturl"
# }