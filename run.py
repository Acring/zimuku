# coding=utf-8
import os
import random

import requests
import re

import time

"""
爬取字幕库的字幕
"""


def url_iterator(start, end):
    """
    地址迭代器
    :param start: 开始下标
    :param end: 结束下标
    :return:
    """
    print('iter')
    url = 'https://www.zimuku.cn/detail/{}.html'
    for index in range(start, end):
        yield index, url.format(index)


def filter_sub(html, lang, sub_format):
    """
    过滤器
    :param html: 网址HTML纯文本
    :param lang: 需要的字幕语言 暂支持： en-英语 ch-中文简体 tch-繁体中文
    :param sub_format: 需要的字幕格式 暂支持: srt
    :return:
    """
    _lang_dic = {
        'en': 'English字幕',
        'ch': '简体中文字幕',
        'tch': '繁體中文字幕'
    }
    _format_dic = {
        'srt': 'SRT',
    }
    if isinstance(html, type(str)):
        raise TypeError('html should be str but it is {}'.format(type(html)))

    _sub_lang = re.findall(r'<b>字幕语言.*?alt="(.*?)"', html, re.S)

    if not len(_sub_lang):
        print('lang not found')
        return False

    _sub_lang = _sub_lang[0]
    if _lang_dic[lang] != _sub_lang:  # 该页面的字幕不符合
        return False

    _sub_format = re.findall(r'字幕格式：</b><span class="label label-info">(.*?)<', html, re.S)

    if not len(_sub_format):
        print('format not found')
        return False

    _sub_format = _sub_format[0]

    if _format_dic[sub_format] != _sub_format:
        return False

    return True


def get_sub(number):
    """
    获取字幕文件
    :param number: 要请求的的字幕序号
    :return: content
    """
    response = None
    try:
        s = requests.session()
        _url = 'http://www.subku.net/dld/{}.html'.format(number)
        proxy = get_proxy()
        while not proxy:
            print('获取代理失败')
            proxy = get_proxy()
        proxies = {'http': 'http://{}'.format(proxy)}
        print(proxies)
        r = s.get(_url, proxies=proxies, timeout=5)

        _dld_url = re.findall(r'href="(http://www.subku.net/download/.*?bk2)"', r.text)
        if _dld_url:
            _dld_url = _dld_url[0]
        else:
            print('无法获取下载链接')
            return None, None
        headers = {
            'referer': "http://www.subku.net/dld/{}.html".format(number),
            'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.\
            0.3325.181 Safari/537.36",
            'host': "www.subku.net",
            'accept-encoding': "gzip, deflate",
            'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            'upgrade-insecure-requests': "1",
            'accept-language': "zh-CN,zh;q=0.9,en;q=0.8",
            "proxy-connection": "keep-alive"
        }

        response = s.get(_dld_url, headers=headers, stream=True, proxies=proxies, timeout=5)
        if not response.ok:  # 获取失败
            print(number, response)
            return None, None
        content_dis = response.headers['Content-Disposition']
        if not content_dis:
            print(response.text)
            return None,None
        filename = re.findall(r'filename="(.*?)"', content_dis)
        if filename:
            filename = filename[0]
        else:
            print('获取文件名失败')
            print('header:', response)
            return None
        return filename, response.content

    except requests.ConnectTimeout as e:
        print('连接代理服务器超时:', e)
        return None, None
    except requests.ReadTimeout as e:
        print('读取代理服务器出错', e)
        return None, None
    except KeyError as e:
        print('无法获取请求头{}, 可能该代理已超过下载次数'.format(e))
        return None, None
    except Exception as e:
        print('其他错误:{}'.format(e))
        return None, None


def save(filename, content):
    if not os.path.exists('sub'):
        os.mkdir('sub')
    with open(os.path.join('sub', filename), 'wb') as f:
        f.write(content)
        print('file: {}, saved'.format(filename))

PROXY_POOL_URL = 'http://localhost:5555/random'


def get_proxy():

    try:
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            return response.text
    except ConnectionError:
        return None


def main():
    start = 1750
    end = 10000
    for index, url in url_iterator(start, end):
        if not index % 10:
            print('at : #', index)
        # time.sleep(random.randint(3, 7))
        r = requests.get(url, timeout=5)
        if not filter_sub(r.text, 'en', 'srt'):
            continue
        name, content = get_sub(index)
        while not content:
            name, content = get_sub(index)
        save(name, content)


if __name__ == '__main__':
    main()