#!/usr/bin/python3
"""
IPVisualizator API Backend v0.9

Copyright (c) 2020 Jakub Jancicka <jancijak@fit.cvut.cz>
Released under Apache license v2.0
"""

import sys
import connexion
from connexion.exceptions import OAuthProblem
import math
import logging
from ipaddress import IPv4Address, IPv4Network
from flask_cors import CORS
from flask import Response
import yaml
import json
import re
import redis
from jsonschema import draft4_format_checker

from redisdb import RedisDB, NotFoundError

CONFIG_FILE = "config/config.yml"
CONFIG = {}

#################################
# Helpers

IP_RE = re.compile("^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")


@draft4_format_checker.checks("ip")
def is_ip(val):
    if not isinstance(val, str):
        return True

    return IP_RE.match(val) is not None


def convert_ip_data_from_csv(records):
    ips = {}

    for row in records.splitlines():
        row = row.decode("UTF-8").strip()

        # Skip comments and empty lines
        if len(row) == 0 or row[0] == "#":
            continue

        record = row.split(',')

        if len(record) != 2:
            raise Exception('Row "{}" is not valid CSV format.'.format(row))

        if IP_RE.match(record[0]) is None:
            raise Exception('"{}" is not valid IP address.'.format(record[0]))

        ip = record[0]

        try:
            value = float(record[1])
        except ValueError:
            raise Exception('"{}" is not valid float number.'.format(record[1]))

        ips[ip] = value

    return ips

#################################
# API


def create_new_dataset_api(user, records):
    try:
        records = convert_ip_data_from_csv(records)
    except Exception as e:
        return {"status": 400, "detail": str(e)}, 400

    if len(records) == 0:
        return {"status": 400, "detail": "No data provided."}, 400

    user = db.find_user_by_uid(user)
    dataset = db.create_dataset(records, user)

    return {"status": 200, "token": dataset.token}, 200


def get_dataset_metadata_api(user, token):
    if db.dataset_exist(token) is False:
        return {"status": 404, "detail": "Dataset not found"}, 404

    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False:
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    metadata = db.get_dataset_metadata(token)

    user = {"uid": metadata.user.uid, "username": metadata.user.username, "authorization": metadata.user.authorization,
            "admin": metadata.user.admin, "owned_datasets": metadata.user.owned_datasets}

    return {"token": metadata.token, "user": user, "size": metadata.size, "dataset_created": metadata.dataset_created,
            "dataset_updated": metadata.dataset_updated, "dataset_viewed": metadata.dataset_viewed}


def update_dataset_api(user, token, records):
    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False and db.dataset_exist(token) is True :
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    try:
        records = convert_ip_data_from_csv(records)
    except Exception as e:
        return {"status": 400, "detail": str(e)}, 400

    if len(records) == 0:
        return {"status": 400, "detail": "No data provided."}, 400

    if db.dataset_exist(token) is False:
        db.create_dataset(records, user, token)
    else:
        db.update_dataset(token, records, update="set")

    return {"status": 200}, 200


def patch_dataset_api(user, token, records, incr=False, decr=False):
    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False and db.dataset_exist(token) is True :
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    try:
        records = convert_ip_data_from_csv(records)
    except Exception as e:
        return {"status": 400, "detail": str(e)}, 400

    if len(records) == 0:
        return {"status": 400, "detail": "No data provided."}, 400

    if db.dataset_exist(token) is False:
        db.create_dataset(records, user, token)
    else:
        if incr is True:
            db.update_dataset(token, records, update="incr")
        elif decr is True:
            db.update_dataset(token, records, update="decr")
        else:
            db.update_dataset(token, records, update="patch")

    return {"status": 200}, 200


def delete_dataset_api(user, token):
    if db.dataset_exist(token) is False:
        return {"status": 404, "detail": "Dataset not found"}, 404

    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False:
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    db.delete_dataset(token)

    return {"status": 200}, 200


def get_ip_api(user, token, ip):
    if db.dataset_exist(token) is False:
        return {"status": 404, "detail": "Dataset not found"}, 404

    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False:
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    try:
        ip = IPv4Address(ip)
    except ValueError:
        return {"status": 400, "detail": "IP address is invalid"}, 400

    ip_record = db.get_ip_record(token, ip)

    return {"status": 200, "ip": str(ip_record.ip), "val": ip_record.value}, 200


def delete_ip_api(user, token, ip):
    if db.dataset_exist(token) is False:
        return {"status": 404, "detail": "Dataset not found"}, 404

    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False:
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    try:
        ip = IPv4Address(ip)
    except ValueError:
        return {"status": 400, "detail": "IP address is invalid"}, 400

    db.delete_ip_record(token, ip)

    return {"status": 200}, 200


def put_ip_api(user, token, ip, value, incr=False, decr=False):
    if db.dataset_exist(token) is False:
        return {"status": 404, "detail": "Dataset not found"}, 404

    user = db.find_user_by_uid(user)

    if db.user_permission(user, token) is False:
        return {"status": 401, "detail": "User doesn't have a permission to manipulate with this dataset"}, 401

    try:
        ip = IPv4Address(ip)
        value = float(value)
    except ValueError:
        return {"status": 400, "detail": "IP address or value is invalid"}, 400

    if incr is True:
        db.update_ip_record(token, ip, value, update="incr")
    elif decr is True:
        db.update_ip_record(token, ip, value, update="decr")
    else:
        db.update_ip_record(token, ip, value, update="set")

    return {"status": 200}, 200


def get_map_api(token, network, mask, resolution=None, skip_zeros=False, raw_data=False):
    if db.dataset_exist(token) is False:
        return {"status": 404, "detail": "Dataset not found"}, 404

    try:
        mask = int(mask)
        network = IPv4Network((network, mask))
    except ValueError:
        return {"status": 400, "detail": "Network or mask is invalid."}, 400

    if mask % 2 != 0:
        return {"status": 400, "detail": "Mask must be even number"}, 400

    if resolution is None:
        resolution = mask + 16 if mask + 16 <= 32 else 32
    else:
        try:
            resolution = int(resolution)
        except ValueError:
            return {"status": 400, "detail": "Resolution is not integer."}, 400

        if resolution % 2 != 0 or resolution < network.prefixlen or resolution > 32:
            return {"status": 400,
                    "detail": "Resolution is invalid - not even or less than given mask or greater than 32."}, 400

    if raw_data is False:
        response = {"status": 200, "network": str(network.network_address), "mask": str(network.netmask),
                    "prefix_length": network.prefixlen, "min_address": str(network.network_address),
                    "max_address": str(network.broadcast_address), "pixel_mask": resolution}
    else:
        response = {"status": 200, "network": int(network.network_address), "mask": str(network.netmask),
                    "prefix_length": network.prefixlen, "min_address": int(network.network_address),
                    "max_address": int(network.broadcast_address), "pixel_mask": resolution}

    hilbert_order = int((resolution - network.prefixlen) / 2)
    dataset = db.get_dataset(token, network, resolution)
    networks = dataset.get_networks(network, resolution)

    max_value = - math.inf
    min_value = math.inf

    round_p = float(10**5)
    pixels = []

    for index, value in enumerate(networks):

        # faster rounding of value to 5 decimal digit
        value = int(value * round_p + 0.5)/round_p
        if value != 0.0:
            min_value = value if value < min_value else min_value
            max_value = value if value > max_value else max_value

        if skip_zeros is not True or value != 0.0:
            if raw_data is False:
                x, y = dataset.hilbert_i_to_xy(index, hilbert_order)
                pixels.append({"y": y, "x": x, "val": value, "ip": "{}/{}".format(
                    str(network.network_address + (index << 32 - resolution)), str(resolution))})
            else:
                pixels.append({"val": value, "ip": index})

    response["pixels"] = pixels
    response["max_value"] = max_value if max_value != - math.inf else 0.0
    response["min_value"] = min_value if min_value != math.inf else 0.0
    response["hilbert_order"] = hilbert_order

    return Response(json.dumps(response, separators=(',', ':')), status=200, mimetype='application/json')


def get_user_info_api(user):
    user = db.find_user_by_uid(user)

    return {"uid": user.uid, "username": user.username, "authorization": user.authorization,
            "admin": user.admin, "owned_datasets": user.owned_datasets}, 200


def create_new_user_api(user):
    user = db.create_user(user["username"])

    return {"uid": user.uid, "username": user.username, "authorization": user.authorization, "admin": user.admin}, 200


def delete_user_api(user):
    db.delete_user(uid=user)

    return {"status": 200}, 200


def apikey_auth(token, required_scopes):
    try:
        user = db.find_user_by_authorization(token)
    except NotFoundError:
        raise OAuthProblem("Invalid token")

    return {"uid": user.uid}


#################################
# Setup IPVisualizator application 

# Setup logger
logger = logging.getLogger("IPVisualizator")
logger.setLevel(logging.INFO)
h = logging.StreamHandler()
h.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
h.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(h)

# Open Config
try:
    with open(CONFIG_FILE, 'r') as data:
        try:
            CONFIG = yaml.safe_load(data)
        except yaml.YAMLError as error:
            logger.critical("Config file '{}' is not valid YAML: {}".format(CONFIG_FILE, error))
            sys.exit(1)
except FileNotFoundError:
    logger.critical("Config file '{}' is not found.".format(CONFIG_FILE))
    sys.exit(1)
except PermissionError:
    logger.critical("Config file '{}' is not readable.".format(CONFIG_FILE))
    sys.exit(1)

# Setup connexion
app = connexion.App(__name__)
CORS(app.app)
API_FILE = CONFIG.get("app", {}).get("api_file", "api/api.yml")
try:
    app.add_api(API_FILE, arguments={"title": "IPVisualizator"})
except FileNotFoundError:
    logger.critical("API file '{}' is not found.".format(API_FILE))
    sys.exit(1)
except PermissionError:
    logger.critical("API file '{}' is not readable.".format(API_FILE))
    sys.exit(1)


# Redis backend for storing data
redis_host = CONFIG.get("redis", {}).get("host", "127.0.0.1")
redis_port = CONFIG.get("redis", {}).get("port", 6379)
redis_db = CONFIG.get("redis", {}).get("db", 0)
redis_prefix = CONFIG.get("redis", {}).get("data_prefix", "ipvisualizator")
initial_users = CONFIG.get("users", [])

try:
    db = RedisDB(host=redis_host, port=redis_port, db=redis_db, data_prefix=redis_prefix, initial_users=initial_users)
except redis.exceptions.ConnectionError as error:
    logger.critical("Can't connect to redis {}:{}.".format(redis_host, redis_port))
    sys.exit(1)

# Expose app for WSGI applications
application = app.app

# Run Flask development server
if __name__ == "__main__":
    app.run(port=CONFIG["app"]["port"])
