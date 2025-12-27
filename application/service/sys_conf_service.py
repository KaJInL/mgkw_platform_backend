from enum import Enum
from typing import Optional, Dict, Any, List

from application.common.base import BaseService
from application.common.constants import BoolEnum
from application.common.models import SysConf
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class SysConfKeyEnum(str, Enum):
    """
    系统配置 Key 枚举
    用于统一管理系统配置的 key 值
    """
    DEFAULT_AVATAR = "default_avatar"
    IS_SUPERUSER_CREATED = "is_superuser_created"
    LOGO = "logo"


class SysConfService(BaseService[SysConf]):
    """
    系统配置 Service
    提供系统配置的增删改查及缓存管理功能
    """
    REDIS_KEY_PREFIX = "sys_conf:"
    MINIPROGRAM_CONF_CACHE_KEY = "sys_conf:miniprogram_conf"
    CACHE_EXPIRE_TIME = 1  # 缓存过期时间：1小时
    CACHE_TIME_UNIT = TimeUnit.HOURS

    async def get_by_key(self, sys_key: str) -> Optional[SysConf]:
        """
        根据配置 key 获取配置信息
        :param sys_key: 配置 key
        :return: 系统配置对象
        """
        # 先从缓存获取
        cache_key = f"{self.REDIS_KEY_PREFIX}{sys_key}"
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"从缓存获取系统配置: {sys_key}")
            return await SysConf.get_or_none(sys_key=sys_key)

        # 从数据库获取
        conf = await self.get_one(sys_key=sys_key)
        if not conf:
            return None

        await self._set_cache(sys_key, conf.sys_value)

        return conf

    async def get_value_by_key(self, sys_key: str) -> Optional[str]:
        """
        根据配置 key 获取配置值
        :param sys_key: 配置 key
        :param default: 默认值，当配置不存在时返回
        :return: 配置值或默认值
        """
        conf = await self.get_by_key(sys_key)
        return conf.sys_value if conf else None

    async def set_config(self, sys_key: str, sys_value: str, description: str = "") -> SysConf:
        """
        设置或更新配置
        :param description:系统配置描述
        :param sys_key: 配置 key
        :param sys_value: 配置 value
        :return: 系统配置对象
        """
        conf, created = await self.save_or_update(
            defaults={"sys_value": sys_value},
            sys_key=sys_key,
            description=description
        )
        
        # 更新配置后删除缓存
        await self._delete_cache(sys_key)

        return conf

    async def batch_set_configs(self, configs: list[SysConf]) -> int:
        """
        批量设置或更新配置
        :param configs: 配置字典 {key: value, ...}
        :return: 成功设置的配置数量
        """
        count = 0
        for config in configs:
            await self.set_config(config.sys_key, config.sys_value)
        count += 1

        return count

    async def delete_config(self, sys_key: str) -> bool:
        """
        删除配置
        :param sys_key: 配置 key
        :return: 是否删除成功
        """
        deleted_count = await self.delete(sys_key=sys_key)

        if deleted_count > 0:
            # 删除缓存
            await self._delete_cache(sys_key)
            logger.info(f"删除系统配置: {sys_key}")
            return True

        return False

    async def get_all_configs(self) -> Dict[str, str]:
        """
        获取所有配置
        :return: 配置字典 {key: value, ...}
        """
        configs = await self.model_class.all()
        return {conf.sys_key: conf.sys_value for conf in configs}

    async def get_configs_by_keys(self, keys: List[str]) -> List[SysConf]:
        """
        批量获取多个配置值（优化版：使用 Redis mget 批量查询）
        :param keys: 配置 key 列表
        :return: 配置对象列表
        """
        if not keys:
            return []
        
        # 构建 Redis key 列表
        cache_keys = [f"{self.REDIS_KEY_PREFIX}{key}" for key in keys]
        
        # 批量从 Redis 获取
        cached_values = await redis_client.mget(cache_keys)
        
        # 构建结果字典：key -> SysConf 对象或 value 字符串
        result_map: Dict[str, Any] = {}
        missing_keys: List[str] = []
        
        for i, key in enumerate(keys):
            cached_value = cached_values[i]
            if cached_value is not None:
                # Redis 中有缓存，存储 value（稍后创建临时对象）
                result_map[key] = cached_value
            else:
                # Redis 中没有，需要从数据库查询
                missing_keys.append(key)
        
        # 批量从数据库查询缺失的配置
        if missing_keys:
            missing_configs = await self.model_class.filter(sys_key__in=missing_keys).all()
            
            # 将查询到的配置写入 Redis 并加入结果
            for conf in missing_configs:
                # 直接使用完整的 SysConf 对象
                result_map[conf.sys_key] = conf
                # 异步写入缓存（不等待完成以提高性能）
                await self._set_cache(conf.sys_key, conf.sys_value)
        
        # 构建返回结果：按照原始 keys 的顺序返回 SysConf 对象
        result: List[SysConf] = []
        for key in keys:
            if key in result_map:
                value = result_map[key]
                if isinstance(value, SysConf):
                    # 从数据库查询到的完整对象，直接使用
                    result.append(value)
                else:
                    # 从 Redis 获取的值，创建临时对象
                    conf = SysConf(sys_key=key, sys_value=value)
                    result.append(conf)
        
        return result

    # ========== 私有方法 ==========

    async def _set_cache(self, sys_key: str, sys_value: str) -> None:
        """
        设置缓存
        :param sys_key: 配置 key
        :param sys_value: 配置 value
        """
        cache_key = f"{self.REDIS_KEY_PREFIX}{sys_key}"
        await redis_client.set(
            cache_key,
            sys_value,
            time=self.CACHE_EXPIRE_TIME,
            unit=self.CACHE_TIME_UNIT
        )

    async def _delete_cache(self, sys_key: str) -> bool:
        """
        删除缓存
        :param sys_key: 配置 key
        :return: 是否删除成功
        """
        cache_key = f"{self.REDIS_KEY_PREFIX}{sys_key}"
        deleted = await redis_client.delete(cache_key)
        
        # 如果删除的是 DEFAULT_AVATAR 或 LOGO，同时删除 miniprogram_conf 的缓存
        if sys_key in [SysConfKeyEnum.DEFAULT_AVATAR, SysConfKeyEnum.LOGO]:
            await redis_client.delete(self.MINIPROGRAM_CONF_CACHE_KEY)
            logger.debug(f"删除 miniprogram_conf 缓存，因为 {sys_key} 已更新")
        
        return deleted > 0

    async def set_default_avatar(self, avatar_url: str) -> None:
        """
        设置默认头像
        :param avatar_url: 头像 URL
        """
        await self.set_config("default_avatar", avatar_url)

    async def get_default_avatar(self) -> Optional[str]:
        """
        获取默认头像
        :return: 头像 URL
        """
        return await self.get_value_by_key("default_avatar")

    async def mark_super_user_created(self):
        """
        标记超级管理员创建状态为已创建
        :return:
        """
        await self.set_config("is_superuser_created", BoolEnum.YES)

    async def get_super_user_create_state(self) -> Optional[str]:
        """
        获取超级管理员创建状态
        :return:
        """
        return await self.get_value_by_key("is_superuser_created")

    async def get_miniprogram_conf(self) -> Dict[str, Optional[str]]:
        """
        获取小程序配置（DEFAULT_AVATAR 和 LOGO）
        使用缓存提高性能
        :return: 包含 default_avatar 和 logo 的字典
        """
        # 先从缓存获取
        cached_data = await redis_client.get(self.MINIPROGRAM_CONF_CACHE_KEY)
        if cached_data:
            logger.debug("从缓存获取 miniprogram_conf")
            return cached_data
        
        # 从数据库批量查询
        keys = [SysConfKeyEnum.DEFAULT_AVATAR, SysConfKeyEnum.LOGO]
        configs = await self.get_configs_by_keys(keys)
        
        # 构建结果字典
        result = {
            SysConfKeyEnum.DEFAULT_AVATAR: None,
            SysConfKeyEnum.LOGO: None
        }
        
        for conf in configs:
            if conf.sys_key in result:
                result[conf.sys_key] = conf.sys_value
        
        # 写入缓存
        await redis_client.set(
            self.MINIPROGRAM_CONF_CACHE_KEY,
            result,
            time=self.CACHE_EXPIRE_TIME,
            unit=self.CACHE_TIME_UNIT
        )
        
        return result


# 创建全局实例
sys_conf_service = SysConfService()
