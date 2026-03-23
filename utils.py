# -*- coding: utf-8 -*-
"""
OAS 工具函数模块
包含日期处理、字符串清洗、日志等公共函数
"""

import re
import os
import yaml
import logging
import logging.handlers
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path


# ==================== 配置管理 ====================

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载配置文件"""
    # 尝试多个可能的配置路径
    possible_paths = [
        config_path,
        os.path.join(os.path.dirname(__file__), config_path),
        os.path.join(os.path.dirname(__file__), '..', config_path),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(f"配置文件未找到: {config_path}")


def get_project_root() -> str:
    """获取项目根目录"""
    return os.path.dirname(os.path.abspath(__file__))


# ==================== 日志配置 ====================

def setup_logging(config: Dict[str, Any] = None) -> logging.Logger:
    """配置日志系统"""
    if config is None:
        config = load_config()

    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/oas.log')
    max_bytes = log_config.get('max_bytes', 10 * 1024 * 1024)
    backup_count = log_config.get('backup_count', 5)

    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建logger
    logger = logging.getLogger('OAS')
    logger.setLevel(level)

    # 清除已有的处理器
    logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件处理器（带轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# ==================== 日期处理 ====================

def parse_date(date_str: str) -> Optional[datetime]:
    """解析各种日期格式"""
    if not date_str:
        return None

    date_str = date_str.strip()

    # 常见格式
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d',
        '%Y/%m/%d %H:%M:%S',
        '%d/%m/%Y',
        '%d/%m/%Y %H:%M:%S',
        '%B %d, %Y',
        '%b %d, %Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%fZ',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # 相对日期处理
    now = datetime.now()
    date_lower = date_str.lower()

    if 'hour' in date_lower or '小时' in date_lower:
        match = re.search(r'(\d+)', date_str)
        if match:
            return now - timedelta(hours=int(match.group(1)))

    if 'day' in date_lower or '天' in date_lower:
        match = re.search(r'(\d+)', date_str)
        if match:
            return now - timedelta(days=int(match.group(1)))

    if 'week' in date_lower or '周' in date_lower:
        match = re.search(r'(\d+)', date_str)
        if match:
            return now - timedelta(weeks=int(match.group(1)))

    if 'month' in date_lower or '月' in date_lower:
        match = re.search(r'(\d+)', date_str)
        if match:
            return now - timedelta(days=int(match.group(1)) * 30)

    return None


def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化日期时间"""
    if dt is None:
        return ''
    return dt.strftime(format_str)


def is_recent(dt: datetime, days: int = 30) -> bool:
    """判断日期是否在最近N天内"""
    if dt is None:
        return False
    return (datetime.now() - dt).days <= days


def get_date_days_ago(days: int) -> datetime:
    """获取N天前的日期"""
    return datetime.now() - timedelta(days=days)


# ==================== 字符串处理 ====================

def clean_text(text: str) -> str:
    """清洗文本，去除多余空白和特殊字符"""
    if not text:
        return ''

    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # 去除常见的HTML实体
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')

    return text


def extract_domain(url: str) -> str:
    """从URL提取域名"""
    if not url:
        return ''

    # 去除协议
    url = re.sub(r'^https?://', '', url)
    # 去除路径
    url = url.split('/')[0]
    # 去除端口
    url = url.split(':')[0]

    return url


def is_valid_url(url: str) -> bool:
    """验证URL是否有效"""
    if not url:
        return False
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def normalize_company_name(name: str) -> str:
    """标准化公司名称"""
    if not name:
        return ''

    # 去除多余空白
    name = clean_text(name)

    # 去除常见后缀
    suffixes = [' Inc', ' Inc.', ' LLC', ' Ltd', ' Ltd.', ' Co.', ' Co', ' Corp', ' Corp.']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()

    return name


# ==================== 中国公司识别 ====================

CHINESE_KEYWORDS = [
    '中国', 'China', 'Chinese', '深圳', '北京', '上海', '杭州', '广州',
    '香港', 'Hong Kong', 'Taiwan', '台湾', '新加坡'
]

OVERSEAS_KEYWORDS = [
    'overseas', 'global', 'international', 'worldwide', '出海',
    '海外', 'global version', 'worldwide launch', 'US', 'USA',
    'United States', 'Europe', 'European'
]


def is_chinese_company(name: str, description: str = '', keywords: List[str] = None) -> bool:
    """判断是否为中国公司"""
    if keywords is None:
        keywords = CHINESE_KEYWORDS

    text = f"{name} {description}".lower()

    for keyword in keywords:
        if keyword.lower() in text:
            return True

    return False


def has_overseas_indicator(text: str, keywords: List[str] = None) -> bool:
    """判断是否有出海迹象"""
    if keywords is None:
        keywords = OVERSEAS_KEYWORDS

    text = text.lower()

    for keyword in keywords:
        if keyword.lower() in text:
            return True

    return False


# ==================== 融资轮次识别 ====================

FUNDING_STAGES = {
    'pre-seed': 0,
    'seed': 5,
    'series a': 10,
    'a轮': 10,
    'series b': 15,
    'b轮': 15,
    'series c': 20,
    'c轮': 20,
    'series d': 25,
    'd轮': 25,
    'series e': 30,
    'e轮': 30,
    'ipo': 30,
    '上市': 30
}


def parse_funding_stage(text: str) -> Optional[str]:
    """解析融资轮次"""
    if not text:
        return None

    text = text.lower()

    for stage in FUNDING_STAGES.keys():
        if stage in text:
            return stage

    return None


def get_funding_score(stage: str) -> int:
    """获取融资轮次对应的分数"""
    if not stage:
        return 0
    return FUNDING_STAGES.get(stage.lower(), 0)


# ==================== 工具函数 ====================

def truncate_text(text: str, max_length: int = 200) -> str:
    """截断文本"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def dict_to_json_safe(data: Dict) -> Dict:
    """将字典转换为JSON安全的格式"""
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, (list, dict)):
            result[key] = str(value)
        else:
            result[key] = value
    return result


# ==================== 文件操作 ====================

def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def read_file(path: str) -> str:
    """读取文件内容"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path: str, content: str):
    """写入文件内容"""
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def file_exists(path: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(path)
