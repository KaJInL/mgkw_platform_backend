import base64
import json
from typing import Dict, Optional

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pydantic.v1 import BaseModel

from application import config
from application.core.lifespan import logger
from application.core.redis_client import redis_client

REDIS_KEY_WX_ACCESS_TOKEN = "wx_access_token"


async def get_access_token() -> str:
    # 先从 Redis 中取
    token = await redis_client.get(REDIS_KEY_WX_ACCESS_TOKEN)
    if token:
        return token

    # 向微信请求 access_token
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "appid": config.wxMiniProgram.appId,
        "secret": config.wxMiniProgram.appSecret,
        "grant_type": "client_credential"
    }
    response = requests.get(url, params=params)
    result = response.json()

    access_token = result.get("access_token")
    if access_token:
        await redis_client.set(REDIS_KEY_WX_ACCESS_TOKEN, access_token, 7000)
    return access_token


async def login_by_js_code(code: str) -> Optional[Dict]:
    """
    使用 js_code 登录，返回 openid 和 session_key 等信息
    """
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": config.miniprogram.wechat_app_id,
        "secret": config.miniprogram.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code"
    }
    response = requests.get(url, params=params)
    return response.json()


async def decrypt_data(encrypted_data: str, session_key: str, iv: str) -> dict[str,str]:
    """
    解密微信用户数据，如手机号信息
    """
    data = base64.b64decode(encrypted_data)
    key = base64.b64decode(session_key)
    iv_bytes = base64.b64decode(iv)

    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
    decrypted = cipher.decrypt(data)
    try:
        decrypted = unpad(decrypted, AES.block_size)
    except ValueError:
        raise ValueError("解密失败：数据可能被篡改或 key/iv 错误")
    data =  decrypted.decode('utf-8')
    logger.info(f"解密微信用户数据成功：{data}")
    return json.loads(data)


__all__ = [
    "get_access_token",
    "login_by_js_code",
    "decrypt_data"
]
