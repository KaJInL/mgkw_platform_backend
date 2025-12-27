from typing import List, Dict, Optional
from fastapi import APIRouter, Query, HTTPException

from application.common.helper import ResponseHelper
from application.service.sys_conf_service import sys_conf_service

common = APIRouter()


@common.get(
    "/conf/value",
    summary="查询系统配置值",
    description="根据配置 key 查询配置值，直接返回字符串"
)
async def get_config_value(
        key: str = Query(..., description="配置 key", alias="key")
) -> str:
    """
    查询系统配置值
    根据配置 key 查询配置值，直接返回字符串
    """
    value = await sys_conf_service.get_value_by_key(key)
    if value is None:
        raise HTTPException(status_code=404, detail="配置不存在")
    return value


@common.get(
    "/conf/values",
    summary="批量查询系统配置值",
    description="根据配置 keys 批量查询配置值，返回 {key: string, value: string} 格式的列表"
)
async def get_config_values(
        keys: List[str] = Query(..., description="配置 key 列表", alias="keys")
) -> List[Dict[str, str]]:
    """
    批量查询系统配置值
    根据配置 keys 批量查询配置值，返回 {key: string, value: string} 格式的列表
    """
    configs = await sys_conf_service.get_configs_by_keys(keys)
    result = [{"key": conf.sys_key, "value": conf.sys_value} for conf in configs]
    return result


@common.get(
    "/conf/miniprogram",
    summary="获取小程序配置",
    description="获取小程序配置（包含 default_avatar 和 logo），使用缓存提高性能"
)
async def get_miniprogram_conf():
    """
    获取小程序配置
    返回包含 default_avatar 和 logo 的字典
    """
    result = await sys_conf_service.get_miniprogram_conf()
    return ResponseHelper.success(result)
