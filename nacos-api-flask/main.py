import os
import nacos
import subprocess
from flask import Flask
from flask import request
from flask import render_template

servers = (
    ["192.168.0.1:8848", "2adcxfbf-7564-46eb-92c0-6fa8fab35d83"],
    ["192.168.0.2:8848", "2adcxfbf-7564-46eb-92c0-6fa8fab35d83"],
    ["192.168.0.3:8848", "2adcxfbf-7564-46eb-92c0-6fa8fab35d83"],
    ["192.168.0.4:8848", "2adcxfbf-7564-46eb-92c0-6fa8fab35d83"]
    )

mq_servers = (
    ['192.168.0.10:9876', 'mq_cluster_1'],
    ['192.168.0.11:9876', 'mq_cluster_2'],
    ['192.168.0.12:9876', 'mq_cluster_3'],
    ['192.168.0.13:9876', 'mq_cluster_4']
    )

app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/getconfig', methods=['POST'])
def getconfig():
    try:
        data_id = request.form['dataid']
        group = request.form['group']
    except:
        return "ERROR", 503

    datas = []
    for server in servers:
        address = server[0]
        namespace = server[1]
        client = nacos.NacosClient(address, namespace=namespace, username="nacos", password="nacos")
        datas.append([address, data_id, group, client.get_config(data_id, group)])
    return render_template('getconfig.html', datas=datas)

@app.route('/publish', methods=['GET', 'POST'])
def publishconfig():
    if request.method == 'POST':
        try:
            data_id = request.form['dataid']
            group = request.form['group']
            content = request.form['content']
            env = request.form['env']

            if env == 'all':
                nacos_servers = servers
            elif env == 'stage':
                nacos_servers = servers[0:2]
            elif env == 'qa':
                nacos_servers = servers[-2:]
            else:
                return "Error no env select"
            print(request.form, env, nacos_servers)

            for server in nacos_servers:
                address = server[0]
                namespace = server[1]
                client = nacos.NacosClient(address, namespace=namespace, username="nacos", password="nacos")
                client.publish_config(data_id, group, content, '5')
            return "OK"
        except Exception as e:
            print(e)
            return "ERROR", 503
    else:
        return render_template('publish.html')

@app.route('/mq', methods=['GET', 'POST'])
def publishmq():
    if request.method == 'GET':
        return render_template('mq.html')
    else:
        try:
            topic = request.form['topic']
            for server in mq_servers:
                command = "/usr/local/rocketmq-4.9/bin/mqadmin updateTopic -c %s -n '%s' -r 4 -w 4 -t %s " % (server[1], server[0], topic)
                print(command)
                #subprocess.call(command, shell=True)
                subprocess.Popen(command, shell=True)
                #subprocess.Popen([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(e)
            return "ERROR"
        return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
