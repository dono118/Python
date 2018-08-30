# 使用微信处理反爬抓取微信文章
# 一、引入模块
from pyquery import PyQuery as pq
import requests
from urllib.parse import urlencode
import pymongo
from config import *

# 参数设置
headers = {
    'Cookie': 'IPLOC=CN3100; SUID=3F9A2D651620940A00000000593501AD; SUV=1496646179483423; ABTEST=2|1496646063|v1; SNUID=63C771395C590C6C4DA62B9E5DA843E5; weixinIndexVisited=1; ppinf=5|1496647654|1497857254|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToyNzolRTclOEUlOEIlRTUlODUlODklRTYlOUQlQjB8Y3J0OjEwOjE0OTY2NDc2NTR8cmVmbmljazoyNzolRTclOEUlOEIlRTUlODUlODklRTYlOUQlQjB8dXNlcmlkOjQ0Om85dDJsdUJzVzdIYXl4M2tlWFpjZTdWWmNNX2NAd2VpeGluLnNvaHUuY29tfA; pprdig=xFuTU5F3rYPr-GxEdzubwrQZ7jX7ifkrTXkYt2AR7gz17xFKLcIlD5r91dsYOnH_RDub9VxG8vNpHf5fwEjxAs4qFEJTqW96oVvr1UZq3qXq-AhGxJEDqlo8g5O3ZXy_F80B8YndLpUVbWeQDfJFlrwBlQ-3PXME0lxEDeguSyY; sgid=08-28925681-AVk1BibbKicbvQn77cbUV9RKo; SUIR=63C771395C590C6C4DA62B9E5DA843E5; pgv_pvi=3861214208; pgv_si=s8617661440; PHPSESSID=3rs7b393svg890cc66tv5kp942; sct=3; JSESSIONID=aaaTpSE3q_s21beotLIXv; ppmdig=14967350130000006401a6de8aa6584a3ed50839343b064b; seccodeRight=success; successCount=2|Tue, 06 Jun 2017 07:50:44 GMT',
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
proxy = None


# 二、请求解析模块
# 1、构造url，进行微信关键词搜索
def get_url(KEYWORDS, page_num):
    base_url = 'http://weixin.sogou.com/weixin?'
    data = {
        'type': '2',
        's_from': 'input',
        'query': KEYWORDS,
        'page': page_num,
        'ie': 'utf8',
        '_sug_': 'y',
        '_sug_type': ''
    }
    data = urlencode(data)
    url = base_url + data
    return url


# 2、请求url，得到索引页html
def get_index_html(url):
    print('正在爬取', url)
    global proxy
    try:
        if proxy:
            print('正在使用代理', proxy)
            proxies = {
                'http': 'http://' + proxy
            }
            response = requests.get(url, headers=headers, allow_redirects=False, proxies=proxies)
        else:
            response = requests.get(url, headers=headers, allow_redirects=False)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            # Need proxy
            print('302')
            proxy = get_proxy()
            if proxy:
                return get_index_html(url)
            else:
                print('请求代理失败')
                return None

    except Exception:
        proxy = get_proxy()
        return get_index_html(url)


# 3、请求url过程中，可能会遇到反爬虫措施，这时候需要开启代理
def get_proxy():
    print('正在请求代理')
    try:
        response = requests.get(POOL_PROXY_URL)
        if response.status_code == 200:
            return response.text
        else:
            print('请求代理失败')
            return None
    except Exception:
        return None


# 4、分析索引页html代码，返回微信详情页url
def get_article_url(index_html):
    doc = pq(index_html)
    lis = doc('.news-box .news-list li').items()
    for item in lis:
        yield item.find('h3 a').attr('href')


# 5、请求微信详情页url，得到详情页html
def get_article_html(article_url):
    try:
        response = requests.get(article_url)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except ConnectionError:
        return None


# 6、分析详情页html代码，得到微信标题、公众号、发布日期，文章内容等信息
def parse_article_html(article_html):
    doc = pq(article_html)
    article_data = {
        'title': doc('#img-content .rich_media_title').text(),
        'nickname': doc('.rich_media_meta_list .rich_media_meta_nickname').text(),
        'date': doc('.rich_media_meta_list #post-date').text(),
        'wechat': doc('#js_profile_qrcode > div > p:nth-child(3) > span').text(),
        'content': doc('.rich_media_content').text()
    }
    # print(article_data)
    return article_data


# 三、存储模块
# 保存到数据库MongoDB
def save_to_mongo(article_data):
    try:
        if db[MONGO_TABLE].insert_one(article_data):
            print('保存到MONGODB成功', article_data)
    except Exception:
        print('保存到MONGODB失败！', article_data)


# 四、调试模块
def main():
    for page_num in range(1, 101):
        index_url = get_url(KEYWORDS, page_num)
        # print(index_url)
        index_html = get_index_html(index_url)
        if index_html:
            article_urls = get_article_url(index_html)
            for article_url in article_urls:
                # print(article_url)
                article_html = get_article_html(article_url)
                if article_html:
                    article_data = parse_article_html(article_html)
                    print(article_data)
                    save_to_mongo(article_data)


if __name__ == '__main__':
    main()
