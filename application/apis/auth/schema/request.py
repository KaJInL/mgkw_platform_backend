from typing import Optional
from pydantic import BaseModel, Field


class QueryRoleListReq(BaseModel):
    """查询角色列表请求"""
    page: int = Field(default=1, description="页码", ge=1)
    page_size: int = Field(default=10, description="每页数量", alias="pageSize", ge=1, le=100)
    keyword: Optional[str] = Field(default=None, description="搜索关键词（角色名/描述）")
    is_system: Optional[bool] = Field(default=None, description="是否为系统角色", alias="isSystem")
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class CreateRoleReq(BaseModel):
    """创建角色请求"""
    role_name: str = Field(description="角色名", alias="roleName", min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, description="角色描述", max_length=255)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class UpdateRoleReq(BaseModel):
    """更新角色请求"""
    role_id: int = Field(description="角色ID", alias="roleId", gt=0)
    role_name: Optional[str] = Field(default=None, description="角色名", alias="roleName", min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, description="角色描述", max_length=255)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class DeleteRoleReq(BaseModel):
    """删除角色请求"""
    role_id: int = Field(description="角色ID", alias="roleId", gt=0)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class GetRoleDetailReq(BaseModel):
    """获取角色详情请求"""
    role_id: int = Field(description="角色ID", alias="roleId", gt=0)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


# ==================== 用户角色关系管理 ====================

class QueryUserRolesReq(BaseModel):
    """查询用户角色请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class BindUserRoleReq(BaseModel):
    """绑定用户角色请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)
    role_id: int = Field(description="角色ID", alias="roleId", gt=0)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class UnbindUserRoleReq(BaseModel):
    """移除用户角色请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)
    role_id: int = Field(description="角色ID", alias="roleId", gt=0)
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值

