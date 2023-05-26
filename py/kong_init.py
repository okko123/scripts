#!/usr/bin/env python3
# use for kong
# copy service from source kong to target kong

import json
import logger
import os
import requests

def create_logger(application, verbose=None):
    if verbose:
        lowestseverity = logging.DEBUG
    else:
        lowestseverity = logging.INFO

    logger = logging.getLogger(application)
    logger.setLevel(lowestseverity)
    ch = logging.StreamHandler()
    ch.setLevel(lowestseverity)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

logger = create_logger(os.path.basename(sys.argv[0]), "debug")

source_server = "http://192.168.0.1:8001"
target_server = "http://192.168.0.2:8001"

logger.info("===== begin =====")
url = "{0}/services".format(source_server)

logger.debug(url)
r = requests.get(url)
res = json.loads(r.text)

for job in res["data"]:
    host_name = job["host"]
    name = job["name"]

    data = {
        "host": host_name,
        "protocol": "http",
        "name": name,
        "port": "8000",
    }

    # create service
    url = "{0}/services".format(target_server)
    r = requests.post(url, data=data)

    url = "{0}/services/{1}/routes".format(source_server, name)

    # get route's name
    r = requests.get(url)
    route_data = json.loads(r.text)

    for i in route_data["data"]:
        route_name = i["name"]
        route_path = i["paths"]
        routes = {
            "name": route_name,
            "paths": route_path,
            "methods": ["GET", "POST"],
            "protocols": ["http"],
        }

        url = "{0}/services/{1}/routes".format(target_server, name)
        r = requests.post(url, data=routes)
        print(r.status_code, r.text)
