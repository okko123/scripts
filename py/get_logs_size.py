#!/usr/bin/env python3

import pymysql
import datetime
import logging

from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException

# 初始化全局变量
namespace = "app"
log_file_path = "/data/app/logs/run_json.log"
today_date = datetime.datetime.now().date()

# 初始化日志
logging.basicConfig(
    level=logging.WARN,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 初始化
try:
    config.load_kube_config(config_file="/data/scripts/config/k8s01.config")
except Exception as e:
    logging.info(f"初始化Kubernetes客户端失败: {str(e)}")
    raise

apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

def insert_to_mysql(data):
    config = {
        'host': '192.168.1.1',
        'port': 3306,
        'user': 'grafana',
        'password': '123456',
        'database': 'test',
        'charset': 'utf8mb4',
        'autocommit': True,
    }

    sql_data = []
    for i in data:
        r = {}
        r["environment"] = "k8s01"
        r["project"]=i
        r["value"]=data[i] / (1024 * 1024 * 1024)
        r["date"]=today_date
        sql_data.append(r)

    logging.info(sql_data)

    try:
        conn = pymysql.connect(**config)
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO log_data (environment, date, value, project_name) VALUES (%(environment)s, %(date)s, %(value)s, %(project)s)
            """
            # 使用 executemany 批量插入
            logging.info(sql)
            cursor.executemany(sql, sql_data)
            print(f"批量插入 {cursor.rowcount} 条记录")
        conn.commit()
    except pymysql.MySQLError as e:
        logging.error(f"MySQL 错误: {e}")
        conn.rollback()  # 回滚事务
    except Exception as e:
        logging.error(f"其他错误: {e}")
        conn.rollback()
    finally:
        # 🧹 关闭连接
        if conn:
            conn.close()

def get_pods_by_deployment(deployment_name, namespace):
    """
    根据 Deployment 的 selector 获取其管理的所有 Pod
    """
    try:
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        selector = deployment.spec.selector.match_labels
        label_selector = ','.join([f"{k}={v}" for k, v in selector.items()])
        pods = core_v1.list_namespaced_pod(namespace, label_selector=label_selector)
        return pods.items
    except Exception as e:
        logging.error(f"无法获取 Deployment {deployment_name} 的 Pod: {e}")
        return []

def get_file_size_in_container(pod_name, container_name, namespace):
    """
    执行 exec 命令获取容器中指定文件的大小（字节）
    如果文件不存在或命令失败，返回 0
    """
    try:
        # 使用 exec 执行 stat 命令获取文件大小
        resp = stream(
            core_v1.connect_get_namespaced_pod_exec,
            name=pod_name,
            namespace=namespace,
            command=['sh', '-c', f'stat -c %s "{log_file_path}" 2>/dev/null || echo 0'],
            stdout=True,
            stderr=True,
            stdin=False,
            tty=False
        )
        return int(resp) if resp.isdigit() else 0
    except ApiException as e:
        logging.error(f"Exec 失败 [{namespace}/{pod_name} - {container_name}]: {e}")
        return 0
    except Exception as e:
        logging.error(f"未知错误 [{namespace}/{pod_name} - {container_name}]: {e}")
        return 0

def main():
    try:
        deployments = apps_v1.list_namespaced_deployment(namespace)
    except ApiException as e:
        logging.WARN(f"无法列出 Deployment: {e}")
        return

    if not deployments.items:
        logging.WARN(f"命名空间 '{namespace}' 中没有找到任何 Deployment。")
        return

    # 存储结果：{ deployment_name: total_size_bytes }
    result = {}

    for dep in deployments.items:
        dep_name = dep.metadata.name
        logging.warn(f"处理 Deployment: {dep_name}")

        pods = get_pods_by_deployment(dep_name, namespace)
        total_size = 0

        for pod in pods:
            if pod.status.phase != "Running":
                continue
            for container in pod.spec.containers:
                container_name = container.name
                pod_name = pod.metadata.name
                logging.info(f"name: {container_name}, pod_name: {pod_name}")
                size = get_file_size_in_container(pod_name, container_name, namespace)
                total_size += size
                if size > 0:
                    logging.info(f"Pod: {pod.metadata.name}, 容器: {container_name}, 日志大小: {size / (1024*1024):.2f} MB")

        result[dep_name] = total_size

    # 输出汇总结果
    print("\n" + "="*60)
    print("Deployment 日志文件大小汇总 (/data/app/logs/run.log)")
    print("="*60)
    for dep, size in result.items():
        size_gb = size / (1024 * 1024 * 1024)
        if size_gb > 10:
            print(f"{dep:30} : {size_gb:8.2f} GB")

    insert_to_mysql(result)

if __name__ == "__main__":
    main()
