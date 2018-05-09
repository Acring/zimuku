# coding=utf-8
import os
import random

import requests
import re
import logging
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


def get_dld_url(number):
    """
    获取字幕文件下载地址
    :param number:
    :return:
    """
    _url = 'http://www.subku.net/dld/{}.html'.format(number)

    r = requests.get(_url, timeout=5)

    _dld_url = re.findall(r'href="(http://www.subku.net/download/.*?bk2)"', r.text)
    if _dld_url:
        _dld_url = _dld_url[0]
    else:
        print('无法获取下载链接')
        raise Exception('无法获取下载链接')
    return _dld_url


def get_sub_content(number, url, proxies):
    """
    获取字幕文件
    :param number:
    :param url:
    :param proxies:
    :return:
    """
    print(proxies)
    headers = {
        'referer': "http://www.subku.net/dld/{}.html".format(number),
    }

    res = requests.get(url, headers=headers, stream=True, proxies=proxies)

    if res.status_code == 404 and res.history:  # 代理的情况下需要重新用响应的url再请求一遍
        res = requests.get(res.url)
        if res.status_code != 200:
            return None, None
    else:
        print(res.history, res.url)
        logging.error('下载失败，且未获取到真实下载地址.')
        return None, None

    try:
        content_dis = res.headers['Content-Disposition']  # 获取头部文件信息
    except KeyError:
        print('获取content-disposition失败，文件可能损坏')
        logging.debug(res.text)
        return None, None

    try:
        filename = re.findall(r'filename="(.*?)"', content_dis)[0]
    except IndexError:
        print('获取文件名失败，文件可能损坏')
        logging.debug(res.text)
        return None, None

    return filename, res.content


def save(filename, content):
    filename.replace(' ', '')
    if not os.path.exists('sub'):
        os.mkdir('sub')
    with open(os.path.join('sub', filename), 'wb') as f:
        f.write(content)
        print('[√] file: {}, saved'.format(filename[:30]))

PROXY_POOL_URL = 'http://webapi.http.zhimacangku.com/getip?num=1&type=1&pro=&city=0&yys=0&port=11&time=1&ts=0&ys=0&' \
                 'cs=1&lb=1&sb=0&pb=4&mr=1&regions='


def get_proxy():
    try:
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(e)
        return None


def main():
    proxy = get_proxy()
    proxies = {'http': 'http://{}/'.format(proxy.strip('\r\n'))} if proxy else None

    start = 12309
    end = 20000
    for index, url in url_iterator(start, end):
        error_count = 0

        print('at : #', index)
        time.sleep(random.randint(3, 5))  # 防止被拉入黑名单

        try:  # 获取字幕详情界面
            r = requests.get(url, timeout=5)
        except Exception as e:
            print('访问官网失败: {}'.format(e))
            r = None

        if not filter_sub(r.text, 'en', 'srt'):  # 检测字幕语言和字幕格式
            continue

        _dld_url = get_dld_url(index)

        name, content = get_sub_content(index, _dld_url, proxies)
        while not content:
            error_count += 1

            proxy = get_proxy()
            proxies = {'http': 'http://{}/'.format(proxy.strip('\r\n'))} if proxy else None

            name, content = get_sub_content(index, _dld_url, proxies)
            if error_count > 10:
                print('失败次数过多，程序退出')
                return

        save(name, content)


if __name__ == '__main__':
    main()
