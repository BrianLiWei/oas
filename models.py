# -*- coding: utf-8 -*-
"""
OAS 数据库模型
支持两种模式：
1. SQLite（本地开发）
2. 内存存储（Vercel无服务器环境）
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class InMemoryDatabase:
    """内存数据库 - 用于Vercel等无服务器环境"""

    def __init__(self):
        self.companies = []
        self.events = []
        self.notifications = []
        self.collector_status = []
        self._company_counter = 1
        self._event_counter = 1

    def add_company(self, company_data: Dict[str, Any]) -> Optional[int]:
        """添加公司"""
        # 检查是否已存在
        for c in self.companies:
            if c['name'] == company_data.get('name'):
                c.update(company_data)
                c['updated_at'] = datetime.now().isoformat()
                return c['id']

        company = {
            'id': self._company_counter,
            'name': company_data.get('name', 'Unknown'),
            'website': company_data.get('website'),
            'description': company_data.get('description'),
            'logo_url': company_data.get('logo_url'),
            'industry': company_data.get('industry'),
            'target_market': company_data.get('target_market'),
            'funding_stage': company_data.get('funding_stage'),
            'location': company_data.get('location'),
            'contact_email': company_data.get('contact_email'),
            'score': company_data.get('score', 0),
            'score_details': company_data.get('score_details'),
            'last_event_time': company_data.get('last_event_time'),
            'is_chinese_overseas': company_data.get('is_chinese_overseas', 0),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.companies.append(company)
        self._company_counter += 1
        return company['id']

    def get_company_by_name(self, name: str) -> Optional[Dict]:
        for c in self.companies:
            if c['name'] == name:
                return c
        return None

    def get_company_by_id(self, company_id: int) -> Optional[Dict]:
        for c in self.companies:
            if c['id'] == company_id:
                return c
        return None

    def get_all_companies(self, min_score: int = 0, funding_stage: str = None, order_by: str = "score DESC") -> List[Dict]:
        result = [c for c in self.companies if c.get('score', 0) >= min_score]
        if funding_stage:
            result = [c for c in result if c.get('funding_stage') == funding_stage]
        # 简单排序
        if 'score' in order_by:
            result.sort(key=lambda x: x.get('score', 0), reverse=True)
        return result

    def update_company_score(self, company_id: int, score: int, score_details: str = None):
        for c in self.companies:
            if c['id'] == company_id:
                c['score'] = score
                c['score_details'] = score_details
                c['updated_at'] = datetime.now().isoformat()
                break

    def update_company(self, company_id: int, company_data: Dict[str, Any]):
        for c in self.companies:
            if c['id'] == company_id:
                c.update(company_data)
                c['updated_at'] = datetime.now().isoformat()
                break

    def add_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        event = {
            'id': self._event_counter,
            'company_id': event_data.get('company_id'),
            'source': event_data.get('source'),
            'event_type': event_data.get('event_type'),
            'title': event_data.get('title'),
            'description': event_data.get('description'),
            'url': event_data.get('url'),
            'event_time': event_data.get('event_time'),
            'raw_data': event_data.get('raw_data'),
            'created_at': datetime.now().isoformat()
        }
        self.events.append(event)
        self._event_counter += 1
        return event['id']

    def get_events_since(self, days: int = 30) -> List[Dict]:
        return self.events[-20:]  # 返回最近20条

    def get_events_by_company(self, company_id: int) -> List[Dict]:
        return [e for e in self.events if e.get('company_id') == company_id]

    def event_exists(self, source: str, url: str) -> bool:
        for e in self.events:
            if e.get('source') == source and e.get('url') == url:
                return True
        return False

    def add_notification(self, company_id: int, event_id: int, message: str):
        self.notifications.append({
            'id': len(self.notifications) + 1,
            'company_id': company_id,
            'event_id': event_id,
            'sent_at': datetime.now().isoformat(),
            'message': message
        })

    def get_recent_notification(self, company_id: int, hours: int = 24) -> Optional[Dict]:
        return None  # 简化实现

    def get_notification_count_today(self) -> int:
        return len(self.notifications)

    def update_collector_status(self, collector_name: str, status: str, items_collected: int = 0, error_message: str = None):
        for s in self.collector_status:
            if s['collector_name'] == collector_name:
                s.update({
                    'last_run_time': datetime.now().isoformat(),
                    'status': status,
                    'items_collected': items_collected,
                    'error_message': error_message
                })
                return
        self.collector_status.append({
            'id': len(self.collector_status) + 1,
            'collector_name': collector_name,
            'last_run_time': datetime.now().isoformat(),
            'status': status,
            'items_collected': items_collected,
            'error_message': error_message
        })

    def get_collector_status(self, collector_name: str) -> Optional[Dict]:
        for s in self.collector_status:
            if s['collector_name'] == collector_name:
                return s
        return None

    def get_all_collector_status(self) -> List[Dict]:
        return self.collector_status

    def get_statistics(self) -> Dict:
        return {
            'total_companies': len(self.companies),
            'high_score_companies': len([c for c in self.companies if c.get('score', 0) >= 60]),
            'total_events': len(self.events),
            'today_events': len(self.events),
            'today_notifications': len(self.notifications)
        }

    def get_last_events(self, limit: int = 20) -> List[Dict]:
        result = []
        for e in self.events[-limit:]:
            company = self.get_company_by_id(e.get('company_id', 0))
            e_copy = dict(e)
            e_copy['company_name'] = company['name'] if company else 'Unknown'
            e_copy['company_score'] = company.get('score', 0) if company else 0
            result.append(e_copy)
        return result

    # 预填充一些示例数据
    def seed_sample_data(self):
        sample_companies = [
            {'name': 'Shenzhen AI Labs', 'industry': 'AI', 'target_market': 'Global', 'score': 45, 'description': 'AI company expanding to overseas markets'},
            {'name': 'Beijing Tech Co', 'industry': 'Hardware', 'target_market': 'Global', 'score': 35, 'description': 'Smart hardware company'},
            {'name': 'Hangzhou Innovation', 'industry': 'SaaS', 'target_market': 'China', 'score': 25, 'description': 'Cloud software provider'},
        ]
        for c in sample_companies:
            self.add_company(c)


# 内存数据库单例（用于Vercel）
_memory_db = None


def get_database(db_path: str = None) -> Any:
    """获取数据库实例"""
    global _memory_db

    # 检测是否在Vercel环境
    is_vercel = os.environ.get('VERCEL') == '1' or (db_path and '/var/task/' in db_path)

    if is_vercel:
        # 使用内存数据库
        if _memory_db is None:
            _memory_db = InMemoryDatabase()
            _memory_db.seed_sample_data()  # 预填充示例数据
        return _memory_db
    else:
        # 使用SQLite数据库
        return SQLiteDatabase(db_path)


class SQLiteDatabase:
    """SQLite数据库 - 用于本地开发"""

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

    # 公司操作
    def add_company(self, company_data: Dict[str, Any]) -> Optional[int]:
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

            if company_id == 0:
                cursor.execute('SELECT id FROM companies WHERE name = ?', (company_data.get('name'),))
                row = cursor.fetchone()
                company_id = row['id'] if row else None

            conn.close()
            return company_id

        except Exception as e:
            logger.error(f"添加公司失败: {e}")
            conn.close()
            return None

    def get_company_by_name(self, name: str) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_company_by_id(self, company_id: int) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_companies(self, min_score: int = 0, funding_stage: str = None, order_by: str = "score DESC") -> List[Dict]:
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
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE companies SET score = ?, score_details = ?, updated_at = ? WHERE id = ?
        ''', (score, score_details, datetime.now().isoformat(), company_id))
        conn.commit()
        conn.close()

    def update_company(self, company_id: int, company_data: Dict[str, Any]):
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

        cursor.execute(f'UPDATE companies SET {", ".join(fields)} WHERE id = ?', values)
        conn.commit()
        conn.close()

    # 事件操作
    def add_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO events (company_id, source, event_type, title, description, url, event_time, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.close()
            return event_id

        except Exception as e:
            logger.error(f"添加事件失败: {e}")
            conn.close()
            return None

    def get_events_since(self, days: int = 30) -> List[Dict]:
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
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM events WHERE company_id = ? ORDER BY event_time DESC
        ''', (company_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def event_exists(self, source: str, url: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM events WHERE source = ? AND url = ?', (source, url))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    # 推送记录
    def add_notification(self, company_id: int, event_id: int, message: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (company_id, event_id, message) VALUES (?, ?, ?)
        ''', (company_id, event_id, message))
        conn.commit()
        conn.close()

    def get_recent_notification(self, company_id: int, hours: int = 24) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM notifications
            WHERE company_id = ? AND sent_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY sent_at DESC LIMIT 1
        ''', (company_id, hours))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_notification_count_today(self) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM notifications WHERE date(sent_at) = date("now")')
        row = cursor.fetchone()
        conn.close()
        return row['count'] if row else 0

    # 采集器状态
    def update_collector_status(self, collector_name: str, status: str, items_collected: int = 0, error_message: str = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO collector_status (collector_name, last_run_time, status, items_collected, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (collector_name, datetime.now().isoformat(), status, items_collected, error_message))
        conn.commit()
        conn.close()

    def get_collector_status(self, collector_name: str) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collector_status WHERE collector_name = ?', (collector_name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_collector_status(self) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collector_status ORDER BY last_run_time DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # 统计
    def get_statistics(self) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM companies')
        total_companies = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM companies WHERE score >= 60')
        high_score_companies = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM events')
        total_events = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM events WHERE date(created_at) = date("now")')
        today_events = cursor.fetchone()['count']

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
