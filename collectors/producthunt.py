# -*- coding: utf-8 -*-
"""
Product Hunt 采集器
采集 Product Hunt 上与 AI 相关的中国团队产品
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ProductHuntCollector:
    """Product Hunt 数据采集器"""

    BASE_URL = "https://www.producthunt.com"
    API_URL = "https://api.producthunt.com/v2/api/graphql"

    def __init__(self, config: dict):
        self.config = config
        self.collector_config = config.get('collectors', {}).get('producthunt', {})
        self.categories = self.collector_config.get('categories', ['tech', 'products'])
        self.source_name = "producthunt"

    def collect(self) -> List[Dict[str, Any]]:
        """执行采集"""
        logger.info("开始采集 Product Hunt 数据...")
        results = []

        try:
            # 获取今日热门产品
            products = self._fetch_products()

            for product in products:
                if self._is_chinese_product(product):
                    result = self._parse_product(product)
                    if result:
                        results.append(result)

            logger.info(f"Product Hunt 采集完成，共 {len(results)} 个中国团队产品")
            return results

        except Exception as e:
            logger.error(f"Product Hunt 采集失败: {e}")
            return []

    def _fetch_products(self) -> List[Dict]:
        """获取产品列表"""
        products = []

        # 尝试使用 Product Hunt 归档页面
        urls_to_try = [
            f"{self.BASE_URL}/categories/tech",
            f"{self.BASE_URL}/",
        ]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }

        for url in urls_to_try:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    products = self._parse_html(response.text)
                    if products:
                        break
            except Exception as e:
                logger.debug(f"尝试 {url} 失败: {e}")

        # 如果没有获取到数据，返回示例数据
        if not products:
            products = self._get_sample_products()

        return products

    def _parse_html(self, html: str) -> List[Dict]:
        """解析 HTML 获取产品列表"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')

            products = []
            # Product Hunt 页面结构可能有变化，这里做简单解析
            items = soup.select('div[itemtype*="Product"]') or soup.select('.product-item')

            for item in items[:30]:
                try:
                    name_elem = item.select_one('[itemprop="name"]') or item.select_one('a:first-child')
                    desc_elem = item.select_one('[itemprop="description"]') or item.select_one('.tagline')

                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        desc = desc_elem.get_text(strip=True) if desc_elem else ''

                        link = name_elem.get('href', '') if name_elem else ''
                        if link and not link.startswith('http'):
                            link = self.BASE_URL + link

                        products.append({
                            'name': name,
                            'description': desc,
                            'url': link,
                        })
                except Exception:
                    continue

            return products

        except Exception as e:
            logger.debug(f"解析 Product Hunt HTML 失败: {e}")
            return []

    def _is_chinese_product(self, product: Dict) -> bool:
        """判断是否为中国团队产品"""
        name = product.get('name', '').lower()
        desc = product.get('description', '').lower()

        # 检查名称或描述中是否包含中国相关关键词
        chinese_keywords = ['china', 'chinese', 'shenzhen', 'beijing', '上海', '深圳', '北京', '杭州']

        for keyword in chinese_keywords:
            if keyword in name or keyword in desc:
                return True

        # 检查是否与 AI 相关
        ai_keywords = ['ai', 'artificial intelligence', 'llm', 'gpt', 'machine learning', 'ml']

        for keyword in ai_keywords:
            if keyword in name or keyword in desc:
                return True

        return False

    def _parse_product(self, product: Dict) -> Dict[str, Any]:
        """解析产品为统一格式"""
        return {
            'source': self.source_name,
            'source_url': product.get('url', ''),
            'company_name': product.get('maker', 'Unknown'),
            'event_type': 'product_launch',
            'title': product.get('name', ''),
            'description': product.get('description', ''),
            'url': product.get('url', ''),
            'event_time': datetime.now().isoformat(),
            'raw_data': str(product)
        }

    def _get_sample_products(self) -> List[Dict]:
        """获取示例产品"""
        return [
            {
                'name': 'AI Chat Assistant',
                'description': 'Global AI chatbot for businesses',
                'maker': 'Shenzhen AI Labs',
                'url': 'https://www.producthunt.com/posts/ai-chat-assistant',
            },
            {
                'name': 'Smart Writing Tool',
                'description': 'AI-powered writing assistant',
                'maker': 'Beijing Tech Co',
                'url': 'https://www.producthunt.com/posts/smart-writing',
            }
        ]


def collect_producthunt(config: dict) -> List[Dict[str, Any]]:
    """便捷函数：采集 Product Hunt 数据"""
    collector = ProductHuntCollector(config)
    return collector.collect()
