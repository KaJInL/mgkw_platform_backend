import hashlib
import random
import string
from datetime import datetime
from typing import Optional

from tortoise.exceptions import IntegrityError
from tortoise.transactions import atomic

from application.apis.account.schema.response import LoginRes
from application.common.config import config
from application.common.constants import RoleEnum, StateEnum
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.middleware.RequestContextMiddleware import get_ctx
from application.common.models import User, UserRole, Role, AuthTypeEnum
from application.common.schema import LoginUserInfo
from application.common.utils import PasswordUtils
from application.core.logger_util import logger
from application.core.redis_client import redis_client, TimeUnit
from application.service.role_service import role_service
from application.service.sys_conf_service import sys_conf_service
from application.service.token_service import token_service
from application.service.user_auth_service import user_auth_service
from application.service.user_role_service import user_role_service
from application.service.user_service import user_service
from application.service.user_vip_service import user_vip_service


class AccountService:
    """
    用户帐户认证service
    """
    CHANGE_USER_LOCK = "change_user_lock:"
    LOGIN_USER_INFO_KEY = "login_user_info:"

    @property
    def token_expire_days(self) -> int:
        """
        获取token过期时间（天）
        从配置文件中读取，如果未配置则使用默认值7天
        """
        return config.auth.token_expire_days

    @atomic()
    async def create_user(self, phone_number: str, password: str, email: str = None, username=None, nickname=None,
                          is_superuser: bool = False) -> User:
        """
        创建用户
        :param username: 用户名
        :param nickname: 用户昵称
        :param is_superuser: 是否为超级管理员用户（True时绑定超管角色+普通用户角色，False时只绑定普通用户角色）
        :param email: 用户邮箱
        :param phone_number: 用户手机号
        :param password: 明文密码
        :return: 创建的用户对象
        """

        async with redis_client.lock(f"create_user_lock:{phone_number}") as lock:
            # 先查询手机号是否已经注册
            existing_user = await user_service.get_user_by_phone(phone=phone_number)
            if existing_user:
                raise HttpBusinessException(message="手机号已经注册")

            # 如果提供了邮箱，检查邮箱是否已经注册
            if email:
                existing_email = await user_service.get_user_by_email(email=email)
                if existing_email:
                    raise HttpBusinessException("邮箱已经注册")

            # 对密码进行加密
            password_hash, password_salt = PasswordUtils.hash_password(password)

            # 获取默认头像
            default_avatar = await sys_conf_service.get_default_avatar()

            # 如果提供了 username 和 nickname 则使用，否则自动生成
            if not username:
                username = self.generate_username(phone_number)
            if not nickname:
                nickname = username

            # 创建用户
            user = await user_service.model_class.create(
                phone=phone_number,
                email=email,
                avatar=default_avatar,
                password_hash=password_hash,
                password_salt=password_salt,
                is_superuser=is_superuser,
                state=StateEnum.ENABLED,  # 默认状态启用
                username=username,
                nickname=nickname,
            )

            # 根据 is_superuser 判断绑定角色
            if is_superuser:
                # 超级管理员：绑定超管角色 + 普通用户角色
                await user_role_service.bind_super_admin_role(user.id)
                # 更新系统配置中的超级管理员注册状态
                await sys_conf_service.mark_super_user_created()

            # 绑定普通用户角色
            await user_role_service.bind_user_role(user.id)

            return user

    def generate_username(self, phone_number: str) -> str:
        """
        生成用户名：mg_<手机号>_<随机哈希>
        """
        # 生成一个随机字符串（例如 6 位）
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        # 用 MD5 哈希一下防止泄露结构，可选
        hash_part = hashlib.md5(random_str.encode()).hexdigest()[:6]
        return f"mg_{phone_number}_{hash_part}"

    async def login_by_pwd(self, phone_number: str, password: str, need_admin_role: bool = False) -> LoginRes:
        """
        登录方法
        :param need_admin_role: 是否需要管理员角色
        :param phone_number:用户手机号
        :param password:  密码
        :return:
        """
        user = await user_service.get_user_by_phone(phone_number)
        if user is None:
            raise HttpBusinessException(message="用户不存在")

        # 管理员角色检查
        if need_admin_role:
            is_admin = await user_role_service.is_admin(user.id)
            if not is_admin:
                raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, "用户没有管理员权限")

        # 对比密码
        password_checked = PasswordUtils.verify_password(password, user.password_hash, user.password_salt)
        if not password_checked:
            raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, "密码错误")

        return await self.login(user)

    async def login(self, user: User) -> LoginRes:
        """
        执行登录流程
        :param user: 用户对象
        :return: token字符串
        """
        async with redis_client.lock(f"{self.CHANGE_USER_LOCK}{user.id}"):
            # 1. 查询用户的所有角色信息
            user_roles = await UserRole.filter(user_id=user.id).all()
            role_ids = [ur.role_id for ur in user_roles]

            # 2. 获取角色详细信息（ORM 对象）
            roles = []
            if role_ids:
                roles = await Role.filter(id__in=role_ids).all()

            # 3. 获取用户vip信息
            user_vip_info = await user_vip_service.model_class.filter(user_id=user.id).get_or_none()

            # 4. 获取用户授权信息
            user_auths = await user_auth_service.model_class.filter(user_id=user.id).all()

            # 5. 构造 LoginUserInfo（使用工厂方法从 ORM 对象创建）
            login_user_info = LoginUserInfo.from_orm_objects(
                user=user, 
                roles=roles, 
                user_vip=user_vip_info,
                user_auths=user_auths
            )

            # 6. 生成 token
            token = token_service.generate_token(
                user_id=user.id,
                expire_days=self.token_expire_days
            )

            # 7. 将 token 添加到用户的 token 集合（白名单）
            import time
            expire_time = int((time.time() + self.token_expire_days * 24 * 3600) * 1000)
            await token_service.add_token_to_user(user.id, token, expire_time)

            # 8. 将登录用户信息缓存到 Redis（包含授权信息）
            cache_key = f"{self.LOGIN_USER_INFO_KEY}{user.id}"
            await redis_client.set(
                cache_key,
                login_user_info.model_dump(),  # 转换为字典
                time=self.token_expire_days,
                unit=TimeUnit.DAYS
            )

            return LoginRes(token=token, user_info=login_user_info)

    async def get_login_user_info(self) -> LoginUserInfo:
        """
        获取当前登录用户信息
        :return: 登录用户信息
        """
        token = get_ctx().token
        if not token:
            raise HttpBusinessException(HttpErrorCodeEnum.UNAUTHORIZED)

        return await self.get_login_user_info_by_token(token)

    async def get_login_user_info_by_token(self, token: str) -> LoginUserInfo:
        """
        根据 token 获取登录用户信息
        :param token: token字符串
        :return: 登录用户信息
        :raises HttpBusinessException: token无效、已过期或用户信息不存在时抛出
        """
        # 1. 解析 token（自动验证并抛出异常）
        user_id, expire_time = await token_service.parse_token(token)

        # 2. 从 Redis 获取登录用户信息
        cache_key = f"{self.LOGIN_USER_INFO_KEY}{user_id}"
        cached_data = await redis_client.get(cache_key)

        if cached_data is None:
            raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_EXPIRED, "登录信息已过期，请重新登录")
        # 3. 将字典数据转换为 LoginUserInfo 对象
        try:
            login_user_info = LoginUserInfo.model_validate(cached_data)
            return login_user_info
        except Exception as e:
            logger.exception(f"解析登录信息失败: {e}")
            raise HttpBusinessException(HttpErrorCodeEnum.TOKEN_INVALID, f"登录信息格式错误: {str(e)}")

    async def is_vip(self) -> bool:
        """
        判断当前登录用户是否为有效VIP会员
        
        判断逻辑：
        1. 如果用户未登录，返回 False（不会抛出异常）
        2. 如果用户没有VIP信息，返回 False
        3. 如果VIP已过期（end_time <= 当前时间），返回 False
        4. 如果VIP未过期（end_time > 当前时间），返回 True
        
        :return: True表示是有效VIP，False表示不是VIP或已过期
        """
        try:
            # 获取当前登录用户信息
            login_user_info = await self.get_login_user_info()
            
            # 检查VIP信息是否存在
            if not login_user_info.vip:
                return False
            
            # 检查VIP是否过期（end_time > 当前时间表示未过期）
            current_time = datetime.now()
            return login_user_info.vip.end_time > current_time
            
        except HttpBusinessException:
            return False
        except Exception as e:
            # 其他异常，记录日志并返回 False（不中断程序）
            logger.exception(f"判断VIP状态失败: {e}")
            return False

    async def is_admin(self) -> bool:
        """
        判断当前登录用户是否为管理员或超级管理员
        
        判断逻辑：
        1. 如果用户未登录，返回 False（不会抛出异常）
        2. 遍历用户的角色列表，检查是否包含管理员（admin）或超级管理员（super_admin）角色
        3. 如果包含任一角色，返回 True；否则返回 False
        
        :return: True表示是管理员或超级管理员，False表示不是
        """
        try:
            # 获取当前登录用户信息
            login_user_info = await self.get_login_user_info()
            
            # 检查角色列表中是否包含管理员或超级管理员角色
            admin_role_names = {RoleEnum.ADMIN, RoleEnum.SUPER_ADMIN}
            user_role_names = {role.role_name for role in login_user_info.roles}
            
            # 判断是否有交集（即用户是否拥有管理员或超级管理员角色）
            return bool(admin_role_names & user_role_names)
            
        except HttpBusinessException:
            return False
        except Exception as e:
            # 其他异常，记录日志并返回 False（不中断程序）
            logger.exception(f"判断管理员状态失败: {e}")
            return False

    async def invalidate_token(self, token: str) -> bool:
        """
        手动失效指定的 token（从用户 token 集合中移除）
        :param token: 要失效的 token
        :return: 是否失效成功
        """
        try:
            # 先解析 token 获取用户ID（不检查白名单）
            user_id, expire_time = await token_service.parse_token(token, check_whitelist=False)

            # 从用户的 token 集合中移除
            success = await token_service.remove_token_from_user(user_id, token)

            if success:
                from application.core.logger_util import logger
                logger.info(f"管理员手动失效用户 {user_id} 的 token")

            return success
        except HttpBusinessException:
            # token 本身无效或已过期，不需要处理
            return True

    async def invalidate_user_all_tokens(self, user_id: int) -> bool:
        """
        手动失效指定用户的所有 token（清空用户的 token 集合）
        :param user_id: 用户ID
        :return: 是否失效成功
        """
        try:
            # 清空用户的 token 集合
            success = await token_service.remove_all_user_tokens(user_id)

            # 同时删除登录信息缓存（双重保险）
            cache_key = f"{self.LOGIN_USER_INFO_KEY}{user_id}"
            await redis_client.delete(cache_key)

            if success:
                from application.core.logger_util import logger
                logger.info(f"管理员手动失效用户 {user_id} 的所有 token")

            return success
        except Exception as e:
            from application.core.logger_util import logger
            logger.error(f"失效用户 {user_id} 的所有 token 失败: {str(e)}")
            return False

    async def get_user_online_devices(self, user_id: int) -> dict:
        """
        获取用户在线设备信息
        :param user_id: 用户ID
        :return: 设备信息字典
        """
        tokens = await token_service.get_user_tokens(user_id)
        device_count = len(tokens)

        return {
            "user_id": user_id,
            "device_count": device_count,
            "tokens": tokens
        }

    async def kick_device(self, token: str) -> bool:
        """
        踢出指定设备（失效指定 token）
        :param user_id: 用户ID
        :param token: 要踢出的 token
        :return: 是否成功
        """
        return await self.invalidate_token(token)

    async def refresh_user_login_cache(self, user_id: int) -> bool:
        """
        刷新用户的登录缓存信息（不删除 token，只更新缓存的用户信息）
        用于用户信息或角色变更后，更新缓存中的用户信息，避免强制用户退出登录
        
        :param user_id: 用户ID
        :return: 是否刷新成功
        """
        try:
            # 1. 查询用户信息
            user = await user_service.get_by_id(user_id)
            if not user:
                logger.warning(f"刷新登录缓存失败：用户 {user_id} 不存在")
                return False

            # 2. 查询用户的所有角色信息
            user_roles = await UserRole.filter(user_id=user_id).all()
            role_ids = [ur.role_id for ur in user_roles]

            # 3. 获取角色详细信息（ORM 对象）
            roles = []
            if role_ids:
                roles = await Role.filter(id__in=role_ids).all()

            # 4. 获取用户授权信息
            user_auths = await user_auth_service.model_class.filter(user_id=user_id).all()

            # 5. 获取用户VIP信息（可选）
            user_vip_info = await user_vip_service.model_class.filter(user_id=user_id).get_or_none()

            # 6. 构造 LoginUserInfo（使用工厂方法从 ORM 对象创建）
            login_user_info = LoginUserInfo.from_orm_objects(
                user=user, 
                roles=roles,
                user_vip=user_vip_info,
                user_auths=user_auths
            )

            # 7. 更新 Redis 中的登录用户信息缓存
            cache_key = f"{self.LOGIN_USER_INFO_KEY}{user_id}"

            # 获取当前缓存的 TTL（保持原有的过期时间）
            ttl = await redis_client.ttl(cache_key)

            if ttl > 0:
                # 如果缓存存在且未过期，使用原有的 TTL 更新缓存
                await redis_client.set(
                    cache_key,
                    login_user_info.model_dump(),
                    time=ttl,
                    unit=TimeUnit.SECONDS
                )
                logger.info(f"已刷新用户 {user_id} 的登录缓存，保持原有过期时间 {ttl} 秒")
            else:
                # 如果缓存不存在或已过期，使用默认过期时间
                await redis_client.set(
                    cache_key,
                    login_user_info.model_dump(),
                    time=self.token_expire_days,
                    unit=TimeUnit.DAYS
                )
                logger.info(f"已刷新用户 {user_id} 的登录缓存，使用默认过期时间 {self.token_expire_days} 天")

            return True
        except Exception as e:
            logger.error(f"刷新用户 {user_id} 的登录缓存失败: {str(e)}")
            return False

    async def login_by_wx_miniprogram_openid(self, openid: str) -> Optional[str]:
        """
        微信小程序使用openid登录
        """
        # 检查这个openid是否已经注册,通过用户第三方授权表查询
        user_auth = await user_auth_service.get_user_id_by_wx_miniprogram_openid(openid)
        if not user_auth:
            return None

        # 查询用户是否存在
        user = await user_service.get_by_id(user_auth.user_id)
        if not user:
            return None

        # 执行登录逻辑
        login_user_info = await self.login(user)
        if not login_user_info:
            return None
        return login_user_info.token

    @atomic()
    async def wx_miniprogram_register(self, phone_number: str, openid: str) -> Optional[str]:
        """
        微信小程序用户注册
        """
        # 检查手机号是否已经创建过用户,如果没有创建过则创建用户
        user = await user_service.get_user_by_phone(phone_number)
        if not user:
            # 创建一个随机密码
            password = PasswordUtils.generate_salt()
            user = await self.create_user(phone_number, password)

        # 保存微信小程序授权信息
        try:
            user_auth = await user_auth_service.save_auth_info(user.id, openid, AuthTypeEnum.WECHAT_MINI_PROGRAM)
        except IntegrityError:
            raise HttpBusinessException(message="此手机号已绑定其他用户...")

        if not user_auth:
            raise HttpBusinessException(HttpErrorCodeEnum.LOGIN_FAILED)

        # 登录
        login_user_info = await self.login(user)
        if not login_user_info:
            raise HttpBusinessException(HttpErrorCodeEnum.LOGIN_FAILED)

        return login_user_info.token


account_service = AccountService()
