#!/usr/bin/env python
# coding=utf-8
# 2021-09-17 clean aliyun acr mirrors

import sys
import json
import time
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcore.client import AcsClient

from aliyunsdkcr.request.v20160607 import GetRepoListRequest
from aliyunsdkcr.request.v20160607 import GetRepoTagsRequest
from aliyunsdkcr.request.v20160607 import DeleteImageRequest

namespace = 'namespace-zt'
times = 0

apiClient = AcsClient('xxxxxx', 'xxxxxxxxxx', 'cn-shenzhen')

def get_repo_list():
    request = GetRepoListRequest.GetRepoListRequest()
    request.set_Status('NORMAL')
    request.set_endpoint("cr.cn-shenzhen.aliyuncs.com")

    try:
        response = apiClient.do_action_with_exception(request)
        #print(response)
    except ServerException as e:
        print(e)
    except ClientException as e:
        print(e)

    res = json.loads(response)
    list = []
    for name in res['data']['repos']:
        list.append(name['repoName'])
    return list

def get_tags(repo_name):
    request = GetRepoTagsRequest.GetRepoTagsRequest()
    request.set_RepoName(repo_name)
    request.set_RepoNamespace(namespace)
    request.set_endpoint("cr.cn-shenzhen.aliyuncs.com")

    try:
        response = apiClient.do_action_with_exception(request)
        #print(response)
    except ServerException as e:
        print(e)
    except ClientException as e:
        print(e)

    res = json.loads(response)
    pages = res['data']['total']/res['data']['pageSize']
    page = res['data']['page']
    total = res['data']['total']
    list = []

    for name in res['data']['tags']:
        list.append(name['tag'])

    while page < pages:
        page += 1
        request.set_Page(page)

        try:
            response = apiClient.do_action_with_exception(request)
        except ServerException as e:
            print(e)
        except ClientException as e:
            print(e)

        res = json.loads(response)
        for name in res['data']['tags']:
            list.append(name['tag'])

    #list.sort(key=lambda x:int(x.split('-')[2]))
    return list, total

def delete_images(job, tags, namespace):
    global times
    tags.sort(key=lambda x:int(x.split('-')[2]))
    request = DeleteImageRequest.DeleteImageRequest()
    request.set_RepoNamespace(namespace)
    request.set_RepoName(job)

    for tag in tags[0:-30]:
        request.set_Tag(tag)
        try:
            response = apiClient.do_action_with_exception(request)
        except ServerException as e:
            print(e)
        except ClientException as e:
            print(e)
        times += 1

        if times % 10 == 0:
            time.sleep(60)

def main():
    jobs = get_repo_list()

    for job in jobs:
        tags, total = get_tags(job)

        list_gray = []
        list_merge = []
        list_other = []

        for tag in tags:
            if 'merge' in tag:
                list_merge.append(tag)
            elif 'gray' in tag:
                list_gray.append(tag)
            else:
                list_other.append(tag)
        print("{:35} merge:{:<5} gray:{:<5} other:{:<5} total:{:<5}".format(job, len(list_merge), len(list_gray), len(list_other), total))
        list_merge.sort(key=lambda x:int(x.split('-')[2]))
        delete_images(job, list_merge, namespace)
        delete_images(job, list_gray, namespace)

if __name__ == "__main__":
    main()
