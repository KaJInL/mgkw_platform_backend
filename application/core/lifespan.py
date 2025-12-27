from contextlib import asynccontextmanager

from fastapi import FastAPI

from application.common.config import config
from .database import disconnect_database
from .logger_util import Log
from .redis_client import redis_client
from ..common.base.base_service import CoreService

logger = Log.init_logger(config.log.level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _start(app)
    yield
    await _shutdown(app)


async def _start(app: FastAPI):
    """初始化"""
    # 初始化数据库
    from .database import connect_database
    await connect_database()

    # 初始化redis
    await redis_client.connect()

    # 初始化系统角色
    from application.service.role_service import role_service
    await role_service.init_system_roles()
    logger.info("系统角色初始化完成")

    # 初始化系统授权方案
    from application.service.design_license_plan_service import design_license_plan_service
    await design_license_plan_service.init_system_license_plans()
    logger.info("系统授权方案初始化完成")



async def _shutdown(app: FastAPI):
    """關閉"""

    # 关闭数据库连接
    await disconnect_database()

    # 关闭redis连接
    await redis_client.close()


__all__ = ["lifespan"]
