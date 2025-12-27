from tortoise import Tortoise

from application.common.config import config


TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": config.database.host,
                "port": config.database.port,
                "user": config.database.user,
                "password": config.database.password,
                "database": config.database.name,
                "charset": "utf8mb4",
            }
        }
    },
    "apps": {
        "models": {
            "models": ["application.common.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",

}


async def connect_database():
    """
    初始化数据库连接
    如果已经初始化，则不会重复初始化
    """
    from .logger_util import logger
    import logging
    from tortoise import connections
    from tortoise.exceptions import ConfigurationError

    # 检查是否已初始化
    try:
        _ = connections.db_config
        # 已初始化，直接返回
        return
    except (ConfigurationError, AttributeError):
        # 未初始化，进行初始化
        pass

    tortoise_logger = logging.getLogger("tortoise")
    tortoise_logger.setLevel(logging.getLevelName(config.log.level))
    for handler in logger.handlers:
        tortoise_logger.addHandler(handler)

    await Tortoise.init(config=TORTOISE_ORM)
    # await Tortoise.generate_schemas()


async def disconnect_database():
    await Tortoise.close_connections()
