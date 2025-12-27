"""
登录相关的 Schema 定义
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from application.common.models import User, Role, UserVIP, UserAuth


class RoleInfo(BaseModel):
    """角色信息"""
    id: int = Field(description="角色ID")
    role_name: str = Field(description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    is_system: bool = Field(default=False, description="是否为系统角色")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "role_name": "super_admin",
                "description": "超级管理员",
                "is_system": True
            }
        }
    )

    @classmethod
    def from_orm_object(cls, role: Role) -> "RoleInfo":
        """
        从 Tortoise ORM Role 对象创建 RoleInfo
        
        Args:
            role: Tortoise ORM Role 对象
            
        Returns:
            RoleInfo 实例
            
        示例:
            role_info = RoleInfo.from_orm_object(orm_role)
        """
        return cls(
            id=role.id,
            role_name=role.role_name,
            description=role.description,
            is_system=role.is_system
        )


class VIPInfo(BaseModel):
    """VIP会员信息"""
    total_days: int = Field(description="累计会员天数")
    start_time: datetime = Field(description="会员开始时间")
    end_time: datetime = Field(description="会员结束时间")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_days": 365,
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-12-31T23:59:59"
            }
        }
    )

    @classmethod
    def from_orm_object(cls, user_vip: UserVIP) -> "VIPInfo":
        """
        从 Tortoise ORM UserVIP 对象创建 VIPInfo
        
        Args:
            user_vip: Tortoise ORM UserVIP 对象
            
        Returns:
            VIPInfo 实例
            
        示例:
            vip_info = VIPInfo.from_orm_object(orm_user_vip)
        """
        return cls(
            total_days=user_vip.total_days,
            start_time=user_vip.start_time,
            end_time=user_vip.end_time
        )


class UserAuthInfo(BaseModel):
    """用户授权信息"""
    id: int = Field(description="授权记录ID")
    user_id: int = Field(description="用户ID", alias="userId")
    auth_type: str = Field(description="授权类型", alias="authType")
    openid: Optional[str] = Field(default=None, description="平台唯一ID（如 openid）")
    unionid: Optional[str] = Field(default=None, description="跨应用统一ID（可为空）")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "userId": 123,
                "authType": "wechat_mini_program",
                "openid": "o69pE19EkoQqPFkfkkqCglbUYag4",
                "unionid": None
            }
        },
        populate_by_name=True
    )

    @classmethod
    def from_orm_object(cls, user_auth: UserAuth) -> "UserAuthInfo":
        """
        从 Tortoise ORM UserAuth 对象创建 UserAuthInfo
        
        Args:
            user_auth: Tortoise ORM UserAuth 对象
            
        Returns:
            UserAuthInfo 实例
            
        示例:
            user_auth_info = UserAuthInfo.from_orm_object(orm_user_auth)
        """
        # 处理 auth_type：如果是枚举类型，获取其值；否则直接转换为字符串
        auth_type_value = user_auth.auth_type
        if isinstance(auth_type_value, str):
            pass  # 已经是字符串
        elif hasattr(auth_type_value, 'value'):
            auth_type_value = auth_type_value.value
        else:
            auth_type_value = str(auth_type_value)
        
        return cls(
            id=user_auth.id,
            user_id=user_auth.user_id,
            auth_type=auth_type_value,
            openid=user_auth.openid,
            unionid=user_auth.unionid
        )


class UserInfo(BaseModel):
    """
    用户基本信息（纯数据对象，不包含敏感信息）
    
    说明：
    - 这是一个 DTO（数据传输对象），从 User ORM 对象转换而来
    - 不包含密码等敏感信息
    - 可以安全地序列化到 Redis 或返回给前端
    """
    id: int = Field(description="用户ID")
    username: Optional[str] = Field(default=None, description="用户名")
    nickname: Optional[str] = Field(default=None, description="昵称")
    avatar: Optional[str] = Field(default=None, description="头像URL")
    phone: Optional[str] = Field(default=None, description="手机号")
    email: Optional[str] = Field(default=None, description="邮箱")
    state: str = Field(description="状态：1=正常，0=禁用")
    is_superuser: bool = Field(default=False, description="是否为超级管理员")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "admin",
                "nickname": "管理员",
                "avatar": "https://example.com/avatar.jpg",
                "phone": "13800138000",
                "email": "admin@example.com",
                "state": "1",
                "is_superuser": True
            }
        }
    )

    @classmethod
    def from_orm_object(cls, user: User) -> "UserInfo":
        """
        从 Tortoise ORM User 对象创建 UserInfo
        
        Args:
            user: Tortoise ORM User 对象
            
        Returns:
            UserInfo 实例
            
        示例:
            user_info = UserInfo.from_orm_object(orm_user)
        """
        return cls(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            phone=user.phone,
            email=user.email,
            state=user.state,
            is_superuser=user.is_superuser
        )


class LoginUserInfo(BaseModel):
    """
    登录用户完整信息（用户信息 + 角色信息 + VIP信息 + 授权信息）
    
    结构说明：
    {
        "user": {  # 用户基本信息
            "id": 1,
            "username": "admin",
            ...
        },
        "roles": [  # 用户角色列表
            {
                "id": 1,
                "role_name": "super_admin",
                ...
            }
        ],
        "vip": {  # VIP会员信息（可选）
            "total_days": 365,
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-12-31T23:59:59"
        },
        "userAuths": [  # 用户授权信息列表
            {
                "id": 1,
                "userId": 123,
                "authType": "wechat_mini_program",
                "openid": "o69pE19EkoQqPFkfkkqCglbUYag4",
                "unionid": null
            }
        ]
    }
    
    优点：
    1. 结构清晰，user、roles、vip 和 userAuths 分离
    2. UserInfo 可以在其他地方复用
    3. 符合单一职责原则
    4. 授权信息缓存后，无需重复查询数据库
    """
    user: UserInfo = Field(description="用户基本信息")
    roles: List[RoleInfo] = Field(default_factory=list, description="用户角色列表")
    vip: Optional[VIPInfo] = Field(default=None, description="VIP会员信息")
    auths: List[UserAuthInfo] = Field(default_factory=list, description="用户授权信息列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": 1,
                    "username": "admin",
                    "nickname": "管理员",
                    "avatar": "https://example.com/avatar.jpg",
                    "phone": "13800138000",
                    "email": "admin@example.com",
                    "state": "1",
                    "is_superuser": True
                },
                "roles": [
                    {
                        "id": 1,
                        "role_name": "super_admin",
                        "description": "超级管理员",
                        "is_system": True
                    }
                ],
                "vip": {
                    "total_days": 365,
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-12-31T23:59:59"
                },
                "userAuths": [
                    {
                        "id": 1,
                        "userId": 123,
                        "authType": "wechat_mini_program",
                        "openid": "o69pE19EkoQqPFkfkkqCglbUYag4",
                        "unionid": None
                    }
                ]
            }
        },
        populate_by_name=True
    )

    @classmethod
    def from_orm_objects(
        cls, 
        user: User, 
        roles: List[Role], 
        user_vip: Optional[UserVIP] = None,
        user_auths: Optional[List[UserAuth]] = None
    ) -> "LoginUserInfo":
        """
        从 Tortoise ORM 对象创建 LoginUserInfo
        
        Args:
            user: Tortoise ORM User 对象
            roles: Tortoise ORM Role 对象列表
            user_vip: Tortoise ORM UserVIP 对象（可选）
            user_auths: Tortoise ORM UserAuth 对象列表（可选）
            
        Returns:
            LoginUserInfo 实例
            
        示例:
            login_info = LoginUserInfo.from_orm_objects(orm_user, orm_roles, orm_user_vip, orm_user_auths)
        """
        return cls(
            user=UserInfo.from_orm_object(user),
            roles=[RoleInfo.from_orm_object(role) for role in roles],
            vip=VIPInfo.from_orm_object(user_vip) if user_vip else None,
            auths=[UserAuthInfo.from_orm_object(auth) for auth in (user_auths or [])]
        )

