import re
import datetime
from elasticsearch_dsl import Document, Date, Integer, Keyword, Text, connections, Search, Q

dayone = (datetime.date.today() + datetime.timedelta(-1))
daytwo = (datetime.date.today() + datetime.timedelta(-2))
esindex = "nginx-proxy-" + dayone.strftime("%Y.%m.%d")

start = dayone.strftime("%d/%b/%Y:08:00:00 +0800")
end = dayone.strftime("%d/%b/%Y:10:00:00 +0800")

print(esindex, start, end)
# Define a default Elasticsearch client
connections.create_connection(hosts=['ip:9200'])

client = connections.get_connection()
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

s = Search().using(client).index(esindex).query(q).sort("time_local").source("http_user_agent").extra(from_=0, size=2000)
respones = s.execute()
stop = int(respones.hits.total)
step = 0
pattern = "ID(.)[^ ]+"
muid_list = []

while step <= stop:
    s = Search().using(client).index(esindex).query(q).sort("time_local").extra(from_=step, size=2000)
    respones = s.execute()
    for hit in s:
        r = re.search(pattern, hit.http_user_agent)
        if r.group():
        #if r.group() and (r.group() not in muid_list):
            muid_list.append(r.group())

    step = step + 2000

print(len(muid_list))

