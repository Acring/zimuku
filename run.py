# coding=utf-8
import os
import random
import requests
import re
import logging
import time

"""
爬取字幕库的字幕文件
"""

def wrapper(func):
    """
    爬取失败时切换代理
    """
    def get_sub(number, proxies):
        name, content = func(number, proxies)
        if not name: # 返回为None
            proxies = get_proxies()
            name, conent = func(number, proxies)
            if not name:  # 如果下载依然失败则报错
                raise Exception('发生未知错误，下载失败')
        return name, content
    return get_sub

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
        'tch': '繁體中文字幕',
        'mul': '双语字幕'
    }
    _format_dic = {
        'srt': 'SRT',
        'ass': 'ASS',
        'ass/ssa': 'ASS/SSA'
    }
    if isinstance(html, type(str)):
        raise TypeError('html should be str but it is {}'.format(type(html)))
    if lang not in _lang_dic:
        raise KeyError('Lang should be one of(en,ch, tch, mul) but it is {}'.format(lang))
    if sub_format not in _format_dic:
        raise KeyError('sub_format should be one of(srt, ass, ass/ssa)')

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


def get_dld_url(number, proxies):
    """
    获取字幕文件下载地址
    :param number:
    :return:
    """
    _url = 'http://www.subku.net/dld/{}.html'.format(number)
    try:
        r = requests.get(_url, proxies=proxies)
    except requests.exceptions.ProxyError as e:
        print('该代理已过期或无法使用')
        return None
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
    headers = {
        'referer': "http://www.subku.net/dld/{}.html".format(number),
    }
    try:
        res = requests.get(url, headers=headers, stream=True, proxies=proxies)
    except requests.exceptions.ProxyError as e:
        print('该代理已过期或无法使用')
        return None, None

    if res.status_code == 404 and res.history:  # 代理的情况下需要重新用响应的url再请求一遍
        res = requests.get(res.url)
        if res.status_code != 200:
            return None, None
    else:
        print(res.history, res.url)
        print(res.text)
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
    """
    保存获取到的文件
    :param filename: 获取文件名
    :param content: 文件内容
    """
    if not filename :
        print('文件名为空')
        return
    if not content:
        print('文件内容为空')
        return
    filename.replace(' ', '')
    if not os.path.exists('sub'):
        os.mkdir('sub')
    with open(os.path.join('sub', filename), 'wb') as f:
        f.write(content)
        print('[√] file: {}, saved'.format(filename[:30]))



def get_proxies():
    """
    获取代理
    """
    PROXY_POOL_HTTP = 'http://webapi.http.zhimacangku.com/getip?num=1&type=1&pro=&city=0&yys=0&port=11&time=1&ts=0&ys=0&' \
                     'cs=1&lb=1&sb=0&pb=4&mr=1&regions='

    try:
        proxies = {}
        response = requests.get(PROXY_POOL_HTTP)
        if response.status_code == 200:
            proxies['http'] = 'http://{}/'.format(response.text.strip('\r\n'))

        print('proxies:', proxies)
        return proxies
    except Exception as e:
        print(e)
        return None


def main():

    proxies = get_proxies()

    start = 15895
    end = 20000

    for index, url in url_iterator(start, end):
        error_count = 0

        print('at : #', index)

        try:  # 获取字幕详情界面
            r = requests.get(url, proxies=proxies)
        except Exception as e:
            print('访问官网失败, 请检查网络: {}'.format(e))
            return

        if not filter_sub(r.text, 'en', 'srt'):  # 检测字幕语言和字幕格式
            continue


        _dld_url = get_dld_url(index, proxies)

        name, content = get_sub_content(index, _dld_url, proxies)

        save(name, content)


if __name__ == '__main__':
    main()
