# -*- coding: utf-8 -*-
"""
RSS 采集器
采集各大科技媒体的出海/AI相关资讯
"""

import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RSSCollector:
    """RSS 订阅源采集器"""

    def __init__(self, config: dict):
        self.config = config
        self.collector_config = config.get('collectors', {}).get('rss_feeds', {})
        self.feeds = self.collector_config.get('feeds', [])
        self.source_name = "rss"

    def collect(self) -> List[Dict[str, Any]]:
        """执行采集"""
        logger.info("开始采集 RSS 数据...")
        results = []

        for feed_config in self.feeds:
            feed_name = feed_config.get('name', 'Unknown')
            feed_url = feed_config.get('url', '')

            if not feed_url:
                continue

            logger.info(f"正在采集: {feed_name}")
            entries = self._fetch_feed(feed_url)

            for entry in entries:
                if self._is_relevant(entry):
                    result = self._parse_entry(entry, feed_name)
                    if result:
                        results.append(result)

        logger.info(f"RSS 采集完成，共 {len(results)} 条相关内容")
        return results

    def _fetch_feed(self, url: str) -> List[Dict]:
        """获取 RSS 订阅源内容"""
        try:
            feed = feedparser.parse(url)
            entries = []

            for entry in feed.entries[:20]:  # 限制每个源的数量
                entries.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'description': entry.get('description', ''),
                    'published': entry.get('published', ''),
                    'updated': entry.get('updated', ''),
                })

            logger.debug(f"从 {url} 获取 {len(entries)} 条记录")
            return entries

        except Exception as e:
            logger.error(f"解析 RSS 源 {url} 失败: {e}")
            return []

    def _is_relevant(self, entry: Dict) -> bool:
        """判断内容是否与出海/AI相关"""
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()
        description = entry.get('description', '').lower()

        text = f"{title} {summary} {description}"

        # AI 相关关键词
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'llm',
            'gpt', 'chatgpt', '大模型', '人工智能', '机器学习'
        ]

        # 出海相关关键词
        overseas_keywords = [
            'overseas', 'global', 'international', 'worldwide', '出海',
            '海外', '美国', '欧洲', 'global', 'abroad', 'expansion',
            '36kr', '白鲸', 'techcrunch'
        ]

        # 公司相关关键词
        company_keywords = [
            'launch', 'product', 'funding', 'series', 'startup', 'launched',
            '发布', '融资', '产品', '初创', 'startup'
        ]

        has_ai = any(kw in text for kw in ai_keywords)
        has_overseas = any(kw in text for kw in overseas_keywords)
        has_company = any(kw in text for kw in company_keywords)

        # 至少包含AI或出海关键词，以及公司相关关键词
        return (has_ai or has_overseas) and has_company

    def _parse_entry(self, entry: Dict, feed_name: str) -> Dict[str, Any]:
        """解析条目为统一格式"""
        # 尝试从内容中提取公司名
        company_name = self._extract_company_name(
            entry.get('title', ''),
            entry.get('summary', '')
        )

        return {
            'source': f"rss_{feed_name}",
            'source_url': entry.get('link', ''),
            'company_name': company_name,
            'event_type': 'news',
            'title': entry.get('title', ''),
            'description': entry.get('summary', '')[:500],
            'url': entry.get('link', ''),
            'event_time': entry.get('published', datetime.now().isoformat()),
            'raw_data': str(entry)
        }

    def _extract_company_name(self, title: str, description: str) -> str:
        """从标题或描述中提取公司名"""
        text = f"{title} {description}"

        # 常见的公司名模式
        import re

        # 尝试匹配 "公司名 + 融资/发布/产品" 等模式
        patterns = [
            r'([A-Z][a-zA-Z]+(?:\s+(?:AI|Tech|Labs|Inc|Co))?)',
            r'([\u4e00-\u9fa5]{2,10}(?:科技|智能|网络|技术|有限|公司))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return "Unknown"


def collect_rss(config: dict) -> List[Dict[str, Any]]:
    """便捷函数：采集 RSS 数据"""
    collector = RSSCollector(config)
    return collector.collect()
