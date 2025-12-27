from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UserInfoRes(BaseModel):
    """用户信息响应"""
    id: int = Field(description="用户ID")
    username: Optional[str] = Field(default=None, description="用户名")
    nickname: Optional[str] = Field(default=None, description="昵称")
    avatar: Optional[str] = Field(default=None, description="头像URL")
    phone: Optional[str] = Field(default=None, description="手机号")
    email: Optional[str] = Field(default=None, description="邮箱")
    state: str = Field(description="状态：1=正常，0=禁用")
    is_superuser: bool = Field(description="是否为超级管理员")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值

