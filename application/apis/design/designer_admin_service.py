from typing import Optional

import redis
from tortoise.transactions import atomic

from application.apis.design.schema import (
    CreateDesignReq,
    UpdateDesignReq,
    QueryMyDesignListReq,
    SearchDesignListReq,
)
from application.common.constants import RoleEnum, BoolEnum
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.models import Product, ProductCheckState, ProductType, SKU
from application.common.models.design import Design, DesignState
from application.common.schema import LoginUserInfo
from application.core.logger_util import logger
from application.core.redis_client import redis_client
from application.service.account_service import account_service
from application.service.design_license_plan_service import design_license_plan_service
from application.service.design_service import design_service
from application.service.product_design_service import product_design_service
from application.service.product_service import product_service
from application.service.sku_service import sku_service


class DesignerAdminService:
    """
    设计师管理后台服务
    整合设计师管理后台的业务逻辑
    """

    async def create_design(self, req: CreateDesignReq) -> Design:
        """
        创建设计作品
        
        Args:
            req: 作品创建请求对象
            login_user_info: 当前登录用户信息
            
        Returns:
            创建的设计作品对象
        """
        login_user_info = await account_service.get_login_user_info()
        user_id = login_user_info.user.id

        # 准备数据并创建模型对象
        data = req.model_dump(exclude_unset=True, by_alias=False)
        design = Design(**data)

        # 检查是否为公司设计师,如果是的话,则设计作品为自营并且直接审核通过
        if any(role == RoleEnum.COMPANY_DESIGNER for role in login_user_info.roles):
            design.is_official = BoolEnum.YES
            design.state = DesignState.APPROVED
        else:
            design.state = DesignState.PENDING

        # 创建作品
        design = await design_service.create_design(user_id, design)

        # 创建设计作品后，自动创建对应的商品和SKU（使用聚合 service）
        await product_design_service.create_product_for_design(design)
        return design

    async def update_design(self, req: UpdateDesignReq) -> Design:
        """
        更新设计作品
        
        Args:
            req: 作品更新请求对象
            login_user_info: 当前登录用户信息
            
        Returns:
            更新后的设计作品对象
            
        Raises:
            HttpBusinessException: 当作品不存在、无权限修改或已被买断时
        """
        # 获取当前登录用户信息
        login_user_info = await account_service.get_login_user_info()
        user_id = login_user_info.user.id

        # 获取现有作品
        existing = await design_service.get_by_id(req.design_id)
        if not existing or existing.user_id != user_id:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "作品不存在或无权限修改"
            )

        # 已被买断的作品不可编辑
        if existing.state == DesignState.BOUGHT_OUT:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "该作品已被买断，无法编辑"
            )

        # 更新属性（只更新提供的字段）
        update_data = req.model_dump(exclude_unset=True, exclude={"design_id"}, by_alias=False)
        for key, value in update_data.items():
            setattr(existing, key, value)

        # 检查是否为公司设计师,如果是的话,则设计作品为自营并且直接审核通过
        existing.state = (
            DesignState.APPROVED
            if RoleEnum.COMPANY_DESIGNER in login_user_info.roles
            else DesignState.PENDING
        )

        # 更新作品
        design = await design_service.update_design(existing, user_id)

        if not design:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "更新失败"
            )

        # 如果设计作品绑定了商品，同步更新商品信息
        if design.product_id:
            await product_design_service.sync_design_to_product(design)

        return design

    async def delete_design(self, design_id: int) -> bool:
        """
        删除设计作品（会同时删除绑定的商品）
        
        Args:
            design_id: 作品ID
            
        Returns:
            删除是否成功
            
        Raises:
            HttpBusinessException: 当作品不存在或无权限删除时
        """
        login_user_info = await account_service.get_login_user_info()
        user_id = login_user_info.user.id

        # 使用聚合 service 删除设计作品及其绑定的商品（双向删除）
        success = await product_design_service.delete_design_with_product(design_id, user_id)

        if not success:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "作品不存在或无权限删除"
            )

        return True

    async def get_design_detail(self, design_id: int) -> Design:
        """
        获取设计作品详情
        
        Args:
            design_id: 作品ID
            
        Returns:
            设计作品对象
            
        Raises:
            HttpBusinessException: 当作品不存在时
        """
        design = await design_service.get_by_id(design_id)

        if not design:
            raise HttpBusinessException(HttpErrorCodeEnum.ERROR, "作品不存在")

        return design

    async def query_my_design_list(
            self,
            req: QueryMyDesignListReq,
            login_user_info: LoginUserInfo
    ) -> dict:
        """
        查询我的设计作品列表
        
        Args:
            req: 查询参数对象
            login_user_info: 当前登录用户信息
            
        Returns:
            分页结果字典
        """
        user_id = login_user_info.user.id

        # 构建查询
        query = Design.filter(user_id=user_id, is_deleted=BoolEnum.NO)

        # 状态筛选
        if req.state:
            query = query.filter(state=req.state)

        # 关键词搜索
        if req.keyword:
            query = query.filter(title__icontains=req.keyword).filter(description__icontains=req.keyword)

        # 分页查询
        result = await design_service.paginate(
            query=query,
            page_no=req.page,
            page_size=req.page_size,
            order_by=["-created_at"]
        )

        return result

    async def search_design_list(self, req: SearchDesignListReq) -> dict:
        """
        搜索设计作品
        
        Args:
            req: 搜索参数对象
            
        Returns:
            分页结果字典
        """
        # 构建搜索查询（只返回已审核通过的作品）
        query = await design_service.search_designs(
            keyword=req.keyword,
            category_id=req.category_id,
            series_id=req.series_id,
            state=DesignState.APPROVED,  # 只显示已审核通过的
            is_official=req.is_official,
            tags=req.tags
        )

        # 分页查询
        result = await design_service.paginate_dic(
            query=query,
            page_no=req.page,
            page_size=req.page_size,
            order_by=["-created_at"]
        )

        return result

    async def change_design_state(
            self,
            design_id: int,
            new_state: DesignState,
            login_user_info: LoginUserInfo
    ) -> Design:
        """
        修改作品状态
        
        Args:
            design_id: 作品ID
            new_state: 新状态
            login_user_info: 当前登录用户信息
            
        Returns:
            更新后的设计作品对象
            
        Raises:
            HttpBusinessException: 当作品不存在或无权限修改时
        """
        user_id = login_user_info.user.id

        # 修改状态
        design = await design_service.change_design_state(design_id, user_id, new_state)

        if not design:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "作品不存在或无权限修改"
            )

        return design

    async def restore_design(self, design_id: int, login_user_info: LoginUserInfo) -> bool:
        """
        恢复已删除的作品
        
        Args:
            design_id: 作品ID
            login_user_info: 当前登录用户信息
            
        Returns:
            恢复是否成功
            
        Raises:
            HttpBusinessException: 当作品不存在、未删除或无权限恢复时
        """
        user_id = login_user_info.user.id

        # 恢复作品
        success = await design_service.restore_design(design_id, user_id)

        if not success:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "作品不存在、未删除或无权限恢复"
            )

        return True


# 创建全局实例
designer_admin_service = DesignerAdminService()
