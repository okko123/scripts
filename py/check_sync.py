#!/usr/bin/env python
# https://github.com/tart/tart-monitoring/blob/master/check_syncrepl.py#L184
# check in python 3.10 and openldap 2.4.54

import json
import ldap
import logging
import os
import sys
import re
import requests
import yaml
from optparse import OptionParser

def create_logger(application, verbose=None, logfile=None):
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

    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setLevel(lowestseverity)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def create_alert(instance):
    info = [
        {
            "labels": {
                "alertname": "LDAP同步异常",
                "instance": instance,
                "severity": "critical",
                "service": "OpenLDAP"
            },
            "annotations": {
                "info": "LDAP同步异常",
                "summary": "请检查实例",
                "env": "stage"
            }
        }
    ]

    headers = {"Content-Type": "application/json"}
    jsons = json.dumps(info)
    alert_url = "http://127.0.0.1:9093/api/v2/alerts"
    r = requests.post(alert_url, headers=headers, data=jsons)
    return True

def ldap_connect(ldapuri, logger=None, binddn="", bindpw=""):
    ldap.set_option(ldap.OPT_DEBUG_LEVEL, 0)
    ldap_trace_level = 0
    ldap_trace_file = sys.stderr

    if logger:
        logger.debug("Connecting to %s" % ldapuri)

    conn = ldap.initialize(ldapuri,
                            trace_level=ldap_trace_level,
                            trace_file=ldap_trace_file)

    if logger:
        logger.debug("LDAP protocol version 3")
    conn.protocol_version = ldap.VERSION3

    if binddn:
        password = bindpw
        if logger:
            logger.debug("Binding with %s" % binddn)
    else:
        password = ""
        logger.debug("Binding with anonymously")

    try:
        conn.bind_s(binddn, password, ldap.AUTH_SIMPLE)
        return conn

    except ldap.LDAPError as error_message:
        if logger:
            logger.debug("LDAP bind failed. %s" % error_message)
        print("FAILED : LDAP bind failed. %s" % error_message)
        return None

def ldap_search(ldapobj, basedn, scope, filter, attrlist):
    result_set = (ldapobj.search_s(basedn, scope, filter, attrlist))
    return result_set

def get_contextCSN(ldapobj, basedn, logger=None, serverid=False):
    result_list = ldap_search(ldapobj, basedn, ldap.SCOPE_BASE, '(objectclass=*)', ['contextCSN'])

    if "contextCSN" in result_list[0][1]:
        CSNs = result_list[0][1]["contextCSN"]

        if serverid is False:
            if logger:
                logger.debug("contextCSN = %s" % CSNs[0])

            return result_list[0][1]["contextCSN"][0]

        else:
            csnid = str(format(serverid, "X")).zfill(3)
            sub = "#%s#" % csnid
            CSN = [s for s in CSNs if sub in s.decode()]

            if not CSN:
                logging.error("No contextCSN matching with ServerID %s (=%s) could be found." % (serverid,sub))
                return False
            else:
                logger.debug("contextCSN = %s" % CSN[0])
                return CSN[0]

    else:
        if logger:
            logger.error("No contextCSN was found")

        return None

    pass

def is_insynch(provldapobj, consldapobj, basedn, threshold=None, logger=None, serverid=False):
    if logger:
        logger.debug("Retrieving Provider contextCSN")
    provcontextCSN = get_contextCSN(provldapobj, basedn, logger, serverid)

    if logger:
        logger.debug("Retrieving Consumer contextCSN")
    conscontextCSN = get_contextCSN(consldapobj, basedn, logger, serverid)

    if (provcontextCSN and conscontextCSN):
        if (provcontextCSN == conscontextCSN):
            if logger:
                logger.info("Provider and consumer exactly in SYNCH")
            return True
        else:
            return False
    else:
        if logger:
            logger.error(" Check failed: at least one contextCSN value is missing")
        print("Check failed: at least one contextCSN value is missing")
    return False

def main():
    IsInSync = True;

    with open("config.yaml", "r") as f:
        configs = yaml.load(f.read(), Loader=yaml.FullLoader)

    usage = "\n  " + sys.argv[0]

    if not configs["quite"]:
        logger = create_logger(os.path.basename(sys.argv[0]), configs["verbose"], configs["logfile"])
    else:
        logger = None

    if logger:
        logger.info("====== begin ======")
        logger.info("Provider is: %s" % re.sub("^.*\/\/", "", configs["prov"]))

    ldapprov = ldap_connect(configs["prov"], logger, configs["binddn"], configs["passwd"])

    if ldapprov:
        for consumer in configs["cons"]:
            if logger:
                logger.info("Checking if consumer %s is in SYNCH with provider" % re.sub("^.*\/\/", "", consumer))
            ldapcons = ldap_connect(consumer, logger, configs["binddn"], configs["passwd"])

            if ldapcons:
                IsInSync = IsInSync and is_insynch(ldapprov, ldapcons, configs["basedn"], None, logger, configs["serverID"])
                ldapcons.unbind_s()
                print(IsInSync)
                if not IsInSync:
                    create_alert(consumer)
            else:
                sys.exit()

        ldapprov.unbind_s()

    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
