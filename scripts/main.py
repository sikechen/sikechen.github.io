#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股市新闻监控 - 主程序入口
功能：整合抓取、分析、生成全流程
支持多新闻源抓取和历史日期查看
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from news_crawler import crawl_all_news, crawl_vix, save_data
from sentiment_analyzer import SentimentAnalyzer, MarketPredictor
from html_generator import generate_html, get_available_dates

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pipeline():
    """运行完整的数据处理流程"""
    start_time = datetime.now()
    today_str = datetime.now().strftime("%Y-%m-%d")
    logger.info("="*60)
    logger.info(f"股市新闻监控任务开始 - {today_str}")
    logger.info("="*60)
    
    try:
        # 1. 抓取数据
        logger.info("[步骤1/4] 抓取新闻数据...")
        news_list = crawl_all_news()
        logger.info(f"  -> 获取新闻 {len(news_list)} 条")
        
        # 统计各来源数量
        source_stats = {}
        for news in news_list:
            source = news.get('source', '未知')
            source_stats[source] = source_stats.get(source, 0) + 1
        logger.info(f"  -> 来源统计: {source_stats}")
        
        logger.info("[步骤2/4] 抓取VIX数据...")
        vix_data = crawl_vix()
        if vix_data:
            logger.info(f"  -> VIX指数: {vix_data.get('current', 'N/A')}")
            logger.info(f"  -> 恐慌等级: {vix_data.get('fear_level', '未知')}")
        else:
            logger.warning("  -> VIX数据获取失败，使用历史数据")
        
        # 2. 保存原始数据（按日期保存）
        logger.info("[步骤3/4] 保存数据...")
        save_data(news_list, vix_data)
        
        # 3. 生成HTML页面
        logger.info("[步骤4/4] 生成HTML页面...")
        # 情感分析
        analyzer = SentimentAnalyzer()
        analyzed_news = analyzer.analyze_batch(news_list)
        
        # 市场预测
        predictor = MarketPredictor()
        summary = predictor.generate_summary(vix_data, analyzed_news)
        
        # 生成HTML
        OUTPUT_DIR = SCRIPT_DIR.parent / 'output'
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # 加载VIX历史数据
        vix_history_file = SCRIPT_DIR.parent / 'data' / 'vix_history.json'
        vix_history = []
        if vix_history_file.exists():
            import json
            with open(vix_history_file, 'r', encoding='utf-8') as f:
                vix_history = json.load(f)
        
        # 获取可用日期
        available_dates = get_available_dates()
        
        # 生成HTML（传入今天的日期）
        html = generate_html(news_list, vix_data, vix_history, today_str, available_dates)
        output_file = OUTPUT_DIR / 'index.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # 统计
        positive = sum(1 for n in analyzed_news if n.get('sentiment') == 'positive')
        negative = sum(1 for n in analyzed_news if n.get('sentiment') == 'negative')
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("="*60)
        logger.info("任务完成!")
        logger.info(f"  - 新闻数量: {len(news_list)} 条")
        logger.info(f"  - 新闻来源: {len(source_stats)} 个")
        logger.info(f"  - 积极新闻: {positive} 条")
        logger.info(f"  - 消极新闻: {negative} 条")
        logger.info(f"  - VIX指数: {vix_data.get('current', 'N/A') if vix_data else 'N/A'}")
        logger.info(f"  - 综合预测: {summary.get('overall_prediction', 'N/A')}")
        logger.info(f"  - 可用历史: {len(available_dates)} 天")
        logger.info(f"  - 输出文件: {output_file}")
        logger.info(f"  - 耗时: {elapsed:.2f}秒")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"任务执行失败: {e}", exc_info=True)
        return False

def main():
    """主入口"""
    success = run_pipeline()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
