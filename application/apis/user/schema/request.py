from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, EmailStr

from application.common.utils.ValidationUtils import ValidationUtils


class QueryUserListReq(BaseModel):
    """查询用户列表请求"""
    page: int = Field(default=1, description="页码", ge=1)
    page_size: int = Field(default=10, description="每页数量", alias="pageSize", ge=1, le=100)
    keyword: Optional[str] = Field(default=None, description="搜索关键词（手机号/邮箱/昵称）")
    state: Optional[str] = Field(default=None, description="用户状态：1=正常，0=禁用")

    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class CreateUserReq(BaseModel):
    """新增用户请求"""
    phone_number: Optional[str] = Field(default=None, description="用户手机号", alias="phoneNumber", min_length=11,
                                        max_length=11)
    password: str = Field(description="密码", min_length=6, max_length=32)
    email: Optional[EmailStr] = Field(default=None, description="邮箱")
    nickname: Optional[str] = Field(default=None, description="昵称", max_length=55)
    username: Optional[str] = Field(default=None, description="用户名", max_length=64)

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """
        校验手机号格式
        支持中国大陆手机号：1开头的11位数字
        """
        if v is None:
            return v
        return ValidationUtils.validate_phone(v)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        校验密码强度
        要求：6-32位，必须包含字母和数字
        """
        return ValidationUtils.validate_password_strength(
            v,
            min_length=6,
            max_length=32,
            require_letter=True,
            require_digit=True,
            require_special=False
        )

    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class UpdateUserReq(BaseModel):
    """修改用户信息请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)
    phone_number: Optional[str] = Field(default=None, description="用户手机号", alias="phoneNumber", min_length=11,
                                        max_length=11)
    email: Optional[EmailStr] = Field(default=None, description="邮箱")
    nickname: Optional[str] = Field(default=None, description="昵称", max_length=55)
    username: Optional[str] = Field(default=None, description="用户名", max_length=64)
    avatar: Optional[str] = Field(default=None, description="头像URL")

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """
        校验手机号格式
        支持中国大陆手机号：1开头的11位数字
        """
        if v is None:
            return v
        return ValidationUtils.validate_phone(v)

    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class DisableUserReq(BaseModel):
    """禁用/启用用户请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)
    state: str = Field(description="用户状态：1=正常，0=禁用", pattern="^[01]$")

    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class GetUserDetailReq(BaseModel):
    """获取用户详情请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)

    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值


class UpdateCurrentUserReq(BaseModel):
    """当前用户修改个人信息请求（只能修改头像、昵称、用户名和邮箱）"""
    username: Optional[str] = Field(default=None, description="用户名", max_length=64)
    avatar: Optional[str] = Field(default=None, description="头像URL")
    nickname: Optional[str] = Field(default=None, description="昵称", max_length=55)
    email: Optional[EmailStr] = Field(default=None, description="邮箱")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """
        校验用户名格式
        用户名只能包含字母、数字和下划线，长度1-64位
        """
        if v is None:
            return v
        return ValidationUtils.validate_username(v)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """
        校验邮箱格式
        """
        if v is None:
            return v
        return ValidationUtils.validate_email(v)

    class Config:
        populate_by_name = True  # 允许使用字段名或别名进行赋值
