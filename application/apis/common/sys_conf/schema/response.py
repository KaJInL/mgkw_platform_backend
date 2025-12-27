from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SysConfResponse(BaseModel):
    """系统配置响应"""
    id: int = Field(description="主键 ID")
    sys_key: str = Field(description="配置 key", alias="sysKey")
    sys_value: str = Field(description="配置 value", alias="sysValue")
    description: Optional[str] = Field(default="", description="描述")
    created_at: datetime = Field(description="创建时间", alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class SysConfValueResponse(BaseModel):
    """系统配置值响应"""
    sys_value: str = Field(description="配置值", alias="sysValue")

    class Config:
        populate_by_name = True


class SysConfOperationResponse(BaseModel):
    """系统配置操作响应"""
    success: bool = Field(description="是否成功")
    message: Optional[str] = Field(default="操作成功", description="提示信息")


class BatchSetSysConfResponse(BaseModel):
    """批量设置系统配置响应"""
    count: int = Field(description="成功设置的配置数量")

