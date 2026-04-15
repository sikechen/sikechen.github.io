#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML页面生成器
功能：将分析结果生成为静态HTML页面，支持日期选择查看历史新闻
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from sentiment_analyzer import SentimentAnalyzer, MarketPredictor

# 项目路径
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / 'output'
TEMPLATE_DIR = BASE_DIR / 'templates'
DATA_DIR = BASE_DIR / 'data'

def get_available_dates(days=7):
    """获取最近可用的日期列表"""
    available_dates = []
    today = datetime.now()
    
    for i in range(days):
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        news_file = DATA_DIR / f'news_{date_str}.json'
        if news_file.exists():
            available_dates.append({
                'date': date_str,
                'label': _get_date_label(date_str),
                'is_today': i == 0
            })
    
    return available_dates

def _get_date_label(date_str):
    """获取日期显示标签"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if date_str == today:
        return "今天"
    elif date_str == yesterday:
        return "昨天"
    else:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        if date_str == day_before_yesterday:
            return "前天"
        else:
            return f"{dt.month}月{dt.day}日"

def load_data(date_str=None):
    """加载指定日期的数据，默认加载今天"""
    # 确定日期
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 尝试加载指定日期的新闻
    news_file = DATA_DIR / f'news_{date_str}.json'
    news_list = []
    loaded_date = date_str
    
    if news_file.exists():
        with open(news_file, 'r', encoding='utf-8') as f:
            news_list = json.load(f)
    else:
        # 如果指定日期没有数据，尝试获取最近可用的日期
        available = get_available_dates()
        if available:
            loaded_date = available[0]['date']
            news_file = DATA_DIR / f'news_{loaded_date}.json'
            if news_file.exists():
                with open(news_file, 'r', encoding='utf-8') as f:
                    news_list = json.load(f)
    
    # 加载VIX
    vix_file = DATA_DIR / 'vix_latest.json'
    vix_data = {}
    if vix_file.exists():
        with open(vix_file, 'r', encoding='utf-8') as f:
            vix_data = json.load(f)
    
    # 加载VIX历史
    vix_history_file = DATA_DIR / 'vix_history.json'
    vix_history = []
    if vix_history_file.exists():
        with open(vix_history_file, 'r', encoding='utf-8') as f:
            vix_history = json.load(f)
    
    return news_list, vix_data, vix_history, loaded_date

def load_all_news_data():
    """加载所有可用日期的新闻数据"""
    all_news_data = {}
    
    for date_info in get_available_dates():
        date_str = date_info['date']
        news_file = DATA_DIR / f'news_{date_str}.json'
        if news_file.exists():
            try:
                with open(news_file, 'r', encoding='utf-8') as f:
                    all_news_data[date_str] = json.load(f)
            except:
                pass
    
    return all_news_data

def generate_html(news_list, vix_data, vix_history, loaded_date=None, available_dates=None):
    """生成HTML页面"""
    # 获取可用日期列表
    if available_dates is None:
        available_dates = get_available_dates()
    
    # 当前加载的日期
    if loaded_date is None and news_list:
        # 从新闻数据中获取日期
        for news in news_list:
            if news.get('fetch_time'):
                loaded_date = news['fetch_time'][:10]
                break
    
    # 情感分析
    analyzer = SentimentAnalyzer()
    predictor = MarketPredictor()
    
    analyzed_news = analyzer.analyze_batch(news_list)
    summary = predictor.generate_summary(vix_data, analyzed_news)
    sector_analysis = predictor.analyze_sectors(analyzed_news)  # 板块分析
    
    # 获取所有新闻来源列表
    sources = list(set([n.get('source', '未知') for n in analyzed_news]))
    sources.sort()
    
    # 生成VIX图表数据 - 按天聚合
    vix_chart_data = []
    if vix_history:
        # 按日期分组，每天取最后一个数据点
        daily_data = {}
        for item in vix_history:
            if item.get('current') and item.get('fetch_time'):
                date_key = item['fetch_time'][:10]  # YYYY-MM-DD
                daily_data[date_key] = item['current']
        
        # 按日期排序，取最近14天
        sorted_dates = sorted(daily_data.keys())[-14:]
        vix_chart_data = [
            {'time': date, 'value': daily_data[date]}
            for date in sorted_dates
        ]
    
    # 情感分布
    sentiment_dist = {
        'positive': sum(1 for n in analyzed_news if n.get('sentiment') == 'positive'),
        'neutral': sum(1 for n in analyzed_news if n.get('sentiment') == 'neutral'),
        'negative': sum(1 for n in analyzed_news if n.get('sentiment') == 'negative')
    }
    
    # 按市场分类
    a_stock_news = [n for n in analyzed_news if 'A股' in n.get('markets', [])]
    us_stock_news = [n for n in analyzed_news if '美股' in n.get('markets', [])]
    hk_stock_news = [n for n in analyzed_news if '港股' in n.get('markets', [])]
    other_news = [n for n in analyzed_news if '综合' in n.get('markets', [])]
    
    # 加载所有日期的新闻数据用于前端切换（需要先进行分析处理）
    all_news_data = {}
    for date_info in available_dates:
        date_str = date_info['date']
        news_file = DATA_DIR / f'news_{date_str}.json'
        if news_file.exists():
            try:
                with open(news_file, 'r', encoding='utf-8') as f:
                    raw_news = json.load(f)
                    # 对原始新闻进行分析，添加 sentiment 和 markets 字段
                    analyzed_raw_news = analyzer.analyze_batch(raw_news)
                    all_news_data[date_str] = analyzed_raw_news
            except:
                pass
    
    # 生成HTML
    html = generate_html_template(
        vix_data=vix_data,
        summary=summary,
        analyzed_news=analyzed_news,
        sentiment_dist=sentiment_dist,
        vix_chart_data=vix_chart_data,
        a_stock_news=a_stock_news,
        us_stock_news=us_stock_news,
        hk_stock_news=hk_stock_news,
        other_news=other_news,
        sector_analysis=sector_analysis,
        available_dates=available_dates,
        loaded_date=loaded_date,
        sources=sources,
        all_news_data=all_news_data
    )
    
    return html

def generate_html_template(vix_data, summary, analyzed_news, sentiment_dist, 
                           vix_chart_data, a_stock_news, us_stock_news, 
                           hk_stock_news, other_news, sector_analysis,
                           available_dates=None, loaded_date=None, sources=None, all_news_data=None):
    """生成完整HTML模板"""
    
    # 设置默认值
    if available_dates is None:
        available_dates = []
    if sources is None:
        sources = []
    if all_news_data is None:
        all_news_data = {}
    
    current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    # 加载日期的显示标签
    loaded_date_label = _get_date_label(loaded_date) if loaded_date else "今天"
    
    # 生成日期选择器HTML
    date_selector_html = ''
    for date_info in available_dates:
        is_active = date_info['date'] == loaded_date
        active_class = 'active' if is_active else ''
        date_selector_html += f'''
            <button class="date-btn {active_class}" data-date="{date_info['date']}" onclick="loadNewsByDate('{date_info['date']}')">
                <span class="date-label">{date_info['label']}</span>
            </button>
        '''
    
    # 将所有日期的新闻数据嵌入到页面中
    all_news_data_json = json.dumps(all_news_data, ensure_ascii=False)
    
    # 生成来源标签HTML
    source_tags_html = ''
    source_count = len(sources)
    for source in sources:
        source_tags_html += f'<span class="source-tag">{source}</span>'
    
    # VIX数据
    vix_value = vix_data.get('current', 'N/A')
    vix_fear_level = vix_data.get('fear_level', '未知')
    vix_fear_desc = vix_data.get('fear_description', '')
    vix_fear_color = vix_data.get('fear_color', '#666')
    
    # 预测摘要
    vix_pred = summary.get('vix_prediction', {})
    sentiment_pred = summary.get('sentiment_prediction', {})
    overall_pred = summary.get('overall_prediction', '数据不足')
    risk_level = summary.get('risk_level', '未知')
    key_points = summary.get('key_points', [])
    
    # VIX图表JSON
    vix_chart_json = json.dumps(vix_chart_data, ensure_ascii=False)
    
    # ECharts配置 - VIX走势
    vix_chart_option = {
        "title": {"text": "VIX恐慌指数走势（近14天）", "left": "center", "textStyle": {"fontSize": 14}},
        "tooltip": {"trigger": "axis", "formatter": "{b}<br/>VIX: {c}"},
        "grid": {"left": "10%", "right": "10%", "bottom": "20%", "top": "20%"},
        "xAxis": {
            "type": "category",
            "data": [d['time'] for d in vix_chart_data] if vix_chart_data else [],
            "axisLabel": {"rotate": 30, "fontSize": 11, "interval": 0}
        },
        "yAxis": {"type": "value", "scale": True, "name": "VIX"},
        "series": [{
            "type": "line",
            "data": [d['value'] for d in vix_chart_data] if vix_chart_data else [],
            "smooth": True,
            "areaStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "rgba(238,102,102,0.5)"},
                        {"offset": 1, "color": "rgba(238,102,102,0.05)"}
                    ]
                }
            },
            "lineStyle": {"color": "#ee6666", "width": 2},
            "itemStyle": {"color": "#ee6666"},
            "markLine": {
                "silent": True,
                "data": [
                    {"yAxis": 20, "name": "恐慌阈值", "lineStyle": {"color": "#FFC107"}},
                    {"yAxis": 30, "name": "极度恐慌", "lineStyle": {"color": "#F44336"}}
                ]
            }
        }]
    }
    
    # 情感分布图表配置
    sentiment_chart_option = {
        "title": {"text": "市场情绪分布", "left": "center", "textStyle": {"fontSize": 14}},
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "series": [{
            "type": "pie",
            "radius": ["40%", "70%"],
            "avoidLabelOverlap": False,
            "itemStyle": {"borderRadius": 5, "borderColor": "#fff", "borderWidth": 2},
            "label": {"show": True, "formatter": "{b}: {d}%"},
            "data": [
                {"value": sentiment_dist['positive'], "name": "积极", "itemStyle": {"color": "#4CAF50"}},
                {"value": sentiment_dist['neutral'], "name": "中性", "itemStyle": {"color": "#FFC107"}},
                {"value": sentiment_dist['negative'], "name": "消极", "itemStyle": {"color": "#F44336"}}
            ]
        }]
    }
    
    # 新闻列表HTML
    def render_news_list(news, max_count=15):
        html_parts = []
        for i, item in enumerate(news[:max_count]):
            sentiment = item.get('sentiment', 'neutral')
            sentiment_icon = {'positive': '📈', 'negative': '📉', 'neutral': '➖'}.get(sentiment, '➖')
            sentiment_class = f"sentiment-{sentiment}"
            
            # 地缘政治新闻标记
            geopolitical = item.get('geopolitical', False)
            geopolitical_keywords = item.get('geopolitical_keywords', [])
            war_impact = item.get('war_impact', False)
            
            # 特殊标记
            special_badge = ''
            if geopolitical:
                special_badge = '<span class="geo-badge">🌍 地缘政治</span>'
            
            # 截取标题
            title = item.get('title', '')[:60]
            if len(item.get('title', '')) > 60:
                title += '...'
            
            # 关键词显示
            keywords_html = ''
            if geopolitical_keywords:
                keywords_html += " ".join([f'<span class="kw geo-kw">{kw}</span>' for kw in geopolitical_keywords[:2]])
            if item.get('keywords'):
                keywords_html += " ".join([f'<span class="kw">{kw}</span>' for kw in item.get('keywords', [])[:2]])
            
            html_parts.append(f'''
                <div class="news-item {sentiment_class} {"geopolitical" if geopolitical else ""}">
                    <div class="news-header">
                        <span class="sentiment-badge {sentiment_class}">{sentiment_icon}</span>
                        {special_badge}
                        <span class="news-source">{item.get('source', '')}</span>
                        <span class="news-time">{item.get('datetime', '')}</span>
                    </div>
                    <a href="{item.get('url', '#')}" class="news-title" target="_blank">{title}</a>
                    <div class="news-keywords">
                        {keywords_html}
                    </div>
                </div>
            ''')
        return '\n'.join(html_parts)
    
    a_stock_html = render_news_list(a_stock_news)
    us_stock_html = render_news_list(us_stock_news)
    hk_stock_html = render_news_list(hk_stock_news)
    other_html = render_news_list(other_news)
    
    # 关键新闻点
    key_points_html = ''
    for point in key_points[:6]:
        icon = '✅' if point['type'] == '利好' else '⚠️'
        key_points_html += f'''
            <div class="key-point {point['type']}">
                <span class="point-icon">{icon}</span>
                <span class="point-text">{point['title']}</span>
                <span class="point-source">来源:{point['source']}</span>
            </div>
        '''
    
    # 板块分析HTML
    def render_sector_analysis(sectors, max_count=8):
        html_parts = []
        for sector in sectors[:max_count]:
            # 趋势颜色
            if sector['trend'] == '强势':
                trend_color = '#4CAF50'
            elif sector['trend'] == '弱势':
                trend_color = '#F44336'
            else:
                trend_color = '#FFC107'
            
            # 变化级别颜色
            if sector['change_level'] == '剧烈变化':
                change_class = 'hot'
            elif sector['change_level'] == '明显变化':
                change_class = 'warm'
            else:
                change_class = 'normal'
            
            html_parts.append(f'''
                <div class="sector-item {change_class}">
                    <div class="sector-header">
                        <span class="sector-name">{sector['trend_icon']} {sector['sector']}</span>
                        <span class="sector-change">{sector['change_icon']} {sector['change_level']}</span>
                    </div>
                    <div class="sector-stats">
                        <span class="stat">新闻: <strong>{sector['total']}</strong></span>
                        <span class="stat positive">📈 {sector['positive']}</span>
                        <span class="stat negative">📉 {sector['negative']}</span>
                        <span class="stat">净情绪: <strong style="color:{trend_color}">{sector['net_sentiment']:+.1f}%</strong></span>
                    </div>
                    <div class="sector-bar">
                        <div class="bar-positive" style="width:{sector['positive_ratio']}%"></div>
                        <div class="bar-negative" style="width:{sector['negative_ratio']}%"></div>
                    </div>
                </div>
            ''')
        return '\n'.join(html_parts)
    
    sector_html = render_sector_analysis(sector_analysis)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股市情绪监控 | Stock Sentiment Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --primary: #1a73e8;
            --success: #4CAF50;
            --warning: #FFC107;
            --danger: #F44336;
            --bg: #f5f7fa;
            --card-bg: #ffffff;
            --text: #333;
            --text-light: #666;
            --border: #e0e0e0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* 头部 */
        .header {{
            background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .update-time {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        /* 日期选择器 */
        .date-selector {{
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }}
        
        .date-selector-label {{
            font-size: 13px;
            opacity: 0.9;
            margin-right: 10px;
            display: inline-block;
            margin-bottom: 10px;
        }}
        
        .date-btns {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        
        .date-btn {{
            padding: 6px 14px;
            border: 1px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.1);
            color: white;
            border-radius: 20px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        
        .date-btn:hover {{
            background: rgba(255,255,255,0.2);
        }}
        
        .date-btn.active {{
            background: white;
            color: #1a73e8;
            border-color: white;
            font-weight: 500;
        }}
        
        /* 新闻来源标签 */
        .source-filter {{
            margin-top: 15px;
        }}
        
        .source-filter-label {{
            font-size: 12px;
            opacity: 0.8;
            margin-right: 10px;
        }}
        
        .source-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }}
        
        .source-tag {{
            padding: 3px 10px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            font-size: 11px;
            color: rgba(255,255,255,0.9);
        }}
        
        .source-count {{
            font-size: 12px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        
        /* 指标卡片 */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        
        .metric-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .metric-card .label {{
            font-size: 13px;
            color: var(--text-light);
            margin-bottom: 8px;
        }}
        
        .metric-card .value {{
            font-size: 32px;
            font-weight: 700;
        }}
        
        .metric-card .sub {{
            font-size: 13px;
            color: var(--text-light);
            margin-top: 5px;
        }}
        
        .vix-card {{
            border-left: 4px solid {vix_fear_color};
        }}
        
        .vix-card .value {{
            color: {vix_fear_color};
        }}
        
        .risk-low {{ color: var(--success); }}
        .risk-medium {{ color: var(--warning); }}
        .risk-high {{ color: var(--danger); }}
        
        /* 图表区 */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        
        .chart-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .chart {{
            height: 300px;
        }}
        
        /* 新闻区 */
        .news-section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .news-tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 10px;
            flex-wrap: wrap;
        }}
        
        .news-tab {{
            padding: 8px 16px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 14px;
            color: var(--text-light);
            border-radius: 20px;
            transition: all 0.3s;
        }}
        
        .news-tab:hover {{
            background: #f0f0f0;
        }}
        
        .news-tab.active {{
            background: var(--primary);
            color: white;
        }}
        
        .news-content {{
            display: none;
        }}
        
        .news-content.active {{
            display: block;
        }}
        
        .news-item {{
            padding: 15px;
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }}
        
        .news-item:hover {{
            background: #f8f9fa;
        }}
        
        .news-item:last-child {{
            border-bottom: none;
        }}
        
        .news-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 12px;
            color: var(--text-light);
        }}
        
        .sentiment-badge {{
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }}
        
        .sentiment-positive {{
            background: rgba(76, 175, 80, 0.15);
            color: var(--success);
        }}
        
        .sentiment-neutral {{
            background: rgba(255, 193, 7, 0.15);
            color: #f57c00;
        }}
        
        .sentiment-negative {{
            background: rgba(244, 67, 54, 0.15);
            color: var(--danger);
        }}
        
        .news-title {{
            color: var(--text);
            text-decoration: none;
            font-size: 15px;
            display: block;
            margin-bottom: 8px;
        }}
        
        .news-title:hover {{
            color: var(--primary);
        }}
        
        .news-keywords {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        
        .kw {{
            background: #e8f0fe;
            color: var(--primary);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }}
        
        .geo-kw {{
            background: #fff3e0;
            color: #e65100;
            font-weight: 500;
        }}
        
        .geo-badge {{
            background: linear-gradient(135deg, #ff6b35, #f7931e);
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}
        
        .news-item.geopolitical {{
            background: linear-gradient(to right, #fff8f0, transparent);
            border-left: 3px solid #ff6b35;
        }}
        
        .news-item.geopolitical:hover {{
            background: linear-gradient(to right, #fff0e6, transparent);
        }}
        
        /* 板块分析 */
        .sector-section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .sector-item {{
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 3px solid #e0e0e0;
            transition: all 0.2s;
        }}
        
        .sector-item.hot {{
            background: linear-gradient(to right, #fff3f3, transparent);
            border-left-color: #F44336;
        }}
        
        .sector-item.warm {{
            background: linear-gradient(to right, #fff8f0, transparent);
            border-left-color: #FF9800;
        }}
        
        .sector-item.normal {{
            background: #fafafa;
            border-left-color: #e0e0e0;
        }}
        
        .sector-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .sector-name {{
            font-size: 16px;
            font-weight: 600;
        }}
        
        .sector-change {{
            font-size: 12px;
            padding: 3px 10px;
            border-radius: 12px;
            background: #f0f0f0;
        }}
        
        .sector-item.hot .sector-change {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .sector-item.warm .sector-change {{
            background: #fff3e0;
            color: #e65100;
        }}
        
        .sector-stats {{
            display: flex;
            gap: 15px;
            font-size: 13px;
            color: var(--text-light);
            margin-bottom: 10px;
        }}
        
        .sector-stats .stat {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        
        .sector-stats .positive {{
            color: var(--success);
        }}
        
        .sector-stats .negative {{
            color: var(--danger);
        }}
        
        .sector-bar {{
            height: 6px;
            background: #f0f0f0;
            border-radius: 3px;
            display: flex;
            overflow: hidden;
        }}
        
        .bar-positive {{
            background: var(--success);
            height: 100%;
        }}
        
        .bar-negative {{
            background: var(--danger);
            height: 100%;
        }}
        
        /* 关键新闻点 */
        .key-points {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .key-point {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 0;
            border-bottom: 1px dashed var(--border);
        }}
        
        .key-point:last-child {{
            border-bottom: none;
        }}
        
        .key-point .point-icon {{
            font-size: 18px;
        }}
        
        .key-point .point-text {{
            flex: 1;
            font-size: 14px;
        }}
        
        .key-point .point-source {{
            font-size: 12px;
            color: var(--text-light);
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-light);
            font-size: 12px;
        }}
        
        /* 响应式 */
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            .metric-card .value {{
                font-size: 24px;
            }}
        }}
        
        /* 预测卡片 */
        .prediction-banner {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .prediction-item {{
            text-align: center;
        }}
        
        .prediction-item .label {{
            font-size: 12px;
            opacity: 0.9;
        }}
        
        .prediction-item .value {{
            font-size: 18px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <header class="header">
            <h1>📊 股市情绪监控面板</h1>
            <p class="update-time">数据更新时间: {current_time} | 每2小时自动更新</p>
            
            <!-- 日期选择器 -->
            {date_selector_html if date_selector_html else ''}
            
            <!-- 新闻来源统计 -->
            <div class="source-filter">
                <span class="source-filter-label">📰 新闻来源 ({source_count}个):</span>
                <div class="source-tags">
                    {source_tags_html if source_tags_html else '<span class="source-tag">加载中...</span>'}
                </div>
                <div class="source-count">共 {len(analyzed_news)} 条新闻</div>
            </div>
        </header>
        
        <!-- 核心指标 -->
        <div class="metrics-grid">
            <div class="metric-card vix-card">
                <div class="label">VIX恐慌指数</div>
                <div class="value">{vix_value if vix_value != 'N/A' else '加载中...'}</div>
                <div class="sub" style="color: {vix_fear_color}">
                    情绪等级: {vix_fear_level} | {vix_fear_desc}
                </div>
            </div>
            <div class="metric-card">
                <div class="label">综合预测</div>
                <div class="value">{overall_pred}</div>
                <div class="sub">风险等级: <span class="risk-{'low' if risk_level == '低' else 'medium' if risk_level == '中' else 'high'}">{risk_level}</span></div>
            </div>
            <div class="metric-card">
                <div class="label">积极新闻</div>
                <div class="value" style="color: var(--success)">{sentiment_pred.get('positive_count', 0)}</div>
                <div class="sub">占比 {sentiment_pred.get('bull_ratio', 0)}%</div>
            </div>
            <div class="metric-card">
                <div class="label">消极新闻</div>
                <div class="value" style="color: var(--danger)">{sentiment_pred.get('negative_count', 0)}</div>
                <div class="sub">占比 {sentiment_pred.get('bear_ratio', 0)}%</div>
            </div>
        </div>
        
        <!-- 预测横幅 -->
        <div class="prediction-banner">
            <div class="prediction-item">
                <div class="label">VIX信号</div>
                <div class="value">{vix_pred.get('suggestion', '分析中')}</div>
            </div>
            <div class="prediction-item">
                <div class="label">情绪信号</div>
                <div class="value">{sentiment_pred.get('action', '观望')}</div>
            </div>
            <div class="prediction-item">
                <div class="label">新闻数量</div>
                <div class="value">{sentiment_pred.get('total_news', 0)}</div>
            </div>
        </div>
        
        <!-- 图表区 -->
        <div class="charts-grid">
            <div class="chart-card">
                <div id="vixChart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div id="sentimentChart" class="chart"></div>
            </div>
        </div>
        
        <!-- 板块分析 -->
        <div class="sector-section">
            <h3 style="margin-bottom: 15px;">🎯 板块智能分析</h3>
            <p style="font-size: 12px; color: var(--text-light); margin-bottom: 15px;">基于新闻数量和情绪变化分析各板块热度</p>
            {sector_html if sector_html else '<p style="color: var(--text-light);">暂无板块数据</p>'}
        </div>
        
        <!-- 关键新闻点 -->
        <div class="key-points">
            <h3 style="margin-bottom: 15px;">🔥 重要资讯速递</h3>
            {key_points_html if key_points_html else '<p style="color: var(--text-light);">暂无关键资讯</p>'}
        </div>
        
        <!-- 新闻列表 -->
        <div class="news-section">
            <div class="news-tabs">
                <button class="news-tab active" onclick="showTab('astock')">A股 ({len(a_stock_news)})</button>
                <button class="news-tab" onclick="showTab('usstock')">美股 ({len(us_stock_news)})</button>
                <button class="news-tab" onclick="showTab('hkstock')">港股 ({len(hk_stock_news)})</button>
                <button class="news-tab" onclick="showTab('other')">综合 ({len(other_news)})</button>
            </div>
            
            <div id="astock" class="news-content active">
                {a_stock_html if a_stock_html else '<p style="color: var(--text-light); padding: 20px;">暂无A股相关资讯</p>'}
            </div>
            <div id="usstock" class="news-content">
                {us_stock_html if us_stock_html else '<p style="color: var(--text-light); padding: 20px;">暂无美股相关资讯</p>'}
            </div>
            <div id="hkstock" class="news-content">
                {hk_stock_html if hk_stock_html else '<p style="color: var(--text-light); padding: 20px;">暂无港股相关资讯</p>'}
            </div>
            <div id="other" class="news-content">
                {other_html if other_html else '<p style="color: var(--text-light); padding: 20px;">暂无综合资讯</p>'}
            </div>
        </div>
        
        <!-- 页脚 -->
        <footer class="footer">
            <p>📈 股市情绪监控系统 | 数据来源: {', '.join(sources) if sources else '新浪财经、东方财富、同花顺、网易财经、腾讯财经、财联社、中国证券报、雪球、华尔街见闻、金十数据、路透社'}</p>
            <p>⚠️ 本页面仅供参考，不构成投资建议</p>
            <p>🔄 自动更新于 {current_time}</p>
        </footer>
    </div>
    
    <script>
        // 所有日期的新闻数据
        var allNewsData = {all_news_data_json};
        
        // 当前选中的日期
        var currentDate = '{loaded_date}';
        
        // 情感分析函数
        function analyzeSentiment(title, content) {{
            var positiveKeywords = ['涨', '利好', '突破', '增长', '上升', '创新高', '看涨', '强劲', '反弹', '大涨', '飙升', '收涨', '上涨'];
            var negativeKeywords = ['跌', '利空', '下跌', '暴跌', '创新低', '看跌', '疲软', '跳水', '崩盘', '大跌', '下滑', '收跌', '下跌'];
            
            var text = (title + ' ' + content).toLowerCase();
            var posCount = positiveKeywords.filter(k => text.includes(k)).length;
            var negCount = negativeKeywords.filter(k => text.includes(k)).length;
            
            if (posCount > negCount) return 'positive';
            if (negCount > posCount) return 'negative';
            return 'neutral';
        }}
        
        // 渲染新闻列表
        function renderNewsList(news, maxCount) {{
            var html = '';
            for (var i = 0; i < Math.min(news.length, maxCount); i++) {{
                var item = news[i];
                var sentiment = item.sentiment || analyzeSentiment(item.title || '', '');
                var sentimentIcon = {{'positive': '📈', 'negative': '📉', 'neutral': '➖'}}[sentiment] || '➖';
                var sentimentClass = 'sentiment-' + sentiment;
                var title = (item.title || '').substring(0, 60);
                if ((item.title || '').length > 60) title += '...';
                var geopolitical = item.geopolitical || false;
                var specialBadge = geopolitical ? '<span class="geo-badge">🌍 地缘政治</span>' : '';
                var url = item.url || '#';
                var source = item.source || '';
                var datetime = item.datetime || '';
                
                html += '<div class="news-item ' + sentimentClass + (geopolitical ? ' geopolitical' : '') + '">' +
                    '<div class="news-header">' +
                    '<span class="sentiment-badge ' + sentimentClass + '">' + sentimentIcon + '</span>' +
                    specialBadge +
                    '<span class="news-source">' + source + '</span>' +
                    '<span class="news-time">' + datetime + '</span>' +
                    '</div>' +
                    '<a href="' + url + '" class="news-title" target="_blank">' + title + '</a>' +
                    '</div>';
            }}
            return html || '<p style="color: var(--text-light); padding: 20px;">暂无相关新闻</p>';
        }}
        
        // 分类新闻
        function categorizeNews(news) {{
            var aStock = [], usStock = [], hkStock = [], other = [];
            var markets = news.markets || [];
            
            for (var i = 0; i < news.length; i++) {{
                var item = news[i];
                var m = item.markets || [];
                if (m.indexOf('A股') !== -1) aStock.push(item);
                else if (m.indexOf('美股') !== -1) usStock.push(item);
                else if (m.indexOf('港股') !== -1) hkStock.push(item);
                else other.push(item);
            }}
            return {{ astock: aStock, usstock: usStock, hkstock: hkStock, other: other }};
        }}
        
        // 切换日期
        function switchDate(date) {{
            var news = allNewsData[date];
            if (!news) return;
            
            currentDate = date;
            var categorized = categorizeNews(news);
            
            // 更新标签页数量
            document.querySelector('.news-tab:nth-child(1)').textContent = 'A股 (' + categorized.astock.length + ')';
            document.querySelector('.news-tab:nth-child(2)').textContent = '美股 (' + categorized.usstock.length + ')';
            document.querySelector('.news-tab:nth-child(3)').textContent = '港股 (' + categorized.hkstock.length + ')';
            document.querySelector('.news-tab:nth-child(4)').textContent = '综合 (' + categorized.other.length + ')';
            
            // 更新新闻内容
            document.getElementById('astock').innerHTML = renderNewsList(categorized.astock, 15);
            document.getElementById('usstock').innerHTML = renderNewsList(categorized.usstock, 15);
            document.getElementById('hkstock').innerHTML = renderNewsList(categorized.hkstock, 15);
            document.getElementById('other').innerHTML = renderNewsList(categorized.other, 15);
            
            // 更新来源统计
            var sources = {{}};
            for (var i = 0; i < news.length; i++) {{
                var s = news[i].source || '未知';
                sources[s] = (sources[s] || 0) + 1;
            }}
            var sourceTags = document.querySelector('.source-tags');
            sourceTags.innerHTML = Object.keys(sources).map(function(s) {{ 
                return '<span class="source-tag">' + s + '</span>'; 
            }}).join('');
            document.querySelector('.source-count').textContent = '共 ' + news.length + ' 条新闻';
            
            // 更新指标卡片的新闻数量
            var positive = 0, negative = 0, neutral = 0;
            for (var i = 0; i < news.length; i++) {{
                var sent = news[i].sentiment || 'neutral';
                if (sent === 'positive') positive++;
                else if (sent === 'negative') negative++;
                else neutral++;
            }}
            var positiveCard = document.querySelector('.metric-card:nth-child(3) .value');
            var negativeCard = document.querySelector('.metric-card:nth-child(4) .value');
            if (positiveCard) positiveCard.textContent = positive;
            if (negativeCard) negativeCard.textContent = negative;
        }}
        
        // Tab切换
        function showTab(tabId) {{
            document.querySelectorAll('.news-tab').forEach(function(tab) {{ tab.classList.remove('active'); }});
            document.querySelectorAll('.news-content').forEach(function(content) {{ content.classList.remove('active'); }});
            document.getElementById(tabId).classList.add('active');
            if (event && event.target) event.target.classList.add('active');
        }}
        
        // 按日期加载新闻
        function loadNewsByDate(date) {{
            // 更新日期按钮状态
            document.querySelectorAll('.date-btn').forEach(function(btn) {{ btn.classList.remove('active'); }});
            var btn = document.querySelector('[data-date="' + date + '"]');
            if (btn) btn.classList.add('active');
            
            // 切换到对应日期的数据
            switchDate(date);
            
            // 更新URL
            history.pushState({{date: date}}, '', '?date=' + date);
        }}
        
        // 检查URL参数并加载对应日期
        document.addEventListener('DOMContentLoaded', function() {{
            var urlParams = new URLSearchParams(window.location.search);
            var dateParam = urlParams.get('date');
            if (dateParam && allNewsData[dateParam]) {{
                loadNewsByDate(dateParam);
            }}
        }});
        
        // ECharts图表
        document.addEventListener('DOMContentLoaded', function() {{
            // VIX走势图表
            var vixChart = echarts.init(document.getElementById('vixChart'));
            vixChart.setOption({json.dumps(vix_chart_option, ensure_ascii=False)});
            
            // 情感分布图表
            var sentimentChart = echarts.init(document.getElementById('sentimentChart'));
            sentimentChart.setOption({json.dumps(sentiment_chart_option, ensure_ascii=False)});
            
            // 响应式
            window.addEventListener('resize', function() {{
                vixChart.resize();
                sentimentChart.resize();
            }});
        }});
    </script>
</body>
</html>'''
    
    return html

def main():
    """主函数"""
    print("开始生成HTML页面...")
    
    # 加载数据
    news_list, vix_data, vix_history, loaded_date = load_data()
    print(f"加载日期: {loaded_date}")
    print(f"加载新闻: {len(news_list)}条")
    print(f"VIX数据: {vix_data.get('current', 'N/A')}")
    
    # 获取可用日期
    available_dates = get_available_dates()
    print(f"可用日期: {[d['date'] for d in available_dates]}")
    
    # 生成HTML
    html = generate_html(news_list, vix_data, vix_history, loaded_date, available_dates)
    
    # 保存
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML页面已生成: {output_file}")
    return output_file

if __name__ == '__main__':
    main()
