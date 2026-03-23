# -*- coding: utf-8 -*-
"""
OAS 数据清洗与入库模块
负责数据去重、标准化、入库
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import Database, get_database
from utils import (
    clean_text, normalize_company_name, is_chinese_company,
    has_overseas_indicator, parse_date, is_valid_url
)

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗与入库处理"""

    def __init__(self, db: Database = None, config: dict = None):
        self.db = db or get_database()
        self.config = config or {}
        self.stats = {
            'total_raw': 0,
            'companies_added': 0,
            'companies_updated': 0,
            'events_added': 0,
            'duplicates_skipped': 0
        }

    def process_raw_data(self, raw_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理采集到的原始数据"""
        logger.info(f"开始清洗数据，共 {len(raw_data_list)} 条原始记录")

        self.stats['total_raw'] = len(raw_data_list)

        for raw_data in raw_data_list:
            try:
                self._process_single(raw_data)
            except Exception as e:
                logger.error(f"清洗数据失败: {e}, 数据: {raw_data}")

        logger.info(f"数据清洗完成: 新增公司 {self.stats['companies_added']}, "
                   f"更新公司 {self.stats['companies_updated']}, "
                   f"新增事件 {self.stats['events_added']}, "
                   f"跳过重复 {self.stats['duplicates_skipped']}")

        return self.stats

    def _process_single(self, raw_data: Dict[str, Any]):
        """处理单条原始数据"""
        # 标准化字段
        normalized = self._normalize_data(raw_data)

        # 检查事件是否已存在（去重）
        source = normalized.get('source', '')
        url = normalized.get('url', '')

        if source and url and self.db.event_exists(source, url):
            self.stats['duplicates_skipped'] += 1
            logger.debug(f"跳过重复事件: {normalized.get('title', '')}")
            return

        # 获取或创建公司
        company_id = self._get_or_create_company(normalized)

        if company_id:
            # 添加事件
            event_id = self._add_event(company_id, normalized)
            if event_id:
                self.stats['events_added'] += 1

    def _normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化原始数据"""
        normalized = {
            'source': raw_data.get('source', ''),
            'source_url': raw_data.get('source_url', ''),
            'company_name': normalize_company_name(raw_data.get('company_name', 'Unknown')),
            'event_type': raw_data.get('event_type', 'news'),
            'title': clean_text(raw_data.get('title', '')),
            'description': clean_text(raw_data.get('description', '')),
            'url': raw_data.get('url', ''),
            'event_time': raw_data.get('event_time', datetime.now().isoformat()),
            'raw_data': raw_data.get('raw_data', ''),
        }

        # 额外字段
        if 'funding_stage' in raw_data:
            normalized['funding_stage'] = raw_data['funding_stage']
        if 'funding_amount' in raw_data:
            normalized['funding_amount'] = raw_data['funding_amount']
        if 'industry' in raw_data:
            normalized['industry'] = raw_data['industry']

        return normalized

    def _get_or_create_company(self, normalized_data: Dict[str, Any]) -> Optional[int]:
        """获取或创建公司记录"""
        company_name = normalized_data.get('company_name', '')

        if not company_name:
            return None

        # 尝试查找已存在的公司
        existing_company = self.db.get_company_by_name(company_name)

        if existing_company:
            # 更新公司信息
            self._update_company(existing_company['id'], normalized_data)
            self.stats['companies_updated'] += 1
            return existing_company['id']
        else:
            # 创建新公司
            company_data = self._build_company_data(normalized_data)
            company_id = self.db.add_company(company_data)

            if company_id:
                self.stats['companies_added'] += 1
                return company_id

        return None

    def _build_company_data(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建公司数据"""
        description = normalized_data.get('description', '')
        title = normalized_data.get('title', '')
        text = f"{title} {description}"

        # 判断是否为中国出海公司
        is_chinese = is_chinese_company(
            normalized_data.get('company_name', ''),
            description,
            self.config.get('keywords', {}).get('company_identifiers')
        )

        has_overseas = has_overseas_indicator(
            text,
            self.config.get('keywords', {}).get('overseas_indicators')
        )

        company_data = {
            'name': normalized_data.get('company_name', 'Unknown'),
            'website': self._extract_website(normalized_data.get('url', '')),
            'description': description[:500],
            'industry': normalized_data.get('industry', self._infer_industry(text)),
            'target_market': 'Global' if has_overseas else 'China',
            'funding_stage': normalized_data.get('funding_stage', ''),
            'is_chinese_overseas': 1 if (is_chinese or has_overseas) else 0,
        }

        return company_data

    def _update_company(self, company_id: int, normalized_data: Dict[str, Any]):
        """更新公司信息"""
        update_data = {}

        # 更新融资轮次
        if 'funding_stage' in normalized_data and normalized_data['funding_stage']:
            update_data['funding_stage'] = normalized_data['funding_stage']

        # 更新目标市场
        if 'target_market' in normalized_data:
            text = normalized_data.get('description', '')
            if has_overseas_indicator(text):
                update_data['target_market'] = 'Global'

        if update_data:
            self.db.update_company(company_id, update_data)

    def _add_event(self, company_id: int, normalized_data: Dict[str, Any]) -> Optional[int]:
        """添加事件记录"""
        event_data = {
            'company_id': company_id,
            'source': normalized_data.get('source', ''),
            'event_type': normalized_data.get('event_type', 'news'),
            'title': normalized_data.get('title', ''),
            'description': normalized_data.get('description', ''),
            'url': normalized_data.get('url', ''),
            'event_time': normalized_data.get('event_time', datetime.now().isoformat()),
            'raw_data': normalized_data.get('raw_data', '')
        }

        return self.db.add_event(event_data)

    def _extract_website(self, url: str) -> str:
        """从URL提取域名作为网站"""
        if not url:
            return ''

        if '://' in url:
            # 从URL提取域名
            from utils import extract_domain
            return extract_domain(url)

        return ''

    def _infer_industry(self, text: str) -> str:
        """推断行业"""
        text = text.lower()

        industries = {
            'AI': ['ai', 'artificial intelligence', 'machine learning', 'llm', 'gpt', '人工智能', '大模型'],
            'Hardware': ['hardware', 'robot', 'device', 'smart device', '硬件', '机器人'],
            'Fintech': ['payment', 'fintech', 'financial', '支付', '金融'],
            'SaaS': ['saas', 'software', 'cloud', 'software as a service'],
            'E-commerce': ['e-commerce', 'ecommerce', 'shopping', '电商'],
        }

        for industry, keywords in industries.items():
            for keyword in keywords:
                if keyword in text:
                    return industry

        return 'Technology'


def process_and_store(raw_data_list: List[Dict[str, Any]],
                       db: Database = None,
                       config: dict = None) -> Dict[str, Any]:
    """便捷函数：处理并存储数据"""
    cleaner = DataCleaner(db, config)
    return cleaner.process_raw_data(raw_data_list)
