#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股市新闻数据抓取主程序
功能：抓取新浪财经、东方财富、雪球的财经新闻，以及VIX指数数据
"""

import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 项目路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# VIX指数配置
VIX_SOURCES = {
    'Yahoo Finance': {
        'url': 'https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX',
        'type': 'api'
    },
    'CBOE VIX': {
        'url': 'https://www.cboe.com/tradable_products/vix/#mktDataWidget',
        'type': 'scrape'
    }
}

class NewsCrawler:
    """新闻抓取器基类"""
    
    def __init__(self, name):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def fetch(self, url, timeout=15):
        """通用请求方法"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            logger.error(f"[{self.name}] 请求失败 {url}: {e}")
            return None
            
    def parse(self, html):
        """解析方法，子类实现"""
        raise NotImplementedError

class SinaFinanceCrawler(NewsCrawler):
    """新浪财经新闻抓取"""
    
    def __init__(self):
        super().__init__('新浪财经')
        self.base_url = 'https://finance.sina.com.cn'
        
    def get_stock_news(self, category='stock'):
        """获取股票新闻"""
        news_list = []
        # 使用新浪财经的API接口
        urls = [
            'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&page=1',  # 股票
            'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2515&k=&num=20&page=1',  # 财经
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=10)
                data = response.json()
                
                if data.get('result'):
                    for item in data['result'].get('data', []):
                        news_list.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'source': '新浪财经',
                            'category': category,
                            'datetime': datetime.fromtimestamp(item.get('ctime', 0)).strftime('%Y-%m-%d %H:%M') if item.get('ctime') else '',
                            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
            except Exception as e:
                logger.error(f"[新浪财经] API请求失败: {e}")
                # 备用：网页抓取
                html = self.fetch('https://finance.sina.com.cn/stock/')
                if html:
                    soup = BeautifulSoup(html, 'lxml')
                    for item in soup.select('.news-item, .blk_hdline_01 li, a[href*="finance.sina"]'):
                        try:
                            title = item.get_text(strip=True)
                            link = item.get('href', '') or item.select_one('a')
                            if link and hasattr(link, 'get'):
                                link = link.get('href', '')
                            if title and len(title) > 10:
                                news_list.append({
                                    'title': title,
                                    'url': link if isinstance(link, str) else '',
                                    'source': '新浪财经',
                                    'category': category,
                                    'datetime': '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                        except:
                            continue
            
            time.sleep(0.5)
            
        return news_list[:30]
        
    def get_macro_news(self):
        """获取宏观新闻"""
        return self.get_stock_news(category='macro')

class EastMoneyCrawler(NewsCrawler):
    """东方财富新闻抓取"""
    
    def __init__(self):
        super().__init__('东方财富')
        self.api_base = 'https://np-anotice-stock.eastmoney.com'
        
    def get_news_list(self, page=1, type_=1):
        """通过API获取新闻列表
        type_: 1=A股, 2=港股, 3=美股
        """
        url = 'https://np-anotice-stock.eastmoney.com/api/security/ann'
        params = {
            'sr': '-1',
            'page_size': 20,
            'page_index': page,
            'type': type_,
            'code': '',
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()
            
            news_list = []
            if data.get('data'):
                for item in data['data'].get('list', []):
                    news_list.append({
                        'title': item.get('title', ''),
                        'url': f"https://data.eastmoney.com/news/{item.get('id', '')}.html",
                        'source': '东方财富',
                        'category': 'stock',
                        'datetime': item.get('notice_date', ''),
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
            return news_list
        except Exception as e:
            logger.error(f"[东方财富] API请求失败: {e}")
            return []
            
    def get_hot_news(self):
        """获取热门新闻"""
        urls = [
            'https://www.eastmoney.com/',
            'https://finance.eastmoney.com/',
        ]
        
        news_list = []
        for url in urls:
            html = self.fetch(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.news-list .item, .data-item, .feed-item'):
                    try:
                        title_elem = item.select_one('a, .title, h3')
                        link_elem = item.select_one('a')
                        time_elem = item.select_one('.time, .date')
                        
                        if title_elem:
                            news_list.append({
                                'title': title_elem.get_text(strip=True),
                                'url': link_elem.get('href', '') if link_elem else '',
                                'source': '东方财富',
                                'category': 'hot',
                                'datetime': time_elem.get_text(strip=True) if time_elem else '',
                                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                    except:
                        continue
            time.sleep(1)
            
        return news_list[:20]

class XueqiuCrawler(NewsCrawler):
    """雪球新闻抓取"""
    
    def __init__(self):
        super().__init__('雪球')
        self.api_base = 'https://xueqiu.com'
        
    def get_hot_discussions(self):
        """获取雪球热帖"""
        news_list = []
        
        try:
            self.session.get(self.api_base, timeout=10)
            url = 'https://xueqiu.com/statuses/hot/listV2.json?since_id=-1&max_id=-1&size=20'
            response = self.session.get(url, timeout=15)
            data = response.json()
            
            for item in data.get('items', []):
                original = item.get('original_status', {})
                news_list.append({
                    'title': original.get('title') or original.get('text', '')[:50],
                    'url': f"https://xueqiu.com/{original.get('user', {}).get('id', '')}/{original.get('id', '')}",
                    'source': '雪球',
                    'category': 'discussion',
                    'datetime': datetime.fromtimestamp(original.get('created_at', 0)/1000).strftime('%Y-%m-%d %H:%M') if original.get('created_at') else '',
                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            logger.error(f"[雪球] 获取失败: {e}")
        
        return news_list[:20]

class WallstreetcnCrawler(NewsCrawler):
    """华尔街见闻新闻抓取"""
    
    def __init__(self):
        super().__init__('华尔街见闻')
        
    def get_news(self):
        """获取快讯"""
        news_list = []
        
        try:
            url = 'https://api-one.wallstcn.com/apiv1/content/articles'
            params = {'channel': 'global-channel', 'limit': 20}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            for item in data.get('data', {}).get('items', []):
                news_list.append({
                    'title': item.get('title', ''),
                    'url': item.get('uri', ''),
                    'source': '华尔街见闻',
                    'category': 'macro',
                    'datetime': datetime.fromtimestamp(item.get('display_time', 0)).strftime('%Y-%m-%d %H:%M') if item.get('display_time') else '',
                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            logger.error(f"[华尔街见闻] 获取失败: {e}")
            
        return news_list


class TonghuashunCrawler(NewsCrawler):
    """同花顺财经新闻抓取"""
    
    def __init__(self):
        super().__init__('同花顺')
        self.api_base = 'https://news.10jqka.com.cn'
        
    def get_stock_news(self):
        """获取同花顺股票新闻"""
        news_list = []
        
        try:
            # 同花顺财经快讯API
            url = 'https://news.10jqka.com.cn/tapp/news/push/stock/?page=1&tag=&track=website&pagesize=20'
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('data'):
                for item in data['data'].get('list', []):
                    news_list.append({
                        'title': item.get('title', ''),
                        'url': item.get('art_url', ''),
                        'source': '同花顺',
                        'category': 'stock',
                        'datetime': item.get('ctime', ''),
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.error(f"[同花顺] 获取失败: {e}")
            # 备用：网页抓取
            html = self.fetch('https://news.10jqka.com.cn/')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.arc-list li, .news-list .item'):
                    try:
                        title_elem = item.select_one('a, h3, .tit')
                        link_elem = item.select_one('a')
                        time_elem = item.select_one('.time, .date')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 5:
                                news_list.append({
                                    'title': title,
                                    'url': link_elem.get('href', '') if link_elem else '',
                                    'source': '同花顺',
                                    'category': 'stock',
                                    'datetime': time_elem.get_text(strip=True) if time_elem else '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except:
                        continue
        
        return news_list[:20]


class NetEaseCrawler(NewsCrawler):
    """网易财经新闻抓取"""
    
    def __init__(self):
        super().__init__('网易财经')
        self.api_base = 'https://money.163.com'
        
    def get_stock_news(self):
        """获取网易财经股票新闻"""
        news_list = []
        
        try:
            # 网易财经快讯API
            url = 'https://api.money.126.net/data/feed/0000001,1399001?callback=a'
            response = self.session.get(url, timeout=10)
            data = response.text
            
            # 尝试解析JSONP
            if data.startswith('a('):
                import re
                json_str = re.search(r'a\((.*)\)', data)
                if json_str:
                    data = json.loads(json_str.group(1))
                    
        except Exception as e:
            logger.error(f"[网易财经] 获取失败: {e}")
        
        # 备用：网页抓取
        try:
            html = self.fetch('https://money.163.com/stock/')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.news_list li, .article-list .item'):
                    try:
                        title_elem = item.select_one('a')
                        time_elem = item.select_one('.time, .date')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 10:
                                news_list.append({
                                    'title': title,
                                    'url': title_elem.get('href', ''),
                                    'source': '网易财经',
                                    'category': 'stock',
                                    'datetime': time_elem.get_text(strip=True) if time_elem else '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except:
                        continue
        except Exception as e:
            logger.error(f"[网易财经] 网页抓取失败: {e}")
        
        return news_list[:20]
    
    def get_macro_news(self):
        """获取宏观经济新闻"""
        news_list = []
        
        try:
            html = self.fetch('https://money.163.com/macro/')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.article-list .item, .news_list li')[:15]:
                    try:
                        title_elem = item.select_one('a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 10:
                                news_list.append({
                                    'title': title,
                                    'url': title_elem.get('href', ''),
                                    'source': '网易财经',
                                    'category': 'macro',
                                    'datetime': '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except:
                        continue
        except Exception as e:
            logger.error(f"[网易财经] 宏观新闻获取失败: {e}")
        
        return news_list


class TencentCrawler(NewsCrawler):
    """腾讯财经新闻抓取"""
    
    def __init__(self):
        super().__init__('腾讯财经')
        self.api_base = 'https://finance.qq.com'
        
    def get_stock_news(self):
        """获取腾讯财经股票新闻"""
        news_list = []
        
        try:
            # 腾讯财经快讯API
            url = 'https://finance.qq.com/act/NewsCrawlService/getNewsList.htm?apptype=&action=click&page=0&pageSize=20&type=0'
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('data'):
                for item in data['data']:
                    news_list.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'source': '腾讯财经',
                        'category': 'stock',
                        'datetime': item.get('datetime', ''),
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.error(f"[腾讯财经] API获取失败: {e}")
        
        # 备用：网页抓取
        try:
            html = self.fetch('https://finance.qq.com/stock/')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.list .item, .news-list li'):
                    try:
                        title_elem = item.select_one('a')
                        time_elem = item.select_one('.time, .date')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 5:
                                news_list.append({
                                    'title': title,
                                    'url': title_elem.get('href', ''),
                                    'source': '腾讯财经',
                                    'category': 'stock',
                                    'datetime': time_elem.get_text(strip=True) if time_elem else '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except:
                        continue
        except Exception as e:
            logger.error(f"[腾讯财经] 网页抓取失败: {e}")
        
        return news_list[:20]


class CLSQCrawler(NewsCrawler):
    """财联社新闻抓取"""
    
    def __init__(self):
        super().__init__('财联社')
        self.api_base = 'https://www.cls.cn'
        
    def get_flash_news(self):
        """获取财联社电报快讯"""
        news_list = []
        
        try:
            # 财联社API
            url = 'https://www.cls.cn/nodeapi/getSwiperNewsList'
            params = {
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '8.4.5',
                'page': 1,
                'size': 20
            }
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data'):
                for item in data['data'].get('roll_data', []):
                    news_list.append({
                        'title': item.get('title', '') or item.get('content', '')[:50],
                        'url': f"https://www.cls.cn/telegraph/{item.get('id', '')}",
                        'source': '财联社',
                        'category': 'flash',
                        'datetime': datetime.fromtimestamp(item.get('ctime', 0)).strftime('%Y-%m-%d %H:%M') if item.get('ctime') else '',
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.error(f"[财联社] API获取失败: {e}")
        
        # 备用：网页抓取
        try:
            html = self.fetch('https://www.cls.cn/telegraph')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.telegraph-list .item, .article-list li'):
                    try:
                        title_elem = item.select_one('a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 5:
                                news_list.append({
                                    'title': title,
                                    'url': title_elem.get('href', ''),
                                    'source': '财联社',
                                    'category': 'flash',
                                    'datetime': '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except:
                        continue
        except Exception as e:
            logger.error(f"[财联社] 网页抓取失败: {e}")
        
        return news_list[:20]


class CSCCrawler(NewsCrawler):
    """中国证券报新闻抓取"""
    
    def __init__(self):
        super().__init__('中证报')
        self.api_base = 'https://www.cs.com.cn'
        
    def get_news(self):
        """获取中国证券报新闻"""
        news_list = []
        
        try:
            html = self.fetch('https://www.cs.com.cn/zqbd/')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('.m_article-list li, .news-list .item, .article-list li')[:20]:
                    try:
                        title_elem = item.select_one('a')
                        time_elem = item.select_one('.time, .date, .time2')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 10:
                                href = title_elem.get('href', '')
                                if href and not href.startswith('http'):
                                    href = 'https://www.cs.com.cn' + href
                                news_list.append({
                                    'title': title,
                                    'url': href,
                                    'source': '中国证券报',
                                    'category': 'stock',
                                    'datetime': time_elem.get_text(strip=True) if time_elem else '',
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except:
                        continue
        except Exception as e:
            logger.error(f"[中国证券报] 获取失败: {e}")
        
        return news_list


class Jin10Crawler(NewsCrawler):
    """金十数据新闻抓取"""
    
    def __init__(self):
        super().__init__('金十数据')
        
    def get_flash_news(self):
        """获取快讯"""
        news_list = []
        
        try:
            url = 'https://flash-api.jin10.com/get_flash_list'
            params = {'channel': '-8200', 'vip': 1, 'max_time': ''}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            for item in data[:20]:
                news_list.append({
                    'title': item.get('content', '')[:50],
                    'url': f"https://www.jin10.com/flash/{item.get('id', '')}.html",
                    'source': '金十数据',
                    'category': 'macro',
                    'datetime': datetime.fromtimestamp(item.get('time', 0)).strftime('%Y-%m-%d %H:%M') if item.get('time') else '',
                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            logger.error(f"[金十数据] 获取失败: {e}")
            
        return news_list

class ReutersCrawler(NewsCrawler):
    """路透社新闻抓取"""
    
    def __init__(self):
        super().__init__('路透社')
        
    def get_china_news(self):
        """获取中国新闻"""
        news_list = []
        
        try:
            url = 'https://cn.reuters.com/news/china'
            html = self.fetch(url)
            
            if html:
                soup = BeautifulSoup(html, 'lxml')
                for item in soup.select('article, .story, .news-item'):
                    try:
                        title_elem = item.select_one('h3, h4, .title, a')
                        link_elem = item.select_one('a')
                        
                        if title_elem:
                            news_list.append({
                                'title': title_elem.get_text(strip=True),
                                'url': f"https://cn.reuters.com{link_elem.get('href', '')}" if link_elem and link_elem.get('href', '').startswith('/') else link_elem.get('href', '') if link_elem else '',
                                'source': '路透社',
                                'category': 'international',
                                'datetime': '',
                                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                    except:
                        continue
        except Exception as e:
            logger.error(f"[路透社] 获取失败: {e}")
            
        return news_list[:15]

class SinaMacroCrawler(NewsCrawler):
    """新浪财经宏观经济新闻"""
    
    def __init__(self):
        super().__init__('新浪宏观')
        
    def get_macro_news(self):
        """获取宏观经济新闻"""
        news_list = []
        
        try:
            url = 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2517&k=&num=20&page=1'
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('result'):
                for item in data['result'].get('data', []):
                    news_list.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'source': '新浪宏观',
                        'category': 'macro',
                        'datetime': datetime.fromtimestamp(item.get('ctime', 0)).strftime('%Y-%m-%d %H:%M') if item.get('ctime') else '',
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.error(f"[新浪宏观] 获取失败: {e}")
            
        return news_list

class VIXCrawler:
    """VIX恐慌指数抓取"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def get_vix_yahoo(self):
        """从Yahoo Finance获取VIX数据"""
        try:
            url = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX'
            response = self.session.get(url, timeout=15)
            data = response.json()
            
            result = data['chart']['result'][0]
            meta = result['meta']
            timestamps = result['timestamp']
            closes = result['indicators']['quote'][0]['close']
            
            # 获取最近数据点
            vix_data = []
            for i in range(-10, 0):  # 最近10个数据点
                vix_data.append({
                    'timestamp': datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d %H:%M'),
                    'value': round(closes[i], 2) if closes[i] else None
                })
            
            current_vix = closes[-1] if closes else None
            
            return {
                'source': 'Yahoo Finance',
                'current': round(current_vix, 2) if current_vix else None,
                'change': None,
                'change_pct': None,
                'history': vix_data,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"[VIX] Yahoo Finance获取失败: {e}")
            return None
            
    def get_vix_cboe(self):
        """从CBOE获取VIX数据"""
        try:
            url = 'https://cdn.cboe.com/api/global/us_indices/daily_prices/'
            # VIX daily data
            response = self.session.get(url + 'VIX_History.csv', timeout=15)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    last_line = lines[-1].split(',')
                    return {
                        'source': 'CBOE',
                        'current': float(last_line[4]) if len(last_line) > 4 else None,  # Close
                        'open': float(last_line[1]) if len(last_line) > 1 else None,
                        'high': float(last_line[2]) if len(last_line) > 2 else None,
                        'low': float(last_line[3]) if len(last_line) > 3 else None,
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
        except Exception as e:
            logger.error(f"[VIX] CBOE获取失败: {e}")
        return None
        
    def get_vix_data(self):
        """综合获取VIX数据"""
        # 优先使用Yahoo Finance
        vix_data = self.get_vix_yahoo()
        
        if not vix_data or not vix_data.get('current'):
            # 备用CBOE
            vix_data = self.get_vix_cboe()
            
        # 添加恐慌等级评估
        if vix_data and vix_data.get('current'):
            current = vix_data['current']
            if current < 15:
                vix_data['fear_level'] = '极低'
                vix_data['fear_description'] = '市场情绪极度乐观'
                vix_data['fear_color'] = '#4CAF50'
            elif current < 20:
                vix_data['fear_level'] = '较低'
                vix_data['fear_description'] = '市场情绪较为乐观'
                vix_data['fear_color'] = '#8BC34A'
            elif current < 25:
                vix_data['fear_level'] = '中性'
                vix_data['fear_description'] = '市场情绪平稳'
                vix_data['fear_color'] = '#FFC107'
            elif current < 30:
                vix_data['fear_level'] = '较高'
                vix_data['fear_description'] = '市场存在一定担忧'
                vix_data['fear_color'] = '#FF9800'
            else:
                vix_data['fear_level'] = '极高'
                vix_data['fear_description'] = '市场恐慌情绪严重'
                vix_data['fear_color'] = '#F44336'
                
        return vix_data

def crawl_all_news():
    """抓取所有来源的新闻"""
    logger.info("开始抓取新闻...")
    
    all_news = []
    
    # 新浪财经
    try:
        sina = SinaFinanceCrawler()
        sina_news = sina.get_stock_news()
        all_news.extend(sina_news)
        logger.info(f"新浪财经: 获取 {len(sina_news)} 条")
    except Exception as e:
        logger.error(f"新浪财经抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 新浪宏观
    try:
        sina_macro = SinaMacroCrawler()
        macro_news = sina_macro.get_macro_news()
        all_news.extend(macro_news)
        logger.info(f"新浪宏观: 获取 {len(macro_news)} 条")
    except Exception as e:
        logger.error(f"新浪宏观抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 东方财富
    try:
        eastmoney = EastMoneyCrawler()
        em_news = eastmoney.get_news_list(page=1)
        all_news.extend(em_news)
        logger.info(f"东方财富: 获取 {len(em_news)} 条")
    except Exception as e:
        logger.error(f"东方财富抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 同花顺
    try:
        tonghuashun = TonghuashunCrawler()
        ths_news = tonghuashun.get_stock_news()
        all_news.extend(ths_news)
        logger.info(f"同花顺: 获取 {len(ths_news)} 条")
    except Exception as e:
        logger.error(f"同花顺抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 网易财经
    try:
        netEase = NetEaseCrawler()
        ne_news = netEase.get_stock_news()
        all_news.extend(ne_news)
        logger.info(f"网易财经: 获取 {len(ne_news)} 条")
    except Exception as e:
        logger.error(f"网易财经抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 腾讯财经
    try:
        tencent = TencentCrawler()
        tx_news = tencent.get_stock_news()
        all_news.extend(tx_news)
        logger.info(f"腾讯财经: 获取 {len(tx_news)} 条")
    except Exception as e:
        logger.error(f"腾讯财经抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 财联社
    try:
        cls = CLSQCrawler()
        cls_news = cls.get_flash_news()
        all_news.extend(cls_news)
        logger.info(f"财联社: 获取 {len(cls_news)} 条")
    except Exception as e:
        logger.error(f"财联社抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 中国证券报
    try:
        csc = CSCCrawler()
        csc_news = csc.get_news()
        all_news.extend(csc_news)
        logger.info(f"中国证券报: 获取 {len(csc_news)} 条")
    except Exception as e:
        logger.error(f"中国证券报抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 雪球
    try:
        xueqiu = XueqiuCrawler()
        xq_news = xueqiu.get_hot_discussions()
        all_news.extend(xq_news)
        logger.info(f"雪球: 获取 {len(xq_news)} 条")
    except Exception as e:
        logger.error(f"雪球抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 华尔街见闻
    try:
        wallstreetcn = WallstreetcnCrawler()
        wscn_news = wallstreetcn.get_news()
        all_news.extend(wscn_news)
        logger.info(f"华尔街见闻: 获取 {len(wscn_news)} 条")
    except Exception as e:
        logger.error(f"华尔街见闻抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 金十数据
    try:
        jin10 = Jin10Crawler()
        jin10_news = jin10.get_flash_news()
        all_news.extend(jin10_news)
        logger.info(f"金十数据: 获取 {len(jin10_news)} 条")
    except Exception as e:
        logger.error(f"金十数据抓取失败: {e}")
    
    time.sleep(0.5)
    
    # 路透社中国
    try:
        reuters = ReutersCrawler()
        reuters_news = reuters.get_china_news()
        all_news.extend(reuters_news)
        logger.info(f"路透社: 获取 {len(reuters_news)} 条")
    except Exception as e:
        logger.error(f"路透社抓取失败: {e}")
    
    # 去重
    seen = set()
    unique_news = []
    for news in all_news:
        if news['title'] not in seen:
            seen.add(news['title'])
            unique_news.append(news)
    
    logger.info(f"去重后共 {len(unique_news)} 条新闻")
    return unique_news

def crawl_vix():
    """抓取VIX数据"""
    logger.info("开始抓取VIX数据...")
    vix_crawler = VIXCrawler()
    return vix_crawler.get_vix_data()

def save_data(news_list, vix_data):
    """保存数据到文件"""
    DATA_DIR.mkdir(exist_ok=True)
    
    # 按日期保存新闻 (news_YYYY-MM-DD.json)
    today_str = datetime.now().strftime("%Y-%m-%d")
    news_file = DATA_DIR / f'news_{today_str}.json'
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    logger.info(f"新闻数据已保存: {news_file}")
    
    # 同时保存一份带小时戳的备份（方便回溯）
    news_file_hourly = DATA_DIR / f'news_{datetime.now().strftime("%Y%m%d_%H")}.json'
    with open(news_file_hourly, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    
    # 保存VIX
    vix_file = DATA_DIR / 'vix_latest.json'
    with open(vix_file, 'w', encoding='utf-8') as f:
        json.dump(vix_data, f, ensure_ascii=False, indent=2)
    logger.info(f"VIX数据已保存: {vix_file}")
    
    # 保存所有历史VIX
    vix_history_file = DATA_DIR / 'vix_history.json'
    try:
        with open(vix_history_file, 'r', encoding='utf-8') as f:
            vix_history = json.load(f)
    except:
        vix_history = []
    
    if vix_data:
        vix_history.append(vix_data)
        # 只保留最近30天
        vix_history = vix_history[-720:]  # 假设每天24条，保留30天
        with open(vix_history_file, 'w', encoding='utf-8') as f:
            json.dump(vix_history, f, ensure_ascii=False, indent=2)
    
    return news_file, vix_file


def get_available_dates(days=7):
    """获取最近可用的日期列表"""
    available_dates = []
    today = datetime.now()
    
    for i in range(days):
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        news_file = DATA_DIR / f'news_{date_str}.json'
        if news_file.exists():
            available_dates.append(date_str)
    
    return available_dates


def load_news_by_date(date_str):
    """按日期加载新闻数据"""
    news_file = DATA_DIR / f'news_{date_str}.json'
    if news_file.exists():
        with open(news_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def main():
    """主函数"""
    logger.info("="*50)
    logger.info("股市新闻抓取任务开始")
    logger.info("="*50)
    
    # 抓取新闻
    news_list = crawl_all_news()
    
    # 抓取VIX
    vix_data = crawl_vix()
    
    # 保存数据
    news_file, vix_file = save_data(news_list, vix_data)
    
    logger.info("="*50)
    logger.info("抓取任务完成")
    logger.info("="*50)
    
    return news_list, vix_data

if __name__ == '__main__':
    main()
