# -*- coding: utf-8 -*-
"""
OAS Flask Web 应用
提供Web界面查看公司信息、事件和系统状态
"""

import os
import sys
import json
import logging
import threading
from flask import Flask, render_template, jsonify, request, redirect, url_for
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logger = logging.getLogger('OAS-Web')


def create_app(config_path: str = None, db_path: str = None):
    """创建Flask应用"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'oas-secret-key-change-in-production'

    # 加载配置
    if config_path is None:
        config_path = os.path.join(project_root, 'config.yaml')

    try:
        from utils import load_config
        config = load_config(config_path)
    except Exception as e:
        logger.warning(f"无法加载配置文件，使用默认配置: {e}")
        config = {}

    # 初始化数据库
    if db_path is None:
        db_path = os.path.join(project_root, config.get('database', {}).get('path', 'data/oas.db'))

    from models import get_database
    db = get_database(db_path)

    # 延迟导入（避免循环依赖）
    scorer = None
    notifier = None

    # ==================== 路由 ====================

    @app.route('/')
    def index():
        """公司列表页"""
        # 获取筛选参数
        min_score = request.args.get('min_score', 0, type=int)
        funding_stage = request.args.get('funding_stage', '')
        sort = request.args.get('sort', 'score')

        # 获取公司列表
        if sort == 'score':
            order_by = 'score DESC'
        elif sort == 'name':
            order_by = 'name ASC'
        elif sort == 'updated':
            order_by = 'updated_at DESC'
        else:
            order_by = 'score DESC'

        companies = db.get_all_companies(
            min_score=min_score,
            funding_stage=funding_stage if funding_stage else None,
            order_by=order_by
        )

        # 统计信息
        stats = db.get_statistics()

        return render_template('index.html',
                             companies=companies,
                             stats=stats,
                             min_score=min_score,
                             funding_stage=funding_stage,
                             sort=sort)

    @app.route('/company/<int:company_id>')
    def company_detail(company_id):
        """公司详情页"""
        company = db.get_company_by_id(company_id)

        if not company:
            return "公司不存在", 404

        # 获取公司事件
        events = db.get_events_by_company(company_id)

        # 解析评分详情
        score_details = {}
        if company.get('score_details'):
            try:
                score_details = json.loads(company['score_details'])
            except:
                pass

        return render_template('company.html',
                             company=company,
                             events=events,
                             score_details=score_details)

    @app.route('/dashboard')
    def dashboard():
        """监控仪表板"""
        # 统计信息
        stats = db.get_statistics()

        # 采集器状态
        collector_status = db.get_all_collector_status()

        # 最近事件
        recent_events = db.get_last_events(limit=20)

        # 今日推送数
        today_notifications = db.get_notification_count_today()

        return render_template('dashboard.html',
                             stats=stats,
                             collector_status=collector_status,
                             recent_events=recent_events,
                             today_notifications=today_notifications)

    # ==================== API 接口 ====================

    @app.route('/api/companies')
    def api_companies():
        """获取公司列表API"""
        companies = db.get_all_companies()
        return jsonify({
            'success': True,
            'data': companies,
            'count': len(companies)
        })

    @app.route('/api/company/<int:company_id>')
    def api_company(company_id):
        """获取公司详情API"""
        company = db.get_company_by_id(company_id)

        if not company:
            return jsonify({'success': False, 'message': 'Company not found'}), 404

        events = db.get_events_by_company(company_id)

        return jsonify({
            'success': True,
            'data': {
                'company': company,
                'events': events
            }
        })

    @app.route('/api/events')
    def api_events():
        """获取事件列表API"""
        days = request.args.get('days', 30, type=int)
        events = db.get_events_since(days=days)
        return jsonify({
            'success': True,
            'data': events,
            'count': len(events)
        })

    @app.route('/api/stats')
    def api_stats():
        """获取统计信息API"""
        stats = db.get_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })

    @app.route('/api/run', methods=['POST'])
    def api_run_pipeline():
        """手动触发采集任务"""
        try:
            # 导入主模块的运行函数
            from main import run_pipeline

            # 在后台线程中运行
            def run_in_background():
                try:
                    run_pipeline(config, db)
                except Exception as e:
                    logger.error(f"采集任务失败: {e}")

            thread = threading.Thread(target=run_in_background)
            thread.start()

            return jsonify({
                'success': True,
                'message': '采集任务已启动'
            })

        except Exception as e:
            logger.error(f"启动采集任务失败: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/notify', methods=['POST'])
    def api_notify():
        """手动触发推送"""
        try:
            from notifier import WeChatNotifier
            notifier = WeChatNotifier(db, config)
            result = notifier.notify_high_score_companies()
            return jsonify({
                'success': True,
                'data': result
            })
        except Exception as e:
            logger.error(f"推送失败: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/api/score', methods=['POST'])
    def api_score():
        """手动触发评分"""
        try:
            from scorer import CompanyScorer
            scorer = CompanyScorer(db, config)
            result = scorer.score_all_companies()
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result)
            })
        except Exception as e:
            logger.error(f"评分失败: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', error='页面不存在'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error='服务器错误'), 500

    return app


# 开发服务器入口
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)


# Vercel WSGI 入口
app = create_app()
