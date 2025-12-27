import asyncio
from functools import wraps

def run_async(func):
    """
    Celery Worker 异步运行装饰器
    自动确保数据库连接已初始化（仅在必要时）
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 尝试获取正在运行的事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
            return future.result()

        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 确保数据库连接已初始化
            # connect_database() 内部有检查机制，如果已初始化会直接返回，不会重复连接
            async def ensure_db_and_run():
                from application.core.database import connect_database
                await connect_database()
                return await func(*args, **kwargs)
            
            return loop.run_until_complete(ensure_db_and_run())
        finally:
            asyncio.set_event_loop(None)

    return wrapper