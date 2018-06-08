# coding=utf-8
import os
import random

import chardet
import requests
import re
import logging
import time
from bs4 import BeautifulSoup as bs
import pymysql

db = pymysql.connect("localhost", "root", "Mlf7netS", "v-tree")

cursor = db.cursor()
db.set_charset('utf8')
"""
爬取字幕库的字幕文件
"""
proxies = {}


def switch_proxies(func):
    """
    爬取失败时切换代理
    """
    def get_sub(*args, **kwargs):
        result = func(*args, **kwargs)
        if not result: # 返回为None
            print('正在切换代理')
            get_proxies()
            result = func(*args, **kwargs)
            if not result:  # 如果下载依然失败则报错
                raise Exception('切换代理后函数依然无法正常工作')
        return result
    return get_sub


def url_iterator(start, end):
    """
    地址迭代器
    :param start: 开始下标
    :param end: 结束下标
    :return:
    """
    url = 'https://www.zimuku.cn/detail/{}.html'
    for index in range(start, end):
        yield index, url.format(index)


def filter_sub(html, lang, sub_format):
    """
    过滤器
    :param html: 网址HTML纯文本
    :param lang: 需要的字幕语言 暂支持： en-英语 ch-中文简体 tch-繁体中文
    :param sub_format: 需要的字幕格式 暂支持: srt， ass, ass/ssa
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

    soup = bs(html, 'lxml')
    try:
        _sub_lang = soup.select('.subinfo li')[0].img['title']
        logging.info(_sub_lang)
    except Exception as e:
        print('获取字幕语言失败')
        return False

    if _lang_dic[lang] != _sub_lang:
        return False

    try:
        _sub_format = soup.select('.subinfo li')[1].span.string
        logging.info(_sub_format)
    except IndexError as e:
        print('获取字幕格式失败')
        return False
    if _format_dic[sub_format] != _sub_format:
        return False

    return True


@switch_proxies
def get_dld_url(number):
    """
    获取字幕文件下载地址
    :param number:
    :return:
    """
    _url = 'http://www.subku.net/dld/{}.html'.format(number)
    try:
        r = requests.get(_url, proxies=proxies, timeout=20)
    except requests.exceptions.ProxyError as e:
        print(e, '该代理已过期或无法使用')
        return None
    except requests.exceptions.ConnectTimeout as e:
        print('代理服务器连接超时')
        return None
    # _dld_url = re.findall(r'href="(http://www.subku.net/download/.*?bk2)"', r.text)

    soup = bs(r.text, 'lxml')
    try:
        _dld_url = soup.select('.down')[0].find_all(name='li')[-2].a['href']
    except Exception as e:
        print(e, '获取下载地址失败')
        raise Exception('获取下载地址失败')
    return _dld_url


@switch_proxies
def get_sub_content(number, url):
    """
    获取字幕文件
    :param number:
    :param url:
    :return:
    """
    headers = {
        'referer': "http://www.subku.net/dld/{}.html".format(number),
    }
    try:
        res = requests.get(url, headers=headers, stream=True, proxies=proxies, timeout=20)
    except requests.exceptions.ProxyError as e:
        print('该代理已过期或无法使用')
        return None

    if res.status_code == 404 and res.history:  # 代理的情况下需要重新用响应的url再请求一遍
        res = requests.get(res.url)
        if res.status_code != 200:
            return None
    else:
        print(res.history, res.url)
        if len(re.findall('超出字幕下载次数', res.text)):
            print('超出字幕下载次数')
        logging.error('下载失败，且未获取到真实下载地址.')
        return None

    try:
        content_dis = res.headers['Content-Disposition']  # 获取头部文件信息
    except KeyError:
        print('获取content-disposition失败，文件可能损坏')
        logging.debug(res.text)
        return None

    try:
        filename = re.findall(r'filename="(.*?)"', content_dis)[0]
    except IndexError:
        print('获取文件名失败，文件可能损坏')
        logging.debug(res.text)
        return None
    return filename, res.content


def save(work_name_zh, work_name_en, sub_name, content):
    """
    保存到数据库
    :param work_name_zh: 作品中文名
    :param work_name_en: 作品英文名
    :param sub_name: 字幕名称
    :param content: 内容
    :return:
    """
    if not sub_name:
        print('字幕名为空')
        return
    if not content:
        print('文件内容为空')
        return
    guess = chardet.detect(content)

    if not guess['encoding']:
        print('无法识别编码，跳过')
        return
    text = content.decode(guess['encoding'], errors='ignore')

    # text = text.encode('utf-8')
    lines = text.split('\n')
    result = []
    pos = 0
    index = 0
    while pos < len(lines):  # 获取
        if lines[pos].strip().isdigit():
            pos += 2
            index += 1
        if len(lines[pos].strip()):
            result.append('{}: {}'.format(index, lines[pos]))
        pos += 1
    result = '\n'.join(result)
    try:
        sql = "INSERT INTO sub(work_name_zh, work_name_en, sub_name  , content) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (work_name_zh, work_name_en, sub_name, result))
    except Exception as e:
        print(e)
        db.rollback()
    db.commit()
    print('[√] {}'.format(work_name_zh))


def get_proxies():
    """
    获取代理
    """
    PROXY_POOL_HTTP = 'http://webapi.http.zhimacangku.com/getip?num=1&type=1&pro=&city=0&yys=0&port=11&time=1&ts=0&ys=0&' \
                     'cs=1&lb=1&sb=0&pb=4&mr=1&regions='

    try:
        global proxies
        response = requests.get(PROXY_POOL_HTTP)
        if response.status_code == 200:
            proxies['http'] = 'http://{}/'.format(response.text.strip('\r\n'))
        print('proxies:', proxies)
    except Exception as e:
        print(e)


def get_work_names(html):
    """
    获取电影/美剧的中文和英文名称
    电影/美剧名称是一大类，比如一个美剧可能有几个字幕文件
    :return:
    """
    soup = bs(html, 'lxml')
    result = soup.select('.md_tt')[0].a.string.split('/')
    return result[0], result[1]


def save_sub_cover(html, name):
    """
    保存电影封面
    :param html:
    :return:
    """
    soup = bs(html, 'lxml')
    img_url = soup.select('.md_img')[0].img['src']
    r = requests.get('http:{}'.format(img_url))

    if not os.path.exists('cover'):  # 不存在封面文件夹
        os.mkdir('cover')

    with open('cover/{}.jpg'.format(name), 'wb') as f:
        f.write(r.content)


def get_sub_name(html):
    """
    获取字幕名称
    :param html:
    :return:
    """
    soup = bs(html, 'lxml')
    return soup.select('.md_tt')[0].h1['title']


def main():

    get_proxies()

    start = 356

    end = 20000

    for index, url in url_iterator(start, end):
        # time.sleep(random.randint(2, 4))  # 友好的爬虫
        print('at : #', index)

        try:  # 获取字幕详情界面
            r = requests.get(url, proxies=proxies, timeout=20)
        except Exception as e:
            print('访问官网失败, 请检查网络: {}'.format(e))
            return

        if not filter_sub(r.text, 'en', 'srt'):  # 检测字幕语言和字幕格式
            continue
        work_names_zh, work_names_en = get_work_names(r.text)  # 获取电影/美剧名称
        sub_name = get_sub_name(r.text)  # 获取字幕名称
        save_sub_cover(r.text, work_names_zh)  # 保存字幕封面

        _dld_url = get_dld_url(number=index)

        name, content = get_sub_content(number=index, url=_dld_url)
        if not name.endswith('.srt'):
            print(name)
            print('非SRT文件，跳过')
            continue
        save(work_names_zh, work_names_en, sub_name, content)


if __name__ == '__main__':
    # logging.basicConfig(format="%(levelname)s : %(message)s", level=logging.INFO)
    main()
