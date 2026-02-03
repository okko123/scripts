#!/usr/bin/env python

import ldap
import logging
import os
import sys
import time
import datetime
import yaml
import re

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

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        try:
            config = yaml.safe_load(f)
            return config or {}
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 格式错误: {e}")

def ldap_connect(ldapuri, logger=None, binddn="", bindpw=""):
    ldap.set_option(ldap.OPT_DEBUG_LEVEL, 0)
    ldap_trace_level = 0
    ldap_trace_file = sys.stderr

    if logger:
        logger.debug(f"Connecting to {ldapuri}")
    conn = ldap.initialize(
        ldapuri,
        trace_level = ldap_trace_level,
        trace_file = ldap_trace_file
    )

    if logger:
        logger.debug("LDAP protocol version 3")
    conn.protocal_version = ldap.VERSION3

    if binddn:
        password = bindpw
        if logger:
            logger.debug(f"Binding with {binddn}")
    else:
        password = ""
        logger.debug("Binding with anonymously")

    try:
        conn.bind_s(binddn, password, ldap.AUTH_SIMPLE)
        return conn

    except ldap.LDAPError as error_message:
        if logger:
            logger.error(f"server: {ldapuri}. LDAP bind failed. {error_message}")
        return None

def ldap_search(ldapobj, basedn, scope, filter, attrlist):
    result_set = (ldapobj.search_s(basedn, scope, filter, attrlist))
    return result_set

def get_contextCSN(ldapobj, basedn ,logger=None, serverid=False):
    result_list = ldap_search(ldapobj, basedn, ldap.SCOPE_BASE, '(objectclass=*)', ['contextCSN'])

    if logger:
        logger.debug(f"get all result {result_list}")

    if "contextCSN" in result_list[0][1]:
        cns = result_list[0][1]["contextCSN"][1].decode('utf-8')
        if logger:
            logger.debug(f"contextCSN = {cns}")
        return cns

    else:
        if logger:
            logger.debug(f"No contextCSN was found")
        return None

def contextCSN_to_datetime(contextCSN):
    """
    Convert contextCSN string (YYYYmmddHHMMMSSZ#...) to datetime object
        contextCSN - Timestamp in YYYYmmddHHMMSSZ#... format (string)

    This function returns a datetime object instance
    """
    gentime = re.sub('(\.\d{6})?Z.*$', '', contextCSN)
    return datetime.datetime.fromtimestamp(time.mktime(time.strptime(gentime,"%Y%m%d%H%M%S")))

def threshold_to_datetime(threshold):
    """
    Convert threshold in seconds to datetime object
        threshold - seconds (integer)

    This function returns a datetime object instance
    """
    nbdays, nbseconds = divmod(threshold, 86400)
    return datetime.timedelta(days=nbdays, seconds=nbseconds)

def is_insynch(provldapobj, consldapobj, basedn, threshold=None, logger=None):
    """
    Check if the consumer is in synch with the provider within the threshold
        provldapobj - Provider LDAP object instance
        consldapobj - Consumer LDAP object instance
        basedn - LDAP base dn (string)
        threshold - limit above which provider and consumer are not considered
        in synch (int)

        This function returns False if the provider and the consumer is not
        in synch, True if in synch within the threshold
    """
    if logger:
        logger.debug("Retrieving Provider contextCSN")
    provcontextCSN = get_contextCSN(provldapobj, basedn, logger)

    if logger:
        logger.debug("Retrieving Consumer contextCSN")
    conscontextCSN = get_contextCSN(consldapobj, basedn, logger)

    if (provcontextCSN and conscontextCSN):
        if (provcontextCSN == conscontextCSN):
            if logger:
                logger.info("OK Provider and consumer exactly in SYNCH")
            return True
        else:
            delta = contextCSN_to_datetime(provcontextCSN) - contextCSN_to_datetime(conscontextCSN)
            LdapDelta= f"Delta is: {delta}"
            logger.info(LdapDelta)

            if threshold:
                maxdelta = threshold_to_datetime(eval(threshold))
                if logger:
                    logger.debug(f"Threshold is {maxdelta}")
                if (abs(delta) <= maxdelta):
                    if logger:
                        logger.info(" Consumer is SYNCH within threshold")
                        logger.info(f" Deta is {delta}")
                else:
                    if logger:
                        logger.warn(" Consumer NOT in SYNCH within threshold")
            else:
                if logger:
                    logger.error("NOT SET threshold")
                    logger.error(f" Delta is {delta}")
                return True
    else:
        if logger:
            logger.error(" Check failed: at least one ContextCSN value is missing")
    return False

def main():
    if logger:
        logger.info("===== begin =====")

    ldapprov = ldap_connect(
        ldapuri = config['prov'],
        logger = logger,
        binddn = config['binddn'],
        bindpw = config['passwd']
    )

    if ldapprov:
        for consumer in config['cons']:
            if logger:
                logger.info(f"Checking if consumer {consumer} is in SYNCH with provider")

            ldapcons = ldap_connect(
                consumer,
                logger,
                config['binddn'],
                config['passwd'],
            )

            if ldapcons:
                IsInSync = is_insynch(ldapprov, ldapcons, config['basedn'], config['threshold'], logger)
                ldapcons.unbind_s()

        ldapprov.unbind_s()
    else:
        sys.exit(1)

if __name__ == '__main__':
    logger = create_logger("ldap_checker", verbose=True)
    try:
        config = load_config("config.yaml")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"❌ 配置加载失败: {e}")
    main()
