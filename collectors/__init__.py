# -*- coding: utf-8 -*-
"""
OAS 数据采集器模块
"""

from .kickstarter import KickstarterCollector
from .producthunt import ProductHuntCollector
from .rss_feeds import RSSCollector
from .github import GitHubCollector
from .itjuzi import ITJuziCollector

__all__ = [
    'KickstarterCollector',
    'ProductHuntCollector',
    'RSSCollector',
    'GitHubCollector',
    'ITJuziCollector',
]


def get_all_collectors(config: dict):
    """获取所有启用的采集器"""
    collectors = []

    if config.get('collectors', {}).get('kickstarter', {}).get('enabled'):
        collectors.append(KickstarterCollector(config))

    if config.get('collectors', {}).get('producthunt', {}).get('enabled'):
        collectors.append(ProductHuntCollector(config))

    if config.get('collectors', {}).get('rss_feeds', {}).get('enabled'):
        collectors.append(RSSCollector(config))

    if config.get('collectors', {}).get('github', {}).get('enabled'):
        collectors.append(GitHubCollector(config))

    if config.get('collectors', {}).get('itjuzi', {}).get('enabled'):
        collectors.append(ITJuziCollector(config))

    return collectors
