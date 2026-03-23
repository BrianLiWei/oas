# -*- coding: utf-8 -*-
"""
OAS 企业微信推送模块
通过企业微信机器人发送高潜力客户通知到手机
"""

import requests
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import Database, get_database

logger = logging.getLogger(__name__)


class WeChatNotifier:
    """企业微信机器人通知器"""

    def __init__(self, db: Database = None, config: dict = None):
        self.db = db or get_database()
        self.config = config or {}
        self.wechat_config = self.config.get('wechat', {})
        self.webhook_url = self.wechat_config.get('webhook_url', '')
        self.mention_list = self.wechat_config.get('mention_list', [])
        self.mention_mobile_list = self.wechat_config.get('mention_mobile_list', [])

        # 推送配置
        notification_config = self.config.get('notification', {})
        self.cooldown_hours = notification_config.get('cooldown_hours', 24)
        self.max_per_day = notification_config.get('max_per_day', 10)

        # 评分阈值
        scoring_config = self.config.get('scoring', {})
        self.high_priority_threshold = scoring_config.get('thresholds', {}).get('high_priority', 60)

    def notify_high_score_companies(self) -> Dict[str, Any]:
        """推送高评分公司"""
        if not self.webhook_url:
            logger.warning("企业微信 webhook URL 未配置，跳过推送")
            return {'success': False, 'message': 'Webhook URL not configured'}

        # 检查今日推送数量
        today_count = self.db.get_notification_count_today()
        if today_count >= self.max_per_day:
            logger.info(f"今日推送已达上限 ({self.max_per_day})，跳过推送")
            return {'success': False, 'message': 'Daily limit reached'}

        # 获取高评分公司
        companies = self._get_companies_to_notify()

        if not companies:
            logger.info("没有需要推送的公司")
            return {'success': True, 'message': 'No companies to notify', 'count': 0}

        results = []
        sent_count = 0

        for company in companies:
            if today_count + sent_count >= self.max_per_day:
                break

            success = self._notify_company(company)
            if success:
                sent_count += 1

        logger.info(f"推送完成，成功 {sent_count} 条")

        return {
            'success': True,
            'message': f'Sent {sent_count} notifications',
            'count': sent_count,
            'total_candidates': len(companies)
        }

    def _get_companies_to_notify(self) -> List[Dict]:
        """获取需要推送的公司列表"""
        # 获取高评分公司
        companies = self.db.get_all_companies(min_score=self.high_priority_threshold)

        to_notify = []

        for company in companies:
            # 检查是否在冷却期内
            recent_notification = self.db.get_recent_notification(
                company['id'],
                hours=self.cooldown_hours
            )

            if not recent_notification:
                # 检查是否有最近事件
                events = self.db.get_events_by_company(company['id'])
                if events:
                    to_notify.append(company)

        return to_notify

    def _notify_company(self, company: Dict) -> bool:
        """推送单个公司"""
        try:
            # 构建消息
            message = self._build_message(company)

            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('errcode') == 0:
                    # 记录推送
                    events = self.db.get_events_by_company(company['id'])
                    if events:
                        self.db.add_notification(
                            company['id'],
                            events[0]['id'],
                            message.get('markdown', {}).get('content', '')[:500]
                        )

                    logger.info(f"成功推送公司: {company['name']}")
                    return True
                else:
                    logger.error(f"企业微信返回错误: {result}")
                    return False
            else:
                logger.error(f"企业微信请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"推送失败: {e}")
            return False

    def _build_message(self, company: Dict) -> Dict[str, Any]:
        """构建企业微信消息"""
        # 获取公司最新事件
        events = self.db.get_events_by_company(company['id'])
        latest_event = events[0] if events else {}

        # 构建Markdown消息
        markdown_content = f"""## 🔥 新发现：高潜力AI出海公司

**公司名称**: {company.get('name', 'Unknown')}

**评分**: {company.get('score', 0)}/100

**行业**: {company.get('industry', 'Unknown')}
**目标市场**: {company.get('target_market', 'Unknown')}
**融资轮次**: {company.get('funding_stage', 'Unknown')}

**最新动态**:
> {latest_event.get('title', '暂无')}
> {latest_event.get('description', '')[:100]}...

**更多信息**: {company.get('website', '暂无')}
"""

        # 添加提及
        mention = {}
        if self.mention_list:
            mention['mentioned_list'] = self.mention_list
        if self.mention_mobile_list:
            mention['mentioned_mobile_list'] = self.mention_mobile_list

        message = {
            'msgtype': 'markdown',
            'markdown': {
                'content': markdown_content
            }
        }

        if mention:
            message['markdown'].update(mention)

        return message

    def send_custom_message(self, title: str, content: str) -> bool:
        """发送自定义消息"""
        if not self.webhook_url:
            logger.warning("企业微信 webhook URL 未配置")
            return False

        try:
            message = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': f"## {title}\n\n{content}"
                }
            }

            if self.mention_mobile_list:
                message['markdown']['mentioned_mobile_list'] = self.mention_mobile_list

            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('errcode') == 0

            return False

        except Exception as e:
            logger.error(f"发送自定义消息失败: {e}")
            return False

    def test_webhook(self) -> bool:
        """测试 webhook 是否可用"""
        return self.send_custom_message(
            "OAS 测试消息",
            "智汇出海情报雷达系统已正常运行！\n\n如收到此消息，说明企业微信机器人配置正确。"
        )


def notify_companies(db: Database = None, config: dict = None) -> Dict[str, Any]:
    """便捷函数：推送高评分公司"""
    notifier = WeChatNotifier(db, config)
    return notifier.notify_high_score_companies()


def send_notification(title: str, content: str,
                     db: Database = None,
                     config: dict = None) -> bool:
    """便捷函数：发送自定义通知"""
    notifier = WeChatNotifier(db, config)
    return notifier.send_custom_message(title, content)
