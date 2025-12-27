from pydantic import BaseModel, Field, field_validator, EmailStr

from application.common.utils.ValidationUtils import ValidationUtils

class WxGetPhoneNumberReq(BaseModel):
    """获取微信小程序手机号的请求"""
    encrypted_data: str = Field(description="微信小程序获取手机号接口返回的 encryptedData",alias="encryptedData")
    iv:str = Field(description="微信小程序获取手机号接口返回的 iv",alias="iv")
    session_key: str = Field(description="微信小程序获取手机号接口返回的 session_key",alias="sessionKey")
    openid : str = Field(description="微信小程序获取手机号接口返回的 openid")


class WxCode2SessionReq(BaseModel):
    """微信小程序获取 session 的请求"""
    code: str = Field(description="微信小程序 code")

class CreateSuperUserReq(BaseModel):
    """创建超级管理员请求"""
    
    phone_number: str = Field(description="用户手机号", alias="phoneNumber", min_length=11, max_length=11)
    password: str = Field(description="密码", min_length=6, max_length=32)
    email: EmailStr = Field(description="邮箱")

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """
        校验手机号格式
        支持中国大陆手机号：1开头的11位数字
        """
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

class LoginByPwdReq(BaseModel):
    """管理员登录请求"""
    phone_number: str = Field(description="用户手机号", alias="phoneNumber", min_length=11, max_length=11)
    password: str = Field(description="密码", min_length=6, max_length=32)

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """
        校验手机号格式
        支持中国大陆手机号：1开头的11位数字
        """
        return ValidationUtils.validate_phone(v)


class InvalidateTokenReq(BaseModel):
    """失效指定 token 的请求"""
    token: str = Field(description="要失效的 token")


class InvalidateUserTokensReq(BaseModel):
    """失效用户所有 token 的请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)


class GetUserOnlineDevicesReq(BaseModel):
    """获取用户在线设备请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)


class KickDeviceReq(BaseModel):
    """踢出指定设备的请求"""
    user_id: int = Field(description="用户ID", alias="userId", gt=0)
    token: str = Field(description="要踢出的设备 token")

