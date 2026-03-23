# -*- coding: utf-8 -*-
"""
OAS (Overseas AI Scout) 主程序
启动调度器 + Flask Web 服务
"""

import os
import sys
import logging
import threading
from datetime import datetime

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from utils import load_config, setup_logging, get_project_root
from models import get_database
from cleaner import DataCleaner
from scorer import CompanyScorer
from notifier import WeChatNotifier
from collectors import get_all_collectors

# 全局变量
scheduler = None
flask_app = None
config = None
db = None
logger = None


def run_pipeline(config: dict = None, db=None):
    """
    执行完整的数据处理流程
    采集 -> 清洗 -> 评分 -> 推送
    """
    global logger

    if logger is None:
        logger = logging.getLogger('OAS')

    logger.info("=" * 50)
    logger.info("开始执行数据处理流程...")
    start_time = datetime.now()

    try:
        if config is None:
            config = load_config()

        if db is None:
            db = get_database()

        # 步骤1: 采集数据
        logger.info("步骤1: 采集数据...")
        collectors = get_all_collectors(config)
        all_raw_data = []

        for collector in collectors:
            collector_name = collector.__class__.__name__
            logger.info(f"运行采集器: {collector_name}")

            try:
                # 更新采集器状态
                db.update_collector_status(collector_name, 'running', 0)

                # 执行采集
                raw_data = collector.collect()
                all_raw_data.extend(raw_data)

                # 更新采集器状态
                db.update_collector_status(
                    collector_name,
                    'success',
                    len(raw_data)
                )

                logger.info(f"  {collector_name}: 采集到 {len(raw_data)} 条数据")

            except Exception as e:
                logger.error(f"  {collector_name} 采集失败: {e}")
                db.update_collector_status(collector_name, 'error', 0, str(e))

        logger.info(f"共采集到 {len(all_raw_data)} 条原始数据")

        # 步骤2: 清洗入库
        logger.info("步骤2: 清洗数据并入库...")
        cleaner = DataCleaner(db, config)
        stats = cleaner.process_raw_data(all_raw_data)
        logger.info(f"  清洗完成: {stats}")

        # 步骤3: 评分
        logger.info("步骤3: 计算公司评分...")
        scorer = CompanyScorer(db, config)
        score_results = scorer.score_all_companies()
        logger.info(f"  评分完成: 共 {len(score_results)} 家公司")

        # 步骤4: 推送
        logger.info("步骤4: 推送高评分公司...")
        notifier = WeChatNotifier(db, config)
        notify_result = notifier.notify_high_score_companies()
        logger.info(f"  推送结果: {notify_result}")

        # 记录执行时间
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"数据处理流程完成，耗时: {elapsed:.2f}秒")
        logger.info("=" * 50)

        return {
            'success': True,
            'raw_data_count': len(all_raw_data),
            'clean_stats': stats,
            'score_count': len(score_results),
            'notify_result': notify_result,
            'elapsed_seconds': elapsed
        }

    except Exception as e:
        logger.error(f"数据处理流程执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


def run_incremental(config: dict = None, db=None):
    """
    执行增量采集（仅采集RSS等实时数据源）
    """
    global logger

    if logger is None:
        logger = logging.getLogger('OAS')

    logger.info("开始执行增量采集...")

    try:
        if config is None:
            config = load_config()

        if db is None:
            db = get_database()

        # 只运行RSS和众筹采集器
        from collectors import RSSCollector, KickstarterCollector

        collectors = [
            RSSCollector(config),
            KickstarterCollector(config)
        ]

        all_raw_data = []

        for collector in collectors:
            collector_name = collector.__class__.__name__

            try:
                raw_data = collector.collect()
                all_raw_data.extend(raw_data)
                logger.info(f"  {collector_name}: 采集到 {len(raw_data)} 条数据")
            except Exception as e:
                logger.error(f"  {collector_name} 采集失败: {e}")

        # 清洗入库
        if all_raw_data:
            cleaner = DataCleaner(db, config)
            stats = cleaner.process_raw_data(all_raw_data)

            # 重新评分
            scorer = CompanyScorer(db, config)
            scorer.score_all_companies()

            logger.info(f"增量采集完成: {stats}")

        return {'success': True}

    except Exception as e:
        logger.error(f"增量采集失败: {e}")
        return {'success': False, 'error': str(e)}


def start_scheduler(config: dict):
    """启动定时任务调度器"""
    global scheduler, logger

    scheduler = BackgroundScheduler()
    scheduler_logger = logging.getLogger('APScheduler')

    scheduler_config = config.get('scheduler', {})

    # 全量运行 - 每天8点
    full_run = scheduler_config.get('full_run', {})
    if full_run.get('enabled', True):
        hour = full_run.get('hour', 8)
        minute = full_run.get('minute', 0)
        scheduler.add_job(
            lambda: run_pipeline(config),
            'cron',
            hour=hour,
            minute=minute,
            id='full_run',
            name='全量采集',
            replace_existing=True
        )
        logger.info(f"已设置全量采集任务: 每天 {hour:02d}:{minute:02d}")

    # 增量运行 - 每隔2小时
    incremental_run = scheduler_config.get('incremental_run', {})
    if incremental_run.get('enabled', True):
        hours = incremental_run.get('hours', 2)
        scheduler.add_job(
            lambda: run_incremental(config),
            'interval',
            hours=hours,
            id='incremental_run',
            name='增量采集',
            replace_existing=True
        )
        logger.info(f"已设置增量采集任务: 每 {hours} 小时")

    scheduler.start()
    logger.info("定时任务调度器已启动")


def start_flask(config: dict, db):
    """启动 Flask Web 服务"""
    global flask_app, logger

    from web.app import create_app

    flask_config = config.get('flask', {})
    host = flask_config.get('host', '0.0.0.0')
    port = flask_config.get('port', 5000)
    debug = flask_config.get('debug', False)

    flask_app = create_app(db_path=db.db_path)

    logger.info(f"启动 Flask Web 服务: http://{host}:{port}")
    flask_app.run(host=host, port=port, debug=debug, threaded=True)


def main():
    """主函数"""
    global config, db, logger

    # 加载配置
    project_root = get_project_root()
    config_path = os.path.join(project_root, 'config.yaml')

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"无法加载配置文件: {e}")
        print("请确保 config.yaml 文件存在")
        sys.exit(1)

    # 设置日志
    logger = setup_logging(config)
    logger.info("智汇出海情报雷达 (OAS) 启动...")
    logger.info(f"项目根目录: {project_root}")

    # 初始化数据库
    db_path = os.path.join(project_root, config.get('database', {}).get('path', 'data/oas.db'))
    db = get_database(db_path)
    logger.info(f"数据库路径: {db_path}")

    # 启动定时任务调度器
    start_scheduler(config)

    # 在后台线程运行定时任务，确保Flask主线程不会被阻塞
    def run_scheduler_thread():
        # 保持调度器运行
        import time
        while True:
            time.sleep(60)

    scheduler_thread = threading.Thread(target=run_scheduler_thread, daemon=True)
    scheduler_thread.start()

    # 启动Flask Web服务（会阻塞）
    start_flask(config, db)


if __name__ == '__main__':
    main()
