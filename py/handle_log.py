#!/usr/bin/env python3

import os
import re
import logging
import pymysql
from datetime import datetime

# 初始化日志
logging.basicConfig(
    level=logging.WARN,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def handle_data(name, s_date):
    f_name = f"files/{name}"
    logging.info(f_name)
    l_res = []
    with open(f_name, "r", encoding="utf-8") as f:
        for line in f:
            res = {}
            r = line.rstrip().split(",", 2)
            res["project"] = r[1]
            res["value"] = int(r[0])/(1024**3)
            res["date"] = s_date
            res["environment"] = "k8s01"
            logging.info(f"name: {r[1]}, value: {r[0]}, environment: k8s01, date: {s_date}")
            l_res.append(res)
    logging.info(l_res)

    insert_to_mysql(l_res)

def extract_dates_from_files(directory="files"):
    """
    从指定目录的文件名中提取日期
    """
    if not os.path.exists(directory):
        logging.info(f"目录 '{directory}' 不存在")
        return

    for filename in os.listdir(directory):
        # 查找文件名中的数字模式 MMdd
        match = re.search(r'(\d{2})(\d{2})', filename)
        if match:
            month, day = match.groups()
            try:
                # 假设年份为2025
                date_obj = datetime(2025, int(month), int(day))
                date_str = date_obj.strftime("%Y-%m-%d")
                logging.info(f"{filename} -> {date_str}")
            except ValueError:
                logging.warn(f"{filename} -> 无效日期")
        else:
            logging.warn(f"{filename} -> 无日期信息")

        handle_data(filename, date_str)

def insert_to_mysql(sql_data):
    config = {
        'host': '192.168.1.1',
        'port': 3306,
        'user': 'grafana',
        'password': '123456',
        'database': 'test',
        'charset': 'utf8mb4',
        'autocommit': True,
    }
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
            logging.info(f"批量插入 {cursor.rowcount} 条记录")
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

# 使用示例
if __name__ == "__main__":
    extract_dates_from_files("files")
