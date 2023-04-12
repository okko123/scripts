import json
import requests
import re

nexus_user = "admin"
nexus_pass = "password"

nexus_url = "http://192.168.0.1:8081/repository/springcloud-hosted/v2"
registry_url = "{}/_catalog".format(nexus_url)

def delete_image(tag_list, name):
    for tag in tag_list:
        digest_url = "{}/{}/manifests/{}".format(nexus_url, name, tag)
        r = requests.head(digest_url, auth=(nexus_user, nexus_pass), headers={"Accept":"application/vnd.docker.distribution.manifest.v2+json"})

        if r.ok:
            header = r.headers
            digest = header["Docker-Content-Digest"]
            del_url = "{}/{}/manifests/{}".format(nexus_url, name, digest)
            r = requests.delete(del_url, auth=(nexus_user, nexus_pass))

r = requests.get(registry_url, auth=(nexus_user, nexus_pass))

if r.ok:
    image_name_list = json.loads(r.text)
else:
    print(r.text)

for image_name in image_name_list["repositories"]:
    image_tags_url = "{}/{}/tags/list".format(nexus_url, image_name)
    r = requests.get(image_tags_url, auth=(nexus_user, nexus_pass))

    if r.ok:
        debug_list = []

        tags = json.loads(r.text)

        for tag in tags["tags"]:
            if re.search("debug", tag):
                debug_list.append(tag)

        del_list_debug = debug_list[:-7]

        delete_image(del_list_debug, image_name)
