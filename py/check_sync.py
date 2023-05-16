#!/usr/bin/env python
# https://github.com/tart/tart-monitoring/blob/master/check_syncrepl.py#L184
# check in python 3.10 and openldap 2.4.54

import ldap
import logging
import os
import sys
import re
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

            print("OK - Provider and consumer exactly in SYNCH")

            return True
    else:
        if logger:
            logger.error(" Check failed: at least one contextCSN value is missing")

        print("Check failed: at least one contextCSN value is missing")

    return False

def main():
    IsInSync = True;

    usage = "\n  " + sys.argv[0] + """ [options] providerLDAPURI consumerLDAPURI ...
    This script takes at least two arguments:
          - providerLDAPURI is the provider LDAP URI (as defined in RFC2255)
          - consumerLDAPURI is the consumer LDAP URI (as defined in RFC2255)
    Additional consumer LDAP URIs can be specified.
    """

    parser = OptionParser(usage = usage)
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      default=False,
                      help="""Enable more verbose output""")

    parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
                      default=False,
                      help="""Disable console and file logging""")

    parser.add_option("-l", "--logfile", dest="logfile", default=re.sub("\.[^\.]*$", "", sys.argv[0]) + '.log',
                      help="""Log the actions of this script to this file
                              [ default : %default ]""")

    parser.add_option("-D", "--binddn",
                        dest = "binddn", default = "",
                        help = """Use the Distinguished Name to bind [default:
                        anonymous]. You will be prompted to enter the
                        associated password.""")

    parser.add_option("-b", "--basedn",
                      dest="basedn", default="dc=amnh,dc=org",
                      help="LDAP base dn [default: %default].")

    parser.add_option("-t", "--threshold", dest="threshold",
                      default=None,
                      help="""Threshold value in seconds""")

    parser.add_option("-p", "--password", dest="password",
                    default="",
                    help="""Bind password""")

    parser.add_option("-i", "--serverID",
                    dest="serverid",
                    action="store",
                    type='int',
                    help="Compare contextCSN of a specific master. Useful in MultiMaster setups where each master has a unique ID and a contextCSN for each replicated master exists. A valid serverID is a integer value from 0 to 4095 (limited to 3 hex digits, example: '12' compares the contextCSN matching '#00C#')",
                    default=False)

    (options, args) = parser.parse_args()

    if not options.quiet:
        logger = create_logger(os.path.basename(sys.argv[0]), options.verbose, options.logfile)
    else:
        logger = None

    if logger:
        logger.info("====== begin ======")
        logger.info("Provider is: %s" % re.sub("^.*\/\/", "", args[0]))

    ldapprov = ldap_connect(args.pop(0), logger, options.binddn, options.password)

    if ldapprov:
        for consumer in args:
            if logger:
                logger.info("Checking if consumer %s is in SYNCH with provider" % re.sub("^.*\/\/", "", consumer))
            ldapcons = ldap_connect(consumer, logger, options.binddn, options.password)

            if ldapcons:
                IsInSync = IsInSync and is_insynch(ldapprov, ldapcons, options.basedn, options.threshold, logger, options.serverid)
                ldapcons.unbind_s()
            else:
                sys.exit()

        ldapprov.unbind_s()

    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
