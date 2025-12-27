from enum import Enum, StrEnum

from application.common.base import DefaultModel

from tortoise import fields
from tortoise.models import Model


class User(DefaultModel):
    """
    用户主表
    用于小程序用户、设计师、管理员等
    """
    username = fields.CharField(max_length=64, null=True, description="用户名")
    password_hash = fields.CharField(max_length=128, null=True, description="密码哈希（包含盐值）")  # 减少长度
    password_salt = fields.CharField(max_length=64, null=True, description="密码盐值")
    nickname = fields.CharField(max_length=55, null=True, description="昵称")
    avatar = fields.TextField(null=True, description="头像URL")
    phone = fields.CharField(max_length=20, null=True, description="手机号")
    email = fields.CharField(max_length=64, null=True, description="邮箱")
    state = fields.CharField(max_length=1, default='1', description="状态：1=启用，0=禁用")
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员")

    class Meta:
        table = "user"
        table_description = "用户主表"


class AuthTypeEnum(StrEnum):
    DOUYIN_MP = "douyin_mp"
    ALIPAY_MP = "alipay_mp"
    WECHAT_MINI_PROGRAM = "wechat_mini_program"


class UserAuth(DefaultModel):
    """
    第三方授权表
    存储小程序、抖音、支付宝等平台的 openid / unionid
    不使用外键，只保存 user_id
    """
    id = fields.BigIntField(pk=True)
    user_id = fields.BigIntField(description="关联的用户ID")
    auth_type = fields.CharEnumField(AuthTypeEnum, max_length=32, description="授权类型")
    openid = fields.CharField(max_length=100, null=True, description="平台唯一ID（如 openid 或 user_id）")
    unionid = fields.CharField(max_length=100, null=True, description="跨应用统一ID（可为空）")

    class Meta:
        table = "user_auth"
        table_description = "第三方授权表"
        unique_together = (("auth_type", "openid"),)


class Role(DefaultModel):
    """
    角色表，用于定义系统中的角色，如管理员、设计师、普通用户等
    """
    role_name = fields.CharField(max_length=64, unique=True, description="角色名，如 admin、designer、account")
    description = fields.TextField(null=True, description="角色描述")
    is_system = fields.BooleanField(default=False, description="是否为系统角色,系统角色无法删除")

    class Meta:
        table = "role"
        table_description = "角色表"


class UserRole(DefaultModel):
    """
    用户角色关联表，表示用户与角色的多对多关系
    """
    user_id = fields.BigIntField(description="关联的用户ID")
    role_id = fields.BigIntField(description="关联的角色ID")

    class Meta:
        table = "user_role"
        table_description = "用户角色关联表"
        unique_together = (("user_id", "role_id"),)
