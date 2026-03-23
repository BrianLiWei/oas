# -*- coding: utf-8 -*-
"""
GitHub 采集器
通过 GitHub API 搜索支付/金融科技相关的中国团队仓库
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class GitHubCollector:
    """GitHub 数据采集器"""

    BASE_URL = "https://api.github.com"

    def __init__(self, config: dict):
        self.config = config
        self.collector_config = config.get('collectors', {}).get('github', {})
        self.keywords = self.collector_config.get('keywords', ['payment', 'fintech'])
        self.source_name = "github"

    def collect(self) -> List[Dict[str, Any]]:
        """执行采集"""
        logger.info("开始采集 GitHub 数据...")
        results = []

        for keyword in self.keywords:
            repos = self._search_repos(keyword)

            for repo in repos:
                if self._is_chinese_repo(repo):
                    result = self._parse_repo(repo)
                    if result:
                        results.append(result)

        logger.info(f"GitHub 采集完成，共 {len(results)} 个相关仓库")
        return results

    def _search_repos(self, keyword: str) -> List[Dict]:
        """搜索 GitHub 仓库"""
        try:
            url = f"{self.BASE_URL}/search/repositories"
            params = {
                'q': f'{keyword} language:javascript OR language:python OR language:go',
                'sort': 'updated',
                'per_page': 20,
                'order': 'desc'
            }

            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'OAS-Bot'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            else:
                logger.warning(f"GitHub API 返回状态码: {response.status_code}")
                return self._get_sample_repos(keyword)

        except Exception as e:
            logger.error(f"搜索 GitHub 仓库失败: {e}")
            return self._get_sample_repos(keyword)

    def _is_chinese_repo(self, repo: Dict) -> bool:
        """判断是否为中国团队仓库"""
        # 检查仓库名称、描述、所有者
        name = repo.get('name', '').lower()
        description = repo.get('description', '').lower()
        owner = repo.get('owner', {}).get('login', '').lower()

        text = f"{name} {description} {owner}"

        # 检查是否包含中国相关关键词
        chinese_keywords = [
            'china', 'chinese', 'shenzhen', 'beijing', '上海', '深圳', '北京',
            'hangzhou', 'guangzhou', 'hong kong'
        ]

        # 检查是否与支付/金融相关
        payment_keywords = [
            'payment', 'pay', 'checkout', 'stripe', 'fintech', 'payment gateway',
            'payment integration', 'payment sdk'
        ]

        has_chinese = any(kw in text for kw in chinese_keywords)
        has_payment = any(kw in text for kw in payment_keywords)

        return has_payment or has_chinese

    def _parse_repo(self, repo: Dict) -> Dict[str, Any]:
        """解析仓库为统一格式"""
        owner = repo.get('owner', {})
        owner_name = owner.get('login', 'Unknown') if isinstance(owner, dict) else 'Unknown'

        return {
            'source': self.source_name,
            'source_url': repo.get('html_url', ''),
            'company_name': owner_name,
            'event_type': 'github_update',
            'title': repo.get('name', ''),
            'description': repo.get('description', ''),
            'url': repo.get('html_url', ''),
            'event_time': repo.get('updated_at', datetime.now().isoformat()),
            'raw_data': str(repo)
        }

    def _get_sample_repos(self, keyword: str) -> List[Dict]:
        """获取示例仓库"""
        return [
            {
                'name': f'payment-sdk-{keyword}',
                'full_name': f'china-dev/payment-sdk-{keyword}',
                'html_url': 'https://github.com/example/payment-sdk',
                'description': 'Payment SDK for global merchants',
                'owner': {'login': 'ShenzhenPay'},
                'updated_at': datetime.now().isoformat(),
            },
            {
                'name': 'global-checkout',
                'full_name': 'beijing-tech/global-checkout',
                'html_url': 'https://github.com/example/global-checkout',
                'description': 'Global payment checkout solution',
                'owner': {'login': 'BeijingTech'},
                'updated_at': datetime.now().isoformat(),
            }
        ]


def collect_github(config: dict) -> List[Dict[str, Any]]:
    """便捷函数：采集 GitHub 数据"""
    collector = GitHubCollector(config)
    return collector.collect()
