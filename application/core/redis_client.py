import asyncio
import json
from decimal import Decimal
from contextlib import AbstractAsyncContextManager
from enum import Enum
from types import TracebackType
from typing import Optional, Type, Any

import aioredlock
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

from application.common.config import config
from application.core.logger_util import logger

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        # 处理 datetime 对象
        if hasattr(obj, 'isoformat'):
            # 支持 datetime 和 date 对象
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

class RedisLock(AbstractAsyncContextManager):
    """
    Redis 分布式锁上下文管理器
    使用 aioredlock 实现，支持 async with 语法
    """

    def __init__(
        self,
        lock_manager: aioredlock.Aioredlock,
        key: str,
        expire: int = 10,
        blocking: bool = True,
        timeout: Optional[float] = None
    ):
        self.lock_manager = lock_manager
        self.key = key
        self.expire = expire * 1000  # aioredlock 使用毫秒
        self.blocking = blocking
        self.timeout = timeout
        self.lock: Optional[aioredlock.Lock] = None

    async def __aenter__(self) -> aioredlock.Lock:
        try:
            if self.blocking:
                retry_count = int(self.timeout * 10) if self.timeout else 100
                retry_delay = 0.1
                for i in range(retry_count):
                    try:
                        self.lock = await self.lock_manager.lock(self.key, self.expire)
                        logger.debug(f"🔐 成功获取锁: {self.key}")
                        return self.lock
                    except aioredlock.LockError:
                        if i < retry_count - 1:
                            await asyncio.sleep(retry_delay)
                        else:
                            raise
                raise aioredlock.LockError(f"获取锁超时: {self.key}")
            else:
                self.lock = await self.lock_manager.lock(self.key, self.expire)
                logger.debug(f"🔐 成功获取锁: {self.key}")
                return self.lock
        except aioredlock.LockError as e:
            logger.warning(f"❌ 获取锁失败: {self.key}, 错误: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ 获取锁时发生异常: {self.key}, 错误: {e}")
            raise

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        if self.lock:
            try:
                await self.lock_manager.unlock(self.lock)
                logger.debug(f"🔓 成功释放锁: {self.key}")
            except Exception as e:
                logger.error(f"❌ 释放锁失败: {self.key}, 错误: {e}")


class TimeUnit(str, Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"

    def to_seconds(self, value: int) -> int:
        multiplier_map = {
            TimeUnit.SECONDS: 1,
            TimeUnit.MINUTES: 60,
            TimeUnit.HOURS: 3600,
            TimeUnit.DAYS: 86400,
        }
        return value * multiplier_map[self]


class _AsyncRedisClient:
    """
    异步 Redis 客户端封装
    包含常用操作和分布式锁功能
    """

    def __init__(self):
        self.pool = redis.ConnectionPool(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            decode_responses=True,
            encoding="utf-8",
            max_connections=config.redis.max_connections,
        )
        self.client: Optional[redis.Redis] = None

        # 初始化分布式锁管理器
        redis_url = (
            f"redis://:{config.redis.password}@{config.redis.host}:{config.redis.port}/{config.redis.db}"
            if config.redis.password
            else f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
        )
        self.lock_manager = aioredlock.Aioredlock([redis_url])

    async def connect(self) -> Optional[redis.Redis]:
        try:
            self.client = redis.Redis(connection_pool=self.pool)
            pong = await self.client.ping()
            logger.info("✅ Redis 连接成功")
            return self.client
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Redis 连接失败: {e}")
            return None

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("🔒 Redis 连接已关闭")
        await self.lock_manager.destroy()

    async def set(self, key: str, value: dict | set | list, time: Optional[int] = None,
                  unit: TimeUnit = TimeUnit.SECONDS):
        ex = unit.to_seconds(time) if time is not None else None
        if isinstance(value, (dict, list, set)):
            if isinstance(value, set):
                value = list(value)
            value = json.dumps(value, cls=DecimalEncoder)
        return await self.client.set(key, value, ex=ex)

    async def get(self, key: str):
        data = await self.client.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except Exception:
            return data

    async def mget(self, keys: list[str]) -> list[Optional[str]]:
        """
        批量获取多个 key 的值
        :param keys: key 列表
        :return: 值列表，如果 key 不存在则对应位置为 None
        """
        if not keys:
            return []
        values = await self.client.mget(keys)
        result = []
        for value in values:
            if value is None:
                result.append(None)
            else:
                try:
                    # 尝试解析 JSON，如果失败则返回原始字符串
                    result.append(json.loads(value))
                except Exception:
                    result.append(value)
        return result

    async def delete(self, key: str):
        return await self.client.delete(key)

    async def incr(self, key: str, amount: int = 1):
        return await self.client.incr(key, amount)

    async def expire(self, key: str, time: int):
        return await self.client.expire(key, time)

    async def ttl(self, key: str) -> int:
        """
        获取 key 的剩余过期时间（秒）
        :param key: 键名
        :return: 剩余秒数，-1 表示永不过期，-2 表示 key 不存在
        """
        return await self.client.ttl(key)

    async def exists(self, key: str):
        return await self.client.exists(key)

    async def sadd(self, key: str, *values):
        return await self.client.sadd(key, *values)

    async def srem(self, key: str, *values):
        return await self.client.srem(key, *values)

    async def smembers(self, key: str):
        return await self.client.smembers(key)

    async def sismember(self, key: str, value):
        """检查值是否是集合的成员"""
        return await self.client.sismember(key, value)

    async def scard(self, key: str):
        """获取集合的元素数量"""
        return await self.client.scard(key)

    async def spop(self, key: str, count: int = None):
        """从集合中随机移除并返回一个或多个元素"""
        return await self.client.spop(key, count)

    async def keys(self, pattern: str = "*", count: int = 100):
        keys = []
        cursor = 0
        while True:
            cursor, partial_keys = await self.client.scan(cursor=cursor, match=pattern, count=count)
            keys.extend(partial_keys)
            if cursor == 0:
                break
        return keys

    # ✅ 改进版：返回 RedisLock 对象，而不是 coroutine
    def lock(
        self,
        key: str,
        expire: int = 10,
        auto_renewal: bool = False,
        blocking: bool = True,
        timeout: Optional[float] = None
    ) -> RedisLock:
        """
        获取分布式锁（直接可用于 async with）
        """
        return RedisLock(
            lock_manager=self.lock_manager,
            key=key,
            expire=expire,
            blocking=blocking,
            timeout=timeout
        )


# ✅ 单例实例
redis_client = _AsyncRedisClient()
