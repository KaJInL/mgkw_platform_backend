"""
Celery Worker 启动脚本
用于启动 Celery Worker 进程处理异步任务
"""
from application.common.tasks.celery_task.celery_app import celery_app

if __name__ == "__main__":
    # 启动 Celery Worker
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=4",  # Worker 并发数，可根据服务器配置调整
        "--pool=prefork",  # 使用 prefork 池（支持异步任务）
        "--queues=default",  # 监听的任务队列
    ])

