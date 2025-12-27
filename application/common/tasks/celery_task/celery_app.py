"""
Celery 实例配置 + Worker 信号处理
"""
import asyncio
from celery import Celery, signals

from application.common.config import config
from application.core.logger_util import logger
from application.core.database import connect_database, disconnect_database
from application.core.redis_client import redis_client

class CeleryManager:
    """封装 Celery 启动和数据库/Redis 初始化"""
    _database_initialized = False

    def __init__(self):
        self.app = Celery(
            "kajin_tool_box",
            broker=f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}",
            backend=f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}",
            include=[
              #  'common.tasks.xxx',  # 公共任务模块
            ],
        )
        self.app.autodiscover_tasks(["application.common.tasks.celery_task"])
        self._configure()
        self._register_signals()

    def _configure(self):
        self.app.conf.update(
            task_serializer=config.celery.task_serializer,
            result_serializer=config.celery.result_serializer,
            accept_content=config.celery.accept_content,
            result_expires=config.celery.result_expires,
            timezone='Asia/Shanghai',
            enable_utc=True,
            task_default_queue='default',
            task_queues={
                'default': {
                    'exchange': 'default',
                    'exchange_type': 'direct',
                    'routing_key': 'default',
                }
            },
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            task_reject_on_worker_lost=True,
        )

    def _register_signals(self):
        @signals.worker_process_init.connect
        def init_worker(**kwargs):
            """Worker 进程初始化"""
            try:
                logger.info("初始化 Worker 进程...")
                asyncio.run(self._init_database_and_redis())
                self._database_initialized = True
            except Exception as e:
                logger.error(f"Worker 初始化失败: {e}")
                self._database_initialized = False

        @signals.worker_process_shutdown.connect
        def shutdown_worker(**kwargs):
            """Worker 进程关闭"""
            try:
                logger.info("关闭 Worker 进程...")
                asyncio.run(self._shutdown_database_and_redis())
                logger.info("Worker 关闭完成")
            except Exception as e:
                logger.error(f"Worker 关闭异常: {e}")

        @signals.task_prerun.connect
        def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
            logger.debug(f"任务 {task_id} 开始: {task.name}")
            if not self._database_initialized:
                logger.warning(f"任务 {task_id}: 数据库连接未初始化")

        @signals.task_postrun.connect
        def task_postrun_handler(sender=None, task_id=None, task=None, state=None, **kwargs):
            logger.debug(f"任务 {task_id} 执行完成: {state}")

        @signals.task_failure.connect
        def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwargs):
            logger.error(f"任务 {task_id} 执行失败: {exception}")
            logger.error(f"错误信息: {einfo}")
            logger.error(f"数据库连接状态: {self._database_initialized}")

    async def _init_database_and_redis(self):
        await connect_database()
        await redis_client.connect()

    async def _shutdown_database_and_redis(self):
        await disconnect_database()
        await redis_client.close()

    def get_database_status(self):
        return self._database_initialized

    def ensure_database_connection(self):
        """确保数据库连接可用，如果不可用尝试重连"""
        if not self._database_initialized:
            logger.warning("数据库连接不可用，尝试重新初始化...")
            import tortoise
            from application.core.database import TORTOISE_ORM
            try:
                asyncio.run(tortoise.Tortoise.init(config=TORTOISE_ORM))
                self._database_initialized = True
                logger.info("数据库重新初始化成功")
            except Exception as e:
                logger.error(f"重新初始化数据库失败: {e}")
                self._database_initialized = False
        return self._database_initialized


# 模块级单例 Celery
celery_manager = CeleryManager()
celery_app = celery_manager.app
get_database_status = celery_manager.get_database_status
ensure_database_connection = celery_manager.ensure_database_connection
