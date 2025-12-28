from tortoise.expressions import Q

from application.apis.user.schema.request import (
    CreateUserReq, UpdateUserReq, DisableUserReq, QueryUserListReq, GetUserDetailReq
)
from application.apis.user.schema.response import UserInfoRes
from application.common.base.base_service import CoreService
from application.common.exception.exception import HttpBusinessException
from application.common.models import User
from application.service.user_service import user_service
from application.service.account_service import account_service


class UserAdminService(CoreService):
    """
    用户管理后台 service
    """

    async def query_user_list(self, req: QueryUserListReq):
        """
        查询用户列表
        :param req: 查询请求
        :return: PaginationResult[User] - 会被自动转换为字典格式
        """
        # 构建查询条件
        query = User.all()
        
        # 关键词搜索：手机号/邮箱/昵称/用户名
        if req.keyword:
            keyword = req.keyword.strip()
            query = query.filter(
                Q(phone__icontains=keyword) |
                Q(email__icontains=keyword) |
                Q(nickname__icontains=keyword) |
                Q(username__icontains=keyword)
            )
        
        # 状态筛选
        if req.state is not None:
            query = query.filter(state=req.state)
        
        # 使用 user_service 的分页方法，返回 PaginationResult[User]
        return await user_service.paginate(
            query=query,
            page_no=req.page,
            page_size=req.page_size,
            order_by=['-created_at']
        )

    async def create_user(self, req: CreateUserReq) -> UserInfoRes:
        """
        新增用户
        :param req: 创建用户请求
        :return: 用户信息
        """
        # 使用 account_service 创建用户
        # account_service.create_user 会自动处理：
        # 1. 检查手机号和邮箱是否已存在
        # 2. 密码加密
        # 3. 设置默认头像
        # 4. 绑定普通用户角色（is_superuser=False 时只绑定普通用户角色）
        user = await account_service.create_user(
            phone_number=req.phone_number,
            password=req.password,
            email=req.email,
            username=req.username,
            nickname=req.nickname,
            is_superuser=False  # 后台创建的用户为普通用户，只绑定普通用户角色
        )

        return UserInfoRes(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            phone=user.phone,
            email=user.email,
            state=user.state,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    async def update_user(self, req: UpdateUserReq) -> UserInfoRes:
        """
        修改用户信息
        :param req: 更新用户请求
        :return: 用户信息
        """
        # 调用 account_service 更新用户信息
        user = await account_service.update_user(
            user_id=req.user_id,
            phone_number=req.phone_number,
            email=req.email,
            nickname=req.nickname,
            username=req.username,
            avatar=req.avatar
        )

        return UserInfoRes(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            phone=user.phone,
            email=user.email,
            state=user.state,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    async def disable_user(self, req: DisableUserReq) -> bool:
        """
        禁用/启用用户
        :param req: 禁用用户请求
        :return: 是否成功
        """
        # 使用 user_service 查询用户是否存在
        user = await user_service.get_by_id(req.user_id)
        if not user:
            raise HttpBusinessException(message="用户不存在")

        # 不能禁用超级管理员
        if user.is_superuser:
            raise HttpBusinessException(message="不能修改超级管理员")

        # 使用 user_service 更新用户状态
        await user_service.update_by_id(req.user_id, {'state': req.state})

        # 如果是禁用操作，清除用户所有 token
        if req.state == '0':
            await account_service.invalidate_user_all_tokens(req.user_id)

        return True

    async def get_user_detail(self, req: GetUserDetailReq) -> UserInfoRes:
        """
        获取用户详情
        :param req: 获取用户详情请求
        :return: 用户信息
        """
        # 使用 user_service 查询用户
        user = await user_service.get_by_id(req.user_id)
        if not user:
            raise HttpBusinessException("用户不存在")

        return UserInfoRes(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            phone=user.phone,
            email=user.email,
            state=user.state,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )


user_admin_service = UserAdminService()

