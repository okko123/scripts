#!/usr/bin/env python3

import logging
import lxml
import os
import requests
import sys

from bs4 import BeautifulSoup

pt_url = "https://pt.soulvoice.club/attendance.php"

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.33",
    "Content-Type": "application/x-www-form-urlencoded",
}


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


logger = create_logger(os.path.basename(sys.argv[0]), "False", "/data/tools/pt.log")

with open("/data/tools/cookies_soulvoice.txt") as f:
    cookies = dict([l.split("=", 1) for l in f.read().split(";")])

try:
    r = requests.get(url=pt_url, headers=headers, cookies=cookies, timeout=5)
    logger.info("OK")
except requests.exceptions.Timeout as e:
    logger.info("timeout %s" % e)

res = r.text
soup = BeautifulSoup(res, "lxml")
messages = soup.find_all("p")
message = messages[0].get_text()
logger.info(message)
