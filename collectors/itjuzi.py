# -*- coding: utf-8 -*-
"""
IT桔子采集器
采集IT桔子上的AI/出海公司融资信息
注：IT桔子需要登录或API Key，这里提供模拟实现
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ITJuziCollector:
    """IT桔子数据采集器"""

    BASE_URL = "https://www.itjuzi.com"
    API_URL = "https://www.itjuzi.com/api"

    def __init__(self, config: dict):
        self.config = config
        self.collector_config = config.get('collectors', {}).get('itjuzi', {})
        self.api_key = self.collector_config.get('api_key', '')
        self.source_name = "itjuzi"

    def collect(self) -> List[Dict[str, Any]]:
        """执行采集"""
        logger.info("开始采集 IT桔子 数据...")
        results = []

        try:
            # 获取最近的融资事件
            fundings = self._fetch_fundings()

            for funding in fundings:
                if self._is_overseas_company(funding):
                    result = self._parse_funding(funding)
                    if result:
                        results.append(result)

            logger.info(f"IT桔子 采集完成，共 {len(results)} 条出海公司融资信息")
            return results

        except Exception as e:
            logger.error(f"IT桔子 采集失败: {e}")
            return []

    def _fetch_fundings(self) -> List[Dict]:
        """获取融资事件列表"""
        # 由于IT桔子需要登录，这里返回示例数据
        # 实际使用时需要配置API Key或使用其他方式

        if self.api_key:
            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                # 尝试调用API
                response = requests.get(
                    f"{self.API_URL}/funding",
                    headers=headers,
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json().get('data', [])
            except Exception as e:
                logger.debug(f"IT桔子 API 调用失败: {e}")

        # 返回示例数据
        return self._get_sample_fundings()

    def _is_overseas_company(self, funding: Dict) -> bool:
        """判断是否为出海公司"""
        company_name = funding.get('company_name', '').lower()
        description = funding.get('description', '').lower()
        industry = funding.get('industry', '').lower()

        text = f"{company_name} {description} {industry}"

        # 检查是否为AI相关
        ai_keywords = ['ai', 'artificial intelligence', '人工智能', '大模型', '机器学习']

        # 检查是否有出海迹象
        overseas_keywords = [
            'overseas', 'global', 'international', '出海', '海外',
            'global', 'abroad', '美国', '欧洲', '海外市场'
        ]

        has_ai = any(kw in text for kw in ai_keywords)
        has_overseas = any(kw in text for kw in overseas_keywords)

        return has_ai or has_overseas

    def _parse_funding(self, funding: Dict) -> Dict[str, Any]:
        """解析融资事件为统一格式"""
        return {
            'source': self.source_name,
            'source_url': funding.get('url', ''),
            'company_name': funding.get('company_name', 'Unknown'),
            'event_type': 'funding',
            'title': f"{funding.get('company_name', '')} 获得 {funding.get('amount', 'N/A')} 融资",
            'description': funding.get('description', ''),
            'url': funding.get('url', ''),
            'event_time': funding.get('funding_date', datetime.now().isoformat()),
            'raw_data': str(funding),
            'funding_stage': funding.get('stage', ''),
            'funding_amount': funding.get('amount', '')
        }

    def _get_sample_fundings(self) -> List[Dict]:
        """获取示例融资数据"""
        return [
            {
                'company_name': 'AI Tech Company',
                'url': 'https://www.itjuzi.com/company/12345',
                'description': 'AI company expanding to overseas markets',
                'funding_date': datetime.now().isoformat(),
                'stage': 'Series A',
                'amount': '$10M',
                'industry': 'AI'
            },
            {
                'company_name': 'Smart Device Inc',
                'url': 'https://www.itjuzi.com/company/12346',
                'description': 'Smart hardware company launching global products',
                'funding_date': datetime.now().isoformat(),
                'stage': 'Series B',
                'amount': '$20M',
                'industry': 'Hardware'
            },
            {
                'company_name': 'Global Pay',
                'url': 'https://www.itjuzi.com/company/12347',
                'description': 'Payment solution provider for cross-border trade',
                'funding_date': datetime.now().isoformat(),
                'stage': 'Series A',
                'amount': '$15M',
                'industry': 'Fintech'
            }
        ]


def collect_itjuzi(config: dict) -> List[Dict[str, Any]]:
    """便捷函数：采集 IT桔子 数据"""
    collector = ITJuziCollector(config)
    return collector.collect()
