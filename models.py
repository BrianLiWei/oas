# -*- coding: utf-8 -*-
"""
OAS 数据库模型
定义公司(companies)和事件(events)表结构及操作类
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Database:
    """数据库操作类"""

    def __init__(self, db_path: str = "data/oas.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.text_factory = str
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建 companies 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                website TEXT,
                description TEXT,
                logo_url TEXT,
                industry TEXT,
                target_market TEXT,
                funding_stage TEXT,
                location TEXT,
                contact_email TEXT,
                score INTEGER DEFAULT 0,
                score_details TEXT,
                last_event_time TEXT,
                is_chinese_overseas BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建 events 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                event_time TEXT,
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        ''')

        # 创建推送记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                event_id INTEGER,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                message TEXT,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        ''')

        # 创建采集器状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collector_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collector_name TEXT NOT NULL UNIQUE,
                last_run_time TEXT,
                status TEXT,
                items_collected INTEGER DEFAULT 0,
                error_message TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成: {self.db_path}")

    # ==================== 公司操作 ====================

    def add_company(self, company_data: Dict[str, Any]) -> Optional[int]:
        """添加新公司，返回公司ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO companies (
                    name, website, description, logo_url, industry,
                    target_market, funding_stage, location, contact_email,
                    is_chinese_overseas, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_data.get('name'),
                company_data.get('website'),
                company_data.get('description'),
                company_data.get('logo_url'),
                company_data.get('industry'),
                company_data.get('target_market'),
                company_data.get('funding_stage'),
                company_data.get('location'),
                company_data.get('contact_email'),
                company_data.get('is_chinese_overseas', 0),
                datetime.now().isoformat()
            ))
            conn.commit()
            company_id = cursor.lastrowid

            # 获取已存在公司的ID
            if company_id == 0:
                cursor.execute('SELECT id FROM companies WHERE name = ?', (company_data.get('name'),))
                row = cursor.fetchone()
                company_id = row['id'] if row else None

            conn.close()
            logger.info(f"添加/更新公司: {company_data.get('name')}, ID: {company_id}")
            return company_id

        except Exception as e:
            logger.error(f"添加公司失败: {e}")
            conn.close()
            return None

    def get_company_by_name(self, name: str) -> Optional[Dict]:
        """根据公司名获取公司信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_company_by_id(self, company_id: int) -> Optional[Dict]:
        """根据ID获取公司信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_all_companies(self, min_score: int = 0, funding_stage: str = None,
                          order_by: str = "score DESC") -> List[Dict]:
        """获取所有公司列表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM companies WHERE score >= ?'
        params = [min_score]

        if funding_stage:
            query += ' AND funding_stage = ?'
            params.append(funding_stage)

        query += f' ORDER BY {order_by}'
        cursor.execute(query, params)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_company_score(self, company_id: int, score: int, score_details: str = None):
        """更新公司评分"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE companies
            SET score = ?, score_details = ?, updated_at = ?
            WHERE id = ?
        ''', (score, score_details, datetime.now().isoformat(), company_id))
        conn.commit()
        conn.close()

    def update_company(self, company_id: int, company_data: Dict[str, Any]):
        """更新公司信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        fields = []
        values = []
        for key, value in company_data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)

        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(company_id)

        cursor.execute(f'''
            UPDATE companies SET {', '.join(fields)} WHERE id = ?
        ''', values)
        conn.commit()
        conn.close()

    # ==================== 事件操作 ====================

    def add_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """添加新事件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO events (
                    company_id, source, event_type, title, description,
                    url, event_time, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_data.get('company_id'),
                event_data.get('source'),
                event_data.get('event_type'),
                event_data.get('title'),
                event_data.get('description'),
                event_data.get('url'),
                event_data.get('event_time'),
                event_data.get('raw_data')
            ))
            conn.commit()
            event_id = cursor.lastrowid

            # 更新公司的最后事件时间
            if event_data.get('company_id'):
                cursor.execute('''
                    UPDATE companies
                    SET last_event_time = ?, updated_at = ?
                    WHERE id = ?
                ''', (event_data.get('event_time'), datetime.now().isoformat(),
                      event_data.get('company_id')))
                conn.commit()

            conn.close()
            logger.info(f"添加事件: {event_data.get('title')}, ID: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"添加事件失败: {e}")
            conn.close()
            return None

    def get_events_since(self, days: int = 30) -> List[Dict]:
        """获取指定天数内的事件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT e.*, c.name as company_name
            FROM events e
            LEFT JOIN companies c ON e.company_id = c.id
            WHERE e.created_at >= datetime('now', '-' || ? || ' days')
            ORDER BY e.created_at DESC
        ''', (days,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_events_by_company(self, company_id: int) -> List[Dict]:
        """获取某公司的所有事件"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM events
            WHERE company_id = ?
            ORDER BY event_time DESC
        ''', (company_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def event_exists(self, source: str, url: str) -> bool:
        """检查事件是否已存在（用于去重）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM events WHERE source = ? AND url = ?', (source, url))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    # ==================== 推送记录操作 ====================

    def add_notification(self, company_id: int, event_id: int, message: str):
        """记录推送"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (company_id, event_id, message)
            VALUES (?, ?, ?)
        ''', (company_id, event_id, message))
        conn.commit()
        conn.close()

    def get_recent_notification(self, company_id: int, hours: int = 24) -> Optional[Dict]:
        """获取公司最近是否已推送"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM notifications
            WHERE company_id = ?
            AND sent_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY sent_at DESC
            LIMIT 1
        ''', (company_id, hours))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_notification_count_today(self) -> int:
        """获取今日推送数量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as count FROM notifications
            WHERE date(sent_at) = date('now')
        ''')
        row = cursor.fetchone()
        conn.close()
        return row['count'] if row else 0

    # ==================== 采集器状态操作 ====================

    def update_collector_status(self, collector_name: str, status: str,
                                items_collected: int = 0, error_message: str = None):
        """更新采集器状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO collector_status (
                collector_name, last_run_time, status, items_collected, error_message
            ) VALUES (?, ?, ?, ?, ?)
        ''', (collector_name, datetime.now().isoformat(), status, items_collected, error_message))
        conn.commit()
        conn.close()

    def get_collector_status(self, collector_name: str) -> Optional[Dict]:
        """获取采集器状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM collector_status WHERE collector_name = ?
        ''', (collector_name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_collector_status(self) -> List[Dict]:
        """获取所有采集器状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collector_status ORDER BY last_run_time DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== 统计操作 ====================

    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 公司总数
        cursor.execute('SELECT COUNT(*) as count FROM companies')
        total_companies = cursor.fetchone()['count']

        # 高评分公司数
        cursor.execute('SELECT COUNT(*) as count FROM companies WHERE score >= 60')
        high_score_companies = cursor.fetchone()['count']

        # 事件总数
        cursor.execute('SELECT COUNT(*) as count FROM events')
        total_events = cursor.fetchone()['count']

        # 今日新增事件
        cursor.execute('SELECT COUNT(*) as count FROM events WHERE date(created_at) = date("now")')
        today_events = cursor.fetchone()['count']

        # 今日推送数
        cursor.execute('SELECT COUNT(*) as count FROM notifications WHERE date(sent_at) = date("now")')
        today_notifications = cursor.fetchone()['count']

        conn.close()

        return {
            'total_companies': total_companies,
            'high_score_companies': high_score_companies,
            'total_events': total_events,
            'today_events': today_events,
            'today_notifications': today_notifications
        }

    def get_last_events(self, limit: int = 20) -> List[Dict]:
        """获取最近的事件"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, c.name as company_name, c.score as company_score
            FROM events e
            LEFT JOIN companies c ON e.company_id = c.id
            ORDER BY e.created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# 全局数据库实例（延迟初始化）
_db_instance = None


def get_database(db_path: str = "data/oas.db") -> Database:
    """获取数据库单例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance
