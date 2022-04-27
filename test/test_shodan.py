import shodan
import argparse
import json
apikey="nFPFE0LlxJJqwa77rHFJ3naqME24S31A"
client = shodan.Shodan(key=apikey)
parser = argparse.ArgumentParser(description='shodan Example')
parser.add_argument('-ip', help='IP eg; 4.4.4.4', required=False)
args = vars(parser.parse_args())


data = client.host(args['ip'], history=False, minify=False)
json_data = json.dumps(data)
print(data)