from typing import Optional, List
from pydantic import BaseModel, Field


class CreateSysConfReq(BaseModel):
    """创建系统配置请求"""
    sys_key: str = Field(description="配置 key", alias="sysKey")
    sys_value: str = Field(description="配置 value", alias="sysValue")
    description: Optional[str] = Field(default="", description="描述")


class UpdateSysConfReq(BaseModel):
    """更新系统配置请求"""
    sys_key: str = Field(description="配置 key", alias="sysKey")
    sys_value: str = Field(description="配置 value", alias="sysValue")
    description: Optional[str] = Field(default=None, description="描述")


class DeleteSysConfReq(BaseModel):
    """批量删除系统配置请求"""
    ids: List[int] = Field(description="配置 ID 列表")

