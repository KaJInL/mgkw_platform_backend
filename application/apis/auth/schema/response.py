from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RoleInfoRes(BaseModel):
    """角色信息响应"""
    id: int = Field(description="角色ID")
    role_name: str = Field(description="角色名", alias="roleName")
    description: Optional[str] = Field(default=None, description="角色描述")
    is_system: bool = Field(description="是否为系统角色", alias="isSystem")
    created_at: datetime = Field(description="创建时间", alias="createdAt")
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class UserRolesRes(BaseModel):
    """用户角色列表响应"""
    user_id: int = Field(description="用户ID", alias="userId")
    roles: List[RoleInfoRes] = Field(description="角色列表")
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值

