import requests
import re

number = 11575

proxy = {'http': 'http://182.99.251.68:1659/'}

_url = 'http://www.subku.net/dld/{}.html'.format(number)

r = requests.get(_url, timeout=5)
_dld_url = re.findall(r'href="(http://www.subku.net/download/.*?bk2)"', r.text)[0]

headers = {
    'referer': "http://www.subku.net/dld/{}.html".format(number),

}

response = requests.get(_dld_url, headers=headers, proxies=proxy,  timeout=5)
print(response.status_code)
print(_dld_url)
print(response.url)
print(response.text)
print(response.headers)
print(response.history)

# headers = {
#     'referer': "http://www.subku.net/dld/{}.html".format(number),
#     'host': "backup.zimuku.cn",
#
# }

r = requests.get(response.url,  )
# print(r.text)
print(r.url)
print(r.history)
print(r.headers)
