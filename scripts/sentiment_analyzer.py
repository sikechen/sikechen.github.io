#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻情感分析模块
功能：对新闻标题进行情感分析，评估市场情绪
"""

import json
import re
from datetime import datetime
from pathlib import Path
from collections import Counter

class SentimentAnalyzer:
    """情感分析器"""
    
    # 正面关键词
    POSITIVE_KEYWORDS = [
        # 增长/上涨相关
        '涨', '上涨', '大涨', '暴涨', '拉升', '反弹', '走强', '回暖', '复苏',
        '增长', '增速', '高增长', '强劲', '超预期', '突破', '创新高', '首涨',
        '上行', '攀升', '上扬', '飘红', '普涨', '涨停', '连涨', '涨势',
        # 利好/政策相关
        '利好', '政策支持', '政策利好', '刺激', '扶持', '宽松', '降准', '降息',
        '改革', '开放', '红利', '机遇', '机会', '看好', '推荐', '增持', '买入',
        '评级上调', '超配', '跑赢', '优于', '优于大市', '强于大市',
        # 业绩/盈利相关
        '业绩增长', '盈利增长', '利润增长', '营收增长', '净利润增长', '扭亏',
        '超预期', '大幅增长', '爆发', '高增长', '增长强劲', '表现亮眼',
        # 积极信号
        '企稳', '稳定', '平稳', '健康', '有序', '积极', '乐观', '信心',
        '资金流入', '净流入', '加仓', '建仓', '入场', '抄底', '买入信号',
        '技术性反弹', '修复', '估值修复', '价值重估'
    ]
    
    # 负面关键词
    NEGATIVE_KEYWORDS = [
        # 下跌相关
        '跌', '下跌', '大跌', '暴跌', '下挫', '回落', '走弱', '低迷', '疲软',
        '下降', '下滑', '跌幅', '跌势', '跳水', '闪崩', '跌停', '连跌',
        '重挫', '重跌', '砸盘', '抛售', '恐慌', '踩踏', '出逃', '做空',
        # 风险/问题相关
        '风险', '暴雷', '违约', '破产', '债务', '危机', '隐患', '问题',
        '造假', '欺诈', '调查', '处罚', '监管', '整改', '清退', '清盘',
        '亏损', '业绩下滑', '利润下降', '亏损扩大', '不及预期', '首亏',
        # 宏观风险
        '衰退', '滞胀', '通胀', '紧缩', '加息', '缩表', '去杠杆', '泡沫',
        '黑天鹅', '灰犀牛', '不确定性', '风险上升', '担忧', '恐慌', '观望',
        # 资金流出
        '资金流出', '净流出', '减仓', '清仓', '离场', '出逃', '抛压',
        '卖出信号', '死叉', '技术性破位'
    ]
    
    # 中性/市场相关关键词
    NEUTRAL_KEYWORDS = [
        '震荡', '整理', '盘整', '波动', '区间', '等待', '观望', '中性',
        '观望', '谨慎', '平仓', '调仓', '换手', '洗盘', '横盘', '牛皮市',
        '盘整', '分化', '分化明显', '结构性', '轮动', '热点切换'
    ]
    
    # A股特有词汇
    A_STOCK_KEYWORDS = [
        'A股', '沪指', '深指', '上证', '深证', '创业板', '科创板', '北证',
        '主板', '中小板', '沪深300', '中证500', '中证1000', '上证50',
        '大盘', '蓝筹', '权重', '护盘', '国家队', '机构', '公募', '私募',
        '北向', '外资', '南下', '融资融券', '杠杆', '做多', '做空',
        '涨停板', '龙头', '妖股', '次新', '壳资源', '题材', '概念',
        '新能源', '半导体', '芯片', '人工智能', '医药', '白酒', '银行',
        '券商', '保险', '地产', '基建', '消费', '科技', '军工'
    ]
    
    # 美股关键词
    US_STOCK_KEYWORDS = [
        '美股', '纳斯达克', '道琼斯', '标普', 'S&P', '纳斯达克', '纽交所',
        '特斯拉', '苹果', '微软', '谷歌', '亚马逊', 'Meta', '英伟达', 'AMD',
        'Fed', '美联储', 'CPI', '非农', 'GDP', '鲍威尔', '华尔街'
    ]
    
    # 港股关键词
    HK_STOCK_KEYWORDS = [
        '港股', '恒生', '恒指', '国企指数', '红筹', 'H股', '港交所',
        '腾讯', '阿里', '京东', '美团', '小米', '比亚迪', '港资'
    ]
    
    # 地缘政治/战争冲突关键词（重点关注）
    GEOPOLITICAL_KEYWORDS = [
        # 美国伊朗
        '美国', '伊朗', '美军', '伊核', '制裁', '波斯湾', '霍尔木兹',
        '特朗普', '拜登', '白宫', '五角大楼',
        # 俄罗斯
        '俄罗斯', '俄军', '普京', '乌克兰', '克里米亚', '北约', 'NATO',
        '俄乌', '俄乌冲突', '俄乌战争', '顿巴斯',
        # 以色列
        '以色列', '巴以', '加沙', '哈马斯', '黎巴嫩', '真主党',
        '中东', '巴勒斯坦',
        # 战争冲突通用
        '战争', '冲突', '军事', '导弹', '空袭', '轰炸', '核武器',
        '军队', '士兵', '伤亡', '难民', '停火', '和谈', '军事行动',
        '地缘政治', '紧张局势', '边境', '领土', '主权',
        # 其他热点地区
        '朝鲜', '台海', '南海', '半岛', '叙利亚', '阿富汗', '也门'
    ]
    
    # 战争冲突对市场影响的关键词
    WAR_MARKET_IMPACT = [
        '油价', '原油', '黄金', '避险', '军工', '国防',
        '能源', '石油', '天然气', '供应链', '通胀'
    ]
    
    # 板块关键词
    SECTOR_KEYWORDS = {
        '科技': ['科技', '半导体', '芯片', '人工智能', 'AI', '算力', '数据', '软件', '云计算', '大数据', '互联网', '电商', '消费电子'],
        '新能源': ['新能源', '光伏', '锂电', '电池', '储能', '风电', '氢能', '充电桩', '新能源车', '电动车', '特斯拉', '比亚迪'],
        '金融': ['银行', '券商', '保险', '基金', '信托', '金融', '信贷', '利率', '货币政策', '央行'],
        '医药': ['医药', '医疗', '生物', '疫苗', '创新药', '中药', 'CXO', '医疗器械', '医院'],
        '消费': ['消费', '零售', '白酒', '食品', '饮料', '家电', '餐饮', '旅游', '酒店', '免税'],
        '地产': ['地产', '房地产', '物业', '租售', '房价', '土拍', '保障房'],
        '军工': ['军工', '国防', '武器', '导弹', '航天', '航空', '舰船', '雷达'],
        '能源': ['能源', '石油', '煤炭', '电力', '核电', '油气', '石化'],
        '基建': ['基建', '建筑', '工程', '建材', '水泥', '钢铁', '工程机械'],
        '农业': ['农业', '粮食', '种子', '农药', '化肥', '养殖', '种植'],
        '有色': ['有色', '铜', '铝', '锂', '稀土', '黄金', '贵金属', '金属'],
        '汽车': ['汽车', '整车', '零部件', '新能源车', '智能驾驶', '造车']
    }
    
    def __init__(self):
        self.positive_set = set(self.POSITIVE_KEYWORDS)
        self.negative_set = set(self.NEGATIVE_KEYWORDS)
        self.neutral_set = set(self.NEUTRAL_KEYWORDS)
        self.a_stock_set = set(self.A_STOCK_KEYWORDS)
        self.us_stock_set = set(self.US_STOCK_KEYWORDS)
        self.hk_stock_set = set(self.HK_STOCK_KEYWORDS)
        self.geopolitical_set = set(self.GEOPOLITICAL_KEYWORDS)
        self.war_impact_set = set(self.WAR_MARKET_IMPACT)
        self.sector_keywords = self.SECTOR_KEYWORDS
        
    def analyze_sentiment(self, title):
        """分析单条新闻的情感"""
        if not title:
            return {'sentiment': 'neutral', 'score': 0, 'keywords': [], 'geopolitical': False}
        
        title_lower = title.lower()
        title_clean = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title)
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        matched_keywords = []
        geopolitical_keywords = []
        war_impact_keywords = []
        
        # 检查关键词
        for keyword in self.positive_keywords:
            if keyword in title_clean:
                positive_count += 1
                matched_keywords.append(keyword)
                
        for keyword in self.negative_keywords:
            if keyword in title_clean:
                negative_count += 1
                matched_keywords.append(keyword)
                
        for keyword in self.neutral_keywords:
            if keyword in title_clean:
                neutral_count += 1
        
        # 检查地缘政治关键词
        for keyword in self.geopolitical_set:
            if keyword in title_clean:
                geopolitical_keywords.append(keyword)
        
        # 检查战争对市场影响关键词
        for keyword in self.war_impact_set:
            if keyword in title_clean:
                war_impact_keywords.append(keyword)
                
        # 计算情感得分
        total = positive_count + negative_count + 1
        score = (positive_count - negative_count) / total * 100
        
        # 确定情感分类
        if positive_count > negative_count:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
            
        return {
            'sentiment': sentiment,
            'score': round(score, 2),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'keywords': matched_keywords[:5],  # 最多返回5个关键词
            'geopolitical': len(geopolitical_keywords) > 0,
            'geopolitical_keywords': geopolitical_keywords[:3],
            'war_impact': len(war_impact_keywords) > 0,
            'war_impact_keywords': war_impact_keywords[:3]
        }
    
    @property
    def positive_keywords(self):
        return [k for k in self.positive_set if len(k) >= 2]
    
    @property
    def negative_keywords(self):
        return [k for k in self.negative_set if len(k) >= 2]
    
    @property
    def neutral_keywords(self):
        return [k for k in self.neutral_set if len(k) >= 2]
    
    def detect_market(self, title):
        """检测新闻涉及的市场"""
        title_clean = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title)
        markets = []
        
        for kw in self.a_stock_set:
            if kw in title_clean:
                markets.append('A股')
                break
                
        for kw in self.us_stock_set:
            if kw in title_clean:
                markets.append('美股')
                break
                
        for kw in self.hk_stock_set:
            if kw in title_clean:
                markets.append('港股')
                break
                
        if not markets:
            markets.append('综合')
            
        return list(set(markets))
    
    def detect_sectors(self, title):
        """检测新闻涉及的板块"""
        title_clean = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title)
        sectors = []
        
        for sector, keywords in self.sector_keywords.items():
            for kw in keywords:
                if kw in title_clean:
                    sectors.append(sector)
                    break
        
        return list(set(sectors)) if sectors else ['综合']
    
    def analyze_batch(self, news_list):
        """批量分析新闻"""
        results = []
        
        for news in news_list:
            title = news.get('title', '')
            sentiment_result = self.analyze_sentiment(title)
            markets = self.detect_market(title)
            sectors = self.detect_sectors(title)
            
            result = {
                **news,
                **sentiment_result,
                'markets': markets,
                'sectors': sectors,
                'analyzed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            results.append(result)
            
        return results

class MarketPredictor:
    """市场预测器"""
    
    def __init__(self):
        self.vix_fear_levels = {
            '极低': {'range': (0, 15), 'signal': '极度乐观', 'action': '可适当加仓'},
            '较低': {'range': (15, 20), 'signal': '乐观', 'action': '维持仓位'},
            '中性': {'range': (20, 25), 'signal': '谨慎', 'action': '观望为主'},
            '较高': {'range': (25, 30), 'signal': '担忧', 'action': '减仓防范'},
            '极高': {'range': (30, 100), 'signal': '恐慌', 'action': '清仓避险'}
        }
        
    def predict_from_vix(self, vix_data):
        """基于VIX进行市场预测"""
        if not vix_data or not vix_data.get('current'):
            return {
                'prediction': '数据不足',
                'signal': '观望',
                'suggestion': '等待数据更新'
            }
            
        vix_value = vix_data['current']
        
        for level, info in self.vix_fear_levels.items():
            min_val, max_val = info['range']
            if min_val <= vix_value < max_val:
                return {
                    'prediction': f"VIX={vix_value:.2f}, 市场{info['signal']}",
                    'signal': level,
                    'suggestion': info['action'],
                    'vix_level': level
                }
                
        return {
            'prediction': f"VIX={vix_value:.2f}",
            'signal': '未知',
            'suggestion': '需进一步分析'
        }
    
    def predict_from_sentiment(self, analyzed_news):
        """基于情感分析进行市场预测"""
        if not analyzed_news:
            return {
                'prediction': '无新闻数据',
                'bull_ratio': 0,
                'bear_ratio': 0,
                'net_sentiment': 0
            }
            
        positive_count = sum(1 for n in analyzed_news if n.get('sentiment') == 'positive')
        negative_count = sum(1 for n in analyzed_news if n.get('sentiment') == 'negative')
        neutral_count = sum(1 for n in analyzed_news if n.get('sentiment') == 'neutral')
        total = len(analyzed_news)
        
        bull_ratio = positive_count / total * 100 if total > 0 else 0
        bear_ratio = negative_count / total * 100 if total > 0 else 0
        
        # 计算净情感
        net_sentiment = bull_ratio - bear_ratio
        
        # 生成预测
        if net_sentiment > 20:
            prediction = '市场情绪偏向积极'
            action = '可关注机会'
        elif net_sentiment < -20:
            prediction = '市场情绪偏向消极'
            action = '谨慎为主'
        else:
            prediction = '市场情绪中性'
            action = '观望等待'
            
        return {
            'prediction': prediction,
            'action': action,
            'bull_ratio': round(bull_ratio, 1),
            'bear_ratio': round(bear_ratio, 1),
            'neutral_ratio': round(neutral_count / total * 100, 1) if total > 0 else 0,
            'net_sentiment': round(net_sentiment, 1),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'total_news': total
        }
    
    def analyze_sectors(self, analyzed_news):
        """分析各板块的新闻数量和情绪变化"""
        from collections import defaultdict
        
        sector_stats = defaultdict(lambda: {
            'total': 0,
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'geopolitical': 0,
            'news': []
        })
        
        for news in analyzed_news:
            sectors = news.get('sectors', ['综合'])
            sentiment = news.get('sentiment', 'neutral')
            geopolitical = news.get('geopolitical', False)
            
            for sector in sectors:
                sector_stats[sector]['total'] += 1
                if sentiment == 'positive':
                    sector_stats[sector]['positive'] += 1
                elif sentiment == 'negative':
                    sector_stats[sector]['negative'] += 1
                else:
                    sector_stats[sector]['neutral'] += 1
                
                if geopolitical:
                    sector_stats[sector]['geopolitical'] += 1
                
                # 保存重要新闻
                if len(sector_stats[sector]['news']) < 3:
                    sector_stats[sector]['news'].append(news.get('title', '')[:40])
        
        # 计算板块情绪指数和变化强度
        sector_analysis = []
        for sector, stats in sector_stats.items():
            if stats['total'] == 0:
                continue
            
            positive_ratio = stats['positive'] / stats['total'] * 100
            negative_ratio = stats['negative'] / stats['total'] * 100
            net_sentiment = positive_ratio - negative_ratio
            
            # 计算板块热度（新闻数量 * 情绪强度）
            intensity = abs(net_sentiment) * (stats['total'] / 10)
            
            # 判断板块趋势
            if net_sentiment > 20:
                trend = '强势'
                trend_icon = '🔥'
            elif net_sentiment < -20:
                trend = '弱势'
                trend_icon = '❄️'
            else:
                trend = '震荡'
                trend_icon = '⚖️'
            
            # 判断变化强度
            if stats['total'] >= 5 and abs(net_sentiment) >= 30:
                change_level = '剧烈变化'
                change_icon = '⚠️'
            elif stats['total'] >= 3 and abs(net_sentiment) >= 20:
                change_level = '明显变化'
                change_icon = '📊'
            else:
                change_level = '平稳'
                change_icon = '➡️'
            
            sector_analysis.append({
                'sector': sector,
                'total': stats['total'],
                'positive': stats['positive'],
                'negative': stats['negative'],
                'neutral': stats['neutral'],
                'geopolitical': stats['geopolitical'],
                'positive_ratio': round(positive_ratio, 1),
                'negative_ratio': round(negative_ratio, 1),
                'net_sentiment': round(net_sentiment, 1),
                'intensity': round(intensity, 1),
                'trend': trend,
                'trend_icon': trend_icon,
                'change_level': change_level,
                'change_icon': change_icon,
                'top_news': stats['news'][:2]
            })
        
        # 按热度排序
        sector_analysis.sort(key=lambda x: x['intensity'], reverse=True)
        
        return sector_analysis
    
    def generate_summary(self, vix_data, analyzed_news):
        """生成综合市场摘要"""
        vix_prediction = self.predict_from_vix(vix_data)
        sentiment_prediction = self.predict_from_sentiment(analyzed_news)
        
        # 综合判断
        risk_level = '低'
        if vix_prediction.get('vix_level') in ['较高', '极高']:
            risk_level = '高'
        elif vix_prediction.get('vix_level') == '中性':
            risk_level = '中'
            
        if sentiment_prediction.get('net_sentiment', 0) < -20:
            risk_level = '高' if risk_level == '中' else risk_level
            
        return {
            'vix_prediction': vix_prediction,
            'sentiment_prediction': sentiment_prediction,
            'risk_level': risk_level,
            'overall_prediction': self._get_overall_prediction(vix_prediction, sentiment_prediction),
            'key_points': self._extract_key_points(analyzed_news),
            'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _get_overall_prediction(self, vix_pred, sentiment_pred):
        """获取综合预测"""
        signals = []
        
        if vix_pred.get('signal') in ['较高', '极高']:
            signals.append('偏空')
        elif vix_pred.get('signal') in ['极低', '较低']:
            signals.append('偏多')
            
        if sentiment_pred.get('net_sentiment', 0) > 20:
            signals.append('积极')
        elif sentiment_pred.get('net_sentiment', 0) < -20:
            signals.append('消极')
            
        if not signals:
            return '中性震荡'
            
        return '/'.join(signals) if len(signals) <= 2 else '震荡整理'
    
    def _extract_key_points(self, analyzed_news):
        """提取关键新闻点"""
        key_points = []
        
        # 按情感分组
        positive_news = [n for n in analyzed_news if n.get('sentiment') == 'positive'][:3]
        negative_news = [n for n in analyzed_news if n.get('sentiment') == 'negative'][:3]
        
        for news in positive_news:
            key_points.append({
                'type': '利好',
                'title': news.get('title', '')[:50],
                'source': news.get('source', '')
            })
            
        for news in negative_news:
            key_points.append({
                'type': '利空',
                'title': news.get('title', '')[:50],
                'source': news.get('source', '')
            })
            
        return key_points

def main():
    """测试函数"""
    analyzer = SentimentAnalyzer()
    predictor = MarketPredictor()
    
    # 测试新闻
    test_news = [
        {'title': 'A股三大指数集体上涨，创业板指涨逾2%', 'source': '新浪财经'},
        {'title': '央行宣布降准0.5个百分点，释放长期资金1万亿', 'source': '东方财富'},
        {'title': '美股暴跌道指重挫800点，恐慌指数飙升', 'source': '雪球'},
        {'title': '宁德时代业绩超预期，股价创历史新高', 'source': '新浪财经'},
        {'title': '房地产市场持续低迷，多地房价下跌', 'source': '东方财富'},
    ]
    
    # 分析
    results = analyzer.analyze_batch(test_news)
    
    for r in results:
        print(f"标题: {r['title']}")
        print(f"情感: {r['sentiment']} ({r['score']})")
        print(f"市场: {r['markets']}")
        print("-" * 50)
    
    # 市场预测
    summary = predictor.generate_summary(
        {'current': 22.5, 'fear_level': '中性'},
        results
    )
    
    print("\n市场摘要:")
    print(f"VIX预测: {summary['vix_prediction']}")
    print(f"情感预测: {summary['sentiment_prediction']}")
    print(f"综合判断: {summary['overall_prediction']}")

if __name__ == '__main__':
    main()
