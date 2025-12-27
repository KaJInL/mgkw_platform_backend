from typing import Optional, List, Dict, Any

from application.apis.common.sys_conf.schema.request import (
    CreateSysConfReq,
    UpdateSysConfReq
)
from application.apis.common.sys_conf.schema.response import (
    SysConfResponse
)
from application.common.base.base_service import CoreService
from application.common.models import SysConf
from application.service.sys_conf_service import sys_conf_service


class SysConfAdminService(CoreService):
    """
    系统配置管理后台 Service
    """

    async def create_config(self, req: CreateSysConfReq) -> SysConfResponse:
        """
        创建系统配置
        :param req: 创建请求
        :return: 系统配置响应
        """
        # 检查配置是否已存在
        existing_conf = await sys_conf_service.get_by_key(req.sys_key)
        if existing_conf:
            raise ValueError(f"配置 key '{req.sys_key}' 已存在")

        # 创建配置
        conf = await sys_conf_service.set_config(req.sys_key, req.sys_value)

        # 如果有描述,更新描述字段
        if req.description:
            conf.description = req.description
            await conf.save()

        return SysConfResponse.model_validate(conf)

    async def update_config(self, sys_key: str, req: UpdateSysConfReq) -> SysConfResponse:
        """
        更新系统配置
        :param sys_key: 配置 key
        :param req: 更新请求
        :return: 系统配置响应
        """
        # 检查配置是否存在
        existing_conf = await sys_conf_service.get_by_key(sys_key)
        if not existing_conf:
            raise ValueError(f"配置 key '{sys_key}' 不存在")

        # 更新配置
        conf = await sys_conf_service.set_config(sys_key, req.sys_value,req.description)
        return SysConfResponse.model_validate(conf)

    async def delete_configs(self, ids: List[int]) -> bool:
        """
        批量删除系统配置
        :param ids: 配置 ID 列表
        :return: 是否删除成功
        """
        if not ids:
            raise ValueError("ID 列表不能为空")

        # 删除配置
        deleted_count = await SysConf.filter(id__in=ids).delete()

        if deleted_count == 0:
            raise ValueError("未找到要删除的配置")

        return True

    async def query_configs(
            self,
            sys_key: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> Dict[str, Any]:
        """
        分页查询配置
        :param sys_key: 配置 key (模糊查询)
        :param page: 页码
        :param page_size: 每页数量
        :return: 分页数据
        """
        # 构建查询
        query = SysConf.all()

        if sys_key:
            query = query.filter(sys_key__icontains=sys_key)

        # 使用 sys_conf_service 的 paginate 方法
        return await sys_conf_service.paginate(
            query=query,
            page_no=page,
            page_size=page_size,
            order_by=["-created_at"]
        )

    async def get_by_key(self, sys_key: str) -> Optional[str]:
        """
        根据配置 key 获取配置值
        :param sys_key: 配置 key
        :return: 配置值，如果不存在则返回 None
        """
        return await sys_conf_service.get_value_by_key(sys_key)


# 创建全局实例
sys_conf_admin_service = SysConfAdminService()
