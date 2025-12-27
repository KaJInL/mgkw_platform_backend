from typing import Any, Optional
from pydantic import BaseModel, Field

from application.common.schema import LoginUserInfo


class SuperuserStatusRes(BaseModel):
    """超级用户创建状态数据模型"""
    is_superuser_created: bool = Field(description="是否已创建超级用户")


class LoginRes(BaseModel):
    """密码登录返回数据模型"""
    token: str = Field(description="token")
    user_info: LoginUserInfo = Field(description="用户信息")


class WxMiniprogramLoginByCodeRes(BaseModel):
    """微信小程序登录返回数据模型"""
    token: Optional[str] = Field(description="登录的token,如果用户没有注册则为空")
    session_key: str = Field(description="调用微信code2Session获取的sessionKey")
    openid: str = Field(description="调用微信code2Session获取的openid")
