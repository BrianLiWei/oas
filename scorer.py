# -*- coding: utf-8 -*-
"""
OAS 评分模块
根据多维度规则对公司进行评分
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from models import Database, get_database
from utils import has_overseas_indicator, get_funding_score, parse_date, is_recent

logger = logging.getLogger(__name__)


class CompanyScorer:
    """公司评分器"""

    # 评分维度配置
    SCORING_RULES = {
        'funding_stage': {
            'max_score': 20,
            'description': '融资轮次评分'
        },
        'overseas_recruitment': {
            'max_score': 15,
            'description': '海外招聘评分'
        },
        'target_market': {
            'max_score': 10,
            'description': '目标市场评分'
        },
        'recent_product_launch': {
            'max_score': 10,
            'description': '近期产品发布评分'
        },
        'overseas_news': {
            'max_score': 5,
            'description': '出海动态评分'
        },
        'github_activity': {
            'max_score': 15,
            'description': 'GitHub活跃度评分'
        },
        'crowdfunding': {
            'max_score': 10,
            'description': '众筹平台评分'
        },
        'producthunt': {
            'max_score': 5,
            'description': 'Product Hunt评分'
        },
        'media_coverage': {
            'max_score': 10,
            'description': '媒体报道评分'
        }
    }

    def __init__(self, db: Database = None, config: dict = None):
        self.db = db or get_database()
        self.config = config or {}
        self.scoring_config = self.config.get('scoring', {})
        self.weights = self.scoring_config.get('weights', {})

    def score_company(self, company_id: int) -> Dict[str, Any]:
        """对单个公司进行评分"""
        company = self.db.get_company_by_id(company_id)

        if not company:
            logger.warning(f"公司不存在: {company_id}")
            return {'total_score': 0, 'details': {}}

        # 获取公司事件
        events = self.db.get_events_by_company(company_id)

        # 计算各项评分
        scores = {}

        # 1. 融资轮次评分
        scores['funding_stage'] = self._score_funding_stage(company)

        # 2. 海外招聘评分
        scores['overseas_recruitment'] = self._score_overseas_recruitment(events)

        # 3. 目标市场评分
        scores['target_market'] = self._score_target_market(company, events)

        # 4. 近期产品发布评分
        scores['recent_product_launch'] = self._score_recent_product_launch(events)

        # 5. 出海动态评分
        scores['overseas_news'] = self._score_overseas_news(events)

        # 6. GitHub活跃度
        scores['github_activity'] = self._score_github_activity(events)

        # 7. 众筹平台
        scores['crowdfunding'] = self._score_crowdfunding(events)

        # 8. Product Hunt
        scores['producthunt'] = self._score_producthunt(events)

        # 9. 媒体报道
        scores['media_coverage'] = self._score_media_coverage(events)

        # 计算总分
        total_score = sum(scores.values())

        # 构建评分详情
        details = {
            rule: {
                'score': score,
                'max_score': self.SCORING_RULES[rule]['max_score'],
                'description': self.SCORING_RULES[rule]['description']
            }
            for rule, score in scores.items()
        }

        # 保存评分到数据库
        self.db.update_company_score(
            company_id,
            total_score,
            json.dumps(details, ensure_ascii=False)
        )

        logger.info(f"公司 {company['name']} 评分完成: {total_score}")

        return {
            'total_score': total_score,
            'details': details,
            'company_name': company['name']
        }

    def score_all_companies(self) -> List[Dict[str, Any]]:
        """批量评分所有公司"""
        logger.info("开始批量评分...")

        companies = self.db.get_all_companies()
        results = []

        for company in companies:
            result = self.score_company(company['id'])
            results.append(result)

        logger.info(f"批量评分完成，共评分 {len(results)} 家公司")

        # 统计高评分公司
        high_score_count = sum(1 for r in results if r['total_score'] >= 60)
        logger.info(f"高评分公司(>=60分): {high_score_count} 家")

        return results

    def get_high_score_companies(self, min_score: int = 60) -> List[Dict]:
        """获取高评分公司列表"""
        return self.db.get_all_companies(min_score=min_score, order_by="score DESC")

    # ==================== 评分维度方法 ====================

    def _score_funding_stage(self, company: Dict) -> int:
        """评分融资轮次"""
        funding_stage = company.get('funding_stage', '')

        if not funding_stage:
            return 0

        # 匹配融资轮次关键词
        stage_mapping = {
            'pre-seed': 5,
            'seed': 5,
            'series a': 10,
            'a': 10,
            'series b': 15,
            'b': 15,
            'series c': 20,
            'c': 20,
            'series d': 25,
            'd': 25,
            'series e': 30,
            'e': 30,
            'ipo': 30,
            '上市': 30
        }

        stage_lower = funding_stage.lower()
        for key, score in stage_mapping.items():
            if key in stage_lower:
                return min(score, self.SCORING_RULES['funding_stage']['max_score'])

        return 0

    def _score_overseas_recruitment(self, events: List[Dict]) -> int:
        """评分海外招聘"""
        # 检查最近事件中是否有海外招聘
        for event in events:
            title = event.get('title', '').lower()
            description = event.get('description', '').lower()
            event_type = event.get('event_type', '')

            if event_type == 'recruitment':
                keywords = ['overseas', 'global', 'international', '海外', '招聘']
                text = f"{title} {description}"
                if any(kw in text for kw in keywords):
                    return self.SCORING_RULES['overseas_recruitment']['max_score']

        return 0

    def _score_target_market(self, company: Dict, events: List[Dict]) -> int:
        """评分目标市场"""
        # 检查公司目标市场
        target_market = company.get('target_market', '').lower()

        if 'global' in target_market or 'international' in target_market:
            return self.SCORING_RULES['target_market']['max_score']

        # 检查事件中是否有海外相关内容
        for event in events[:5]:  # 只看最近5条
            text = f"{event.get('title', '')} {event.get('description', '')}"
            if has_overseas_indicator(text):
                return self.SCORING_RULES['target_market']['max_score']

        return 0

    def _score_recent_product_launch(self, events: List[Dict]) -> int:
        """评分近期产品发布"""
        for event in events:
            event_type = event.get('event_type', '')
            event_time = event.get('event_time', '')

            if event_type in ['product_launch', 'product']:
                # 检查是否在30天内
                dt = parse_date(event_time)
                if dt and is_recent(dt, days=30):
                    return self.SCORING_RULES['recent_product_launch']['max_score']

        return 0

    def _score_overseas_news(self, events: List[Dict]) -> int:
        """评分出海动态"""
        for event in events[:10]:
            event_time = event.get('event_time', '')
            title = event.get('title', '').lower()
            description = event.get('description', '').lower()
            text = f"{title} {description}"

            # 检查是否有出海关键词且在30天内
            if has_overseas_indicator(text):
                dt = parse_date(event_time)
                if dt and is_recent(dt, days=30):
                    return self.SCORING_RULES['overseas_news']['max_score']

        return 0

    def _score_github_activity(self, events: List[Dict]) -> int:
        """评分GitHub活跃度"""
        for event in events:
            source = event.get('source', '')

            if 'github' in source.lower():
                return self.SCORING_RULES['github_activity']['max_score']

        return 0

    def _score_crowdfunding(self, events: List[Dict]) -> int:
        """评分众筹平台"""
        for event in events:
            source = event.get('source', '').lower()

            if 'kickstarter' in source or 'indiegogo' in source:
                return self.SCORING_RULES['crowdfunding']['max_score']

        return 0

    def _score_producthunt(self, events: List[Dict]) -> int:
        """评分Product Hunt"""
        for event in events:
            source = event.get('source', '').lower()

            if 'producthunt' in source:
                return self.SCORING_RULES['producthunt']['max_score']

        return 0

    def _score_media_coverage(self, events: List[Dict]) -> int:
        """评分媒体报道"""
        for event in events[:5]:
            event_time = event.get('event_time', '')
            source = event.get('source', '')

            # 检查是否是新闻类事件
            if event.get('event_type') == 'news' or 'rss' in source.lower():
                dt = parse_date(event_time)
                if dt and is_recent(dt, days=30):
                    return self.SCORING_RULES['media_coverage']['max_score']

        return 0


def calculate_company_score(company_id: int,
                           db: Database = None,
                           config: dict = None) -> Dict[str, Any]:
    """便捷函数：计算公司评分"""
    scorer = CompanyScorer(db, config)
    return scorer.score_company(company_id)


def score_all_companies(db: Database = None,
                        config: dict = None) -> List[Dict[str, Any]]:
    """便捷函数：批量评分所有公司"""
    scorer = CompanyScorer(db, config)
    return scorer.score_all_companies()
