"""
Token 服务层，负责 token 的生成、验证、存储和管理
"""
import time
import json
import base64
import hmac
import hashlib
from typing import Optional, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from application.common.config import config
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.core.logger_util import logger
from application.core.redis_client import redis_client


class TokenService:
    """Token 服务类，管理 token 的完整生命周期"""
    
    # 密钥，从配置文件读取
    SECRET_KEY = config.secret_key
    
    # 用户 token 集合前缀（白名单方案：存储用户所有有效的 token）
    USER_TOKENS_PREFIX = "tokens:"
    
    @property
    def default_expire_days(self) -> int:
        """
        获取默认token过期时间（天）
        从配置文件中读取
        """
        return config.auth.token_expire_days
    
    @property
    def max_tokens_per_user(self) -> int:
        """
        获取单个用户最大登录设备数量
        从配置文件中读取，0表示不限制
        """
        return config.auth.max_tokens_per_user
    
    @staticmethod
    def _get_fernet_key() -> Fernet:
        """
        从 SECRET_KEY 生成 Fernet 加密密钥
        Fernet 需要 32 字节的 URL-safe base64 编码密钥
        使用 SHA256 哈希 SECRET_KEY 并转换为 Fernet 格式
        """
        # 使用 SHA256 哈希 SECRET_KEY 得到 32 字节
        key_bytes = hashlib.sha256(TokenService.SECRET_KEY.encode('utf-8')).digest()
        # 转换为 URL-safe base64 编码（Fernet 要求的格式）
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)
    
    @staticmethod
    def _encrypt_data(data: str) -> str:
        """
        加密数据
        :param data: 待加密的字符串
        :return: 加密后的 base64 编码字符串
        """
        fernet = TokenService._get_fernet_key()
        encrypted_bytes = fernet.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    
    @staticmethod
    def _decrypt_data(encrypted_data: str) -> str:
        """
        解密数据
        :param encrypted_data: 加密后的 base64 编码字符串
        :return: 解密后的原始字符串
        :raises ValueError: 解密失败时抛出
        """
        try:
            fernet = TokenService._get_fernet_key()
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception:
            raise ValueError("Invalid encrypted data format")
    
    @staticmethod
    def _generate_signature(payload: str) -> str:
        """
        生成签名
        :param payload: 待签名的数据
        :return: 签名字符串
        """
        return hmac.new(
            TokenService.SECRET_KEY.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def _base64_encode(data: str) -> str:
        """Base64 编码（URL安全）"""
        return base64.urlsafe_b64encode(data.encode('utf-8')).decode('utf-8')
    
    @staticmethod
    def _base64_decode(data: str) -> str:
        """Base64 解码"""
        try:
            return base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8')
        except Exception:
            raise ValueError("Invalid token format")
    
    def generate_token(self, user_id: int, expire_days: int = None) -> str:
        """
        生成 token
        :param user_id: 用户ID
        :param expire_days: 过期天数，如果不传则使用配置文件中的默认值
        :return: token 字符串
        """
        if expire_days is None:
            expire_days = self.default_expire_days
        
        # 计算过期时间戳（毫秒）
        expire_time = int((datetime.now() + timedelta(days=expire_days)).timestamp() * 1000)
        
        # 构造 payload
        payload_data = {
            "user_id": user_id,
            "expire_time": expire_time,
            "timestamp": int(time.time() * 1000)  # 生成时间戳
        }
        
        # 转换为 JSON 字符串
        payload_json = json.dumps(payload_data, separators=(',', ':'))
        
        # 先加密 payload，再 Base64 编码
        payload_encrypted = self._encrypt_data(payload_json)
        
        # 生成签名（对加密后的数据进行签名）
        signature = self._generate_signature(payload_encrypted)
        
        # 组合 token: encrypted_payload.signature
        token = f"{payload_encrypted}.{signature}"
        
        return token
    
    async def parse_token(self, token: str, check_whitelist: bool = True) -> Tuple[int, int]:
        """
        解析 token，验证失败直接抛出异常
        :param token: token 字符串
        :param check_whitelist: 是否检查白名单（用户 token 集合），默认为 True
        :return: (user_id, expire_time)
                 - user_id: 用户ID
                 - expire_time: 过期时间戳（毫秒）
        :raises HttpBusinessException: token 无效或已过期时抛出
        """
        try:
            # 分割 token
            parts = token.split('.')
            if len(parts) != 2:
                logger.error(f"token{token}无效")
                raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID)
            
            payload_encrypted, signature = parts
            
            # 验证签名
            expected_signature = self._generate_signature(payload_encrypted)
            if signature != expected_signature:
                logger.error(f"token{token}无效")
                raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID)
            
            # 先解密 payload，再解析 JSON
            payload_json = self._decrypt_data(payload_encrypted)
            payload_data = json.loads(payload_json)
            
            user_id = payload_data.get("user_id")
            expire_time = payload_data.get("expire_time")
            
            if user_id is None or expire_time is None:
                raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID)
            
            # 检查是否过期
            current_time = int(time.time() * 1000)
            if current_time > expire_time:
                logger.error(f"token: {token}已过期")
                raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_EXPIRED)
            
            # 检查白名单（用户 token 集合）
            if check_whitelist:
                is_in_whitelist = await self.is_token_in_user_tokens(user_id, token)
                if not is_in_whitelist:
                    logger.warning(f"token: {token} 不在用户 {user_id} 的有效 token 集合中")
                    raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_EXPIRED)
            
            return user_id, expire_time
        
        except HttpBusinessException:
            # 直接抛出业务异常
            raise
        except json.JSONDecodeError:
            logger.error(f"token: {token} 解析失败")
            raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID)
        except ValueError:
            logger.error(f"token: {token} 解析失败")
            raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID)
        except Exception as e:
            logger.error(f"token: {token} 解析失败")
            raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID)
    
    async def is_token_valid(self, token: str) -> bool:
        """
        检查 token 是否有效
        :param token: token 字符串
        :return: 是否有效
        """
        try:
            await self.parse_token(token)
            return True
        except HttpBusinessException:
            return False
    
    async def get_user_id_from_token(self, token: str) -> Optional[int]:
        """
        从 token 中获取用户ID
        :param token: token 字符串
        :return: 用户ID
        :raises HttpBusinessException: token 无效或已过期时抛出
        """
        user_id, _ = await self.parse_token(token)
        return user_id
    
    # ==================== 白名单方案：用户 Token 集合管理 ====================
    
    async def add_token_to_user(self, user_id: int, token: str, expire_time: int) -> bool:
        """
        将 token 添加到用户的 token 集合中（白名单）
        :param user_id: 用户ID
        :param token: token 字符串
        :param expire_time: token 的过期时间戳（毫秒）
        :return: 是否添加成功
        """
        try:
            cache_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            
            # 检查是否需要限制设备数量
            max_tokens = self.max_tokens_per_user
            if max_tokens > 0:
                current_count = await redis_client.scard(cache_key)
                if current_count >= max_tokens:
                    # 移除最旧的 token（FIFO）
                    oldest_token = await redis_client.spop(cache_key)
                    logger.info(f"用户 {user_id} 达到最大设备数 {max_tokens}，移除旧 token")
            
            # 将 token 添加到 Set 中
            await redis_client.sadd(cache_key, token)
            
            # 计算过期时间（设置为 token 的过期时间）
            current_time = int(time.time() * 1000)
            ttl_seconds = max(int((expire_time - current_time) / 1000), 1)
            await redis_client.expire(cache_key, ttl_seconds)
            
            logger.info(f"token 已添加到用户 {user_id} 的 token 集合，TTL: {ttl_seconds}秒")
            return True
        except Exception as e:
            logger.error(f"将 token 添加到用户集合失败: {str(e)}")
            return False
    
    async def is_token_in_user_tokens(self, user_id: int, token: str) -> bool:
        """
        检查 token 是否在用户的 token 集合中（白名单）
        :param user_id: 用户ID
        :param token: token 字符串
        :return: 是否在集合中
        """
        try:
            cache_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            result = await redis_client.sismember(cache_key, token)
            # sismember 返回 True/False 或 1/0，统一转换为布尔值
            return bool(result)
        except Exception as e:
            logger.error(f"检查用户 token 集合失败: {str(e)}")
            # 如果 Redis 出错，为安全起见返回 True（不阻止用户访问）
            return True
    
    async def remove_token_from_user(self, user_id: int, token: str) -> bool:
        """
        从用户的 token 集合中移除指定 token
        :param user_id: 用户ID
        :param token: token 字符串
        :return: 是否移除成功
        """
        try:
            cache_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            await redis_client.srem(cache_key, token)
            logger.info(f"token 已从用户 {user_id} 的集合中移除")
            return True
        except Exception as e:
            logger.error(f"从用户集合移除 token 失败: {str(e)}")
            return False
    
    async def remove_all_user_tokens(self, user_id: int) -> bool:
        """
        移除用户所有 token（清空用户的 token 集合）
        :param user_id: 用户ID
        :return: 是否移除成功
        """
        try:
            cache_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            await redis_client.delete(cache_key)
            logger.info(f"用户 {user_id} 的所有 token 已清空")
            return True
        except Exception as e:
            logger.error(f"清空用户所有 token 失败: {str(e)}")
            return False
    
    async def get_user_tokens(self, user_id: int) -> list:
        """
        获取用户所有有效的 token
        :param user_id: 用户ID
        :return: token 列表
        """
        try:
            cache_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            tokens = await redis_client.smembers(cache_key)
            return list(tokens) if tokens else []
        except Exception as e:
            logger.error(f"获取用户 token 列表失败: {str(e)}")
            return []
    
    async def get_user_online_device_count(self, user_id: int) -> int:
        """
        获取用户在线设备数量
        :param user_id: 用户ID
        :return: 设备数量
        """
        try:
            cache_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            count = await redis_client.scard(cache_key)
            return count
        except Exception as e:
            logger.error(f"获取用户设备数量失败: {str(e)}")
            return 0


# 创建全局实例
token_service = TokenService()

