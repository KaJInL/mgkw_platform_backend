from typing import Optional
from tortoise.expressions import Q

from application.apis.auth.schema.request import (
    QueryRoleListReq, CreateRoleReq, UpdateRoleReq, DeleteRoleReq, GetRoleDetailReq
)
from application.apis.auth.schema.response import RoleInfoRes
from application.common.exception.exception import HttpBusinessException
from application.common.models import Role
from application.common.schema import PaginationData
from application.service.role_service import role_service
from application.core.logger_util import logger


class RoleAdminService:
    """角色管理服务"""

    @staticmethod
    def _role_to_response(role: Role) -> RoleInfoRes:
        """将 Role 模型转换为响应对象"""
        return RoleInfoRes(
            id=role.id,
            role_name=role.role_name,
            description=role.description,
            is_system=role.is_system,
            created_at=role.created_at
        )

    async def query_role_list(self, req: QueryRoleListReq) -> PaginationData[RoleInfoRes]:
        """
        查询角色列表（分页）
        :param req: 查询参数
        :return: 分页数据
        """
        # 构建查询条件
        query = Role.all()

        # 关键词搜索（角色名或描述）
        if req.keyword:
            query = query.filter(
                Q(role_name__icontains=req.keyword) | Q(description__icontains=req.keyword)
            )

        # 是否为系统角色筛选
        if req.is_system is not None:
            query = query.filter(is_system=req.is_system)

        # 总数
        total = await query.count()

        # 分页查询
        offset = (req.page - 1) * req.page_size
        roles = await query.offset(offset).limit(req.page_size).order_by('-created_at')

        # 转换为响应对象
        items = [self._role_to_response(role) for role in roles]

        logger.info(f"📋 查询角色列表，共 {total} 条，当前页 {len(items)} 条")

        return PaginationData(
            total=total,
            items=items,
            page=req.page,
            page_size=req.page_size
        )

    async def create_role(self, req: CreateRoleReq) -> RoleInfoRes:
        """
        创建角色
        :param req: 创建请求
        :return: 角色信息
        """
        # 检查角色名是否已存在
        existing_role = await Role.filter(role_name=req.role_name).first()
        if existing_role:
            raise HttpBusinessException(f"角色名 '{req.role_name}' 已存在")

        # 创建角色（通过 role_service 以清除缓存）
        role = await role_service.get_or_create_role(
            role_name=req.role_name,
            description=req.description or req.role_name,
            is_system=False  # 通过接口创建的都是非系统角色
        )

        logger.info(f"✨ 创建角色成功: {role.role_name}")

        return self._role_to_response(role)

    async def update_role(self, req: UpdateRoleReq) -> RoleInfoRes:
        """
        更新角色信息
        :param req: 更新请求
        :return: 更新后的角色信息
        """
        # 查询角色
        role = await role_service.get_by_id(req.role_id)
        if not role:
            raise HttpBusinessException(f"角色 ID={req.role_id} 不存在")

        # 系统角色不允许修改
        if role.is_system:
            raise HttpBusinessException("系统角色不允许修改")

        # 检查角色名是否重复
        if req.role_name and req.role_name != role.role_name:
            existing_role = await Role.filter(role_name=req.role_name).first()
            if existing_role:
                raise HttpBusinessException(f"角色名 '{req.role_name}' 已存在")

        # 构建更新字段
        update_fields = {}
        if req.role_name is not None:
            update_fields['role_name'] = req.role_name
        if req.description is not None:
            update_fields['description'] = req.description

        if not update_fields:
            raise HttpBusinessException("没有需要更新的字段")

        # 通过 role_service 更新（以清除缓存）
        updated_role = await role_service.update_role(req.role_id, **update_fields)

        logger.info(f"📝 更新角色成功: {updated_role.role_name}")

        return self._role_to_response(updated_role)

    async def delete_role(self, req: DeleteRoleReq) -> bool:
        """
        删除角色
        :param req: 删除请求
        :return: 是否成功
        """
        # 通过 role_service 删除（以清除缓存和检查系统角色）
        await role_service.delete_role(req.role_id)

        logger.info(f"🗑️ 删除角色成功: ID={req.role_id}")

        return True

    async def get_role_detail(self, req: GetRoleDetailReq) -> RoleInfoRes:
        """
        获取角色详情
        :param req: 查询请求
        :return: 角色信息
        """
        role = await Role.filter(id=req.role_id).first()
        if not role:
            raise HttpBusinessException(f"角色 ID={req.role_id} 不存在")

        return self._role_to_response(role)

    async def get_all_roles(self) -> list[RoleInfoRes]:
        """
        获取所有角色（不分页）
        :return: 角色列表
        """
        roles = await Role.all().order_by('-created_at')
        return [self._role_to_response(role) for role in roles]


role_admin_service = RoleAdminService()
