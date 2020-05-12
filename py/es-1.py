import re
import json
import requests
from datetime import datetime, timedelta, date
from elasticsearch_dsl import connections, Search, Q

def gen_times(now):
    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    times = []
    for i in range(0, 24, 2):
        st = yesterday.replace(hour=i)
        et = st + timedelta(hours=2)
        times.append((st, et))
    return times

def send_message(body):
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
    headers = {'content-type': 'application/json'}
    data =  {
        "msgtype": "text",
        "text": {
            "content": body
        }
    }
    r = requests.post(url, json=data, headers=headers)

if __name__ == '__main__':
    times = gen_times(datetime.now())
    fmt = '%d/%b/%Y:%H:%M:%S +0800'

    # Define a default Elasticsearch client
    connections.create_connection(hosts=['ip:9200'])    
    client = connections.get_connection()

    muid_list = []
    android = 0
    ios = 0

    for s, e in times:
        if int(s.strftime("%H")) < 8:
            day = (date.today() + timedelta(-2))
            esindex = "nginx-proxy-" + day.strftime("%Y.%m.%d")
        else:
            day = (date.today() + timedelta(-1))
            esindex = "nginx-proxy-" + day.strftime("%Y.%m.%d")

        start = s.strftime(fmt)
        end = e.strftime(fmt)

        q = Q("bool",
            must = [
                Q("match", domain = "www.baidu.com"),
                Q("match", http_user_agent = "ID")
            ],
            filter = [
                Q("range", time_local = {
                    "gte": start,
                    "lt": end
                    }
                )
            ]
        )

        pattern = "ID(.)[^ ]+"
        osmt = "[A-z]+"

        s = Search().using(client).index(esindex).query(q).source("http_user_agent").extra(from_=0, size=2000)
        for hit in s.scan():
            r = re.search(pattern, hit.http_user_agent)
            r1 = re.search(osmt, hit.http_user_agent)
            if r.group() and (r.group() not in muid_list):
                muid_list.append(r.group())
                if r1.group() == "ERCAndroid":
                    android += 1
                elif r1.group() == "ERCIOS":
                    ios += 1
    message = "{day} ID is {muid}, android user is {android}, ios user {ios}".format(day = day.strftime("%Y.%m.%d"), android=android, ios=ios, muid=len(muid_list))
    send_message(message)
