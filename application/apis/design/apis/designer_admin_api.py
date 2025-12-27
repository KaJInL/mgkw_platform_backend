from fastapi import APIRouter, Depends

from application.apis.design.schema import (
    CreateDesignReq,
    UpdateDesignReq,
    DeleteDesignReq,
    GetDesignDetailReq,
    QueryMyDesignListReq,
    SearchDesignListReq,
    ChangeDesignStateReq,
    DesignInfoRes
)
from application.common.schema import PaginationData, BaseResponse
from application.common.helper import ResponseHelper
from application.service.account_service import account_service
from application.apis.design.designer_admin_service import designer_admin_service

designer_admin_router = APIRouter(tags=["设计师管理端接口"])


@designer_admin_router.post(
    "/designer-admin/design/create",
    summary="创建设计作品",
    description="设计师上传新作品，自动关联当前登录用户",
    response_model=BaseResponse[DesignInfoRes],
)
async def create_design(req: CreateDesignReq):
    """
    创建设计作品
    
    Args:
        req: 作品创建请求对象
    """
    # 调用 service 创建设计作品
    design = await designer_admin_service.create_design(req)

    return ResponseHelper.success(DesignInfoRes.model_validate(design))


@designer_admin_router.post(
    "/designer-admin/design/update",
    summary="更新设计作品",
    description="更新自己的设计作品信息",
    response_model=BaseResponse[DesignInfoRes],
)
async def update_design(req: UpdateDesignReq):
    """
    更新设计作品
    
    Args:
        req: 作品更新请求对象
    """

    # 调用 service 更新设计作品
    design = await designer_admin_service.update_design(req)

    return ResponseHelper.success(DesignInfoRes.model_validate(design))


@designer_admin_router.post(
    "/designer-admin/design/delete",
    summary="删除设计作品",
    description="删除自己的设计作品",
    response_model=BaseResponse[bool],
)
async def delete_design(req: DeleteDesignReq):
    """
    删除设计作品
    
    Args:
        req: 删除请求对象
    """
    # 调用 service 删除设计作品
    await designer_admin_service.delete_design(req.design_id)

    return ResponseHelper.success(True)


@designer_admin_router.get(
    "/designer-admin/design/detail",
    summary="获取设计作品详情",
    description="获取作品的详细信息（带缓存）",
    response_model=BaseResponse[DesignInfoRes],
)
async def get_design_detail(req: GetDesignDetailReq = Depends()):
    """
    获取设计作品详情
    
    Args:
        req: 查询参数对象
    """
    # 调用 service 获取设计作品详情
    design = await designer_admin_service.get_design_detail(req.design_id)

    return ResponseHelper.success(DesignInfoRes.model_validate(design))


@designer_admin_router.get(
    "/designer-admin/design/my-list",
    summary="查询我的设计作品列表",
    description="分页查询当前用户的设计作品，支持状态筛选和关键词搜索",
    response_model=BaseResponse[PaginationData[DesignInfoRes]],
)
async def query_my_design_list(req: QueryMyDesignListReq = Depends()):
    """
    查询我的设计作品列表
    
    Args:
        req: 查询参数对象
    """
    # 获取当前登录用户信息
    login_user_info = await account_service.get_login_user_info()

    # 调用 service 查询我的设计作品列表
    result = await designer_admin_service.query_my_design_list(req, login_user_info)

    return ResponseHelper.success(result)


@designer_admin_router.get(
    "/design/search",
    summary="搜索设计作品",
    description="公开接口，搜索已审核通过的设计作品，支持多条件筛选",
    response_model=BaseResponse[PaginationData[DesignInfoRes]],
)
async def search_design_list(req: SearchDesignListReq = Depends()):
    """
    搜索设计作品
    
    Args:
        req: 搜索参数对象
    """
    # 调用 service 搜索设计作品
    result = await designer_admin_service.search_design_list(req)

    return ResponseHelper.success(result)


@designer_admin_router.post(
    "/designer-admin/design/change-state",
    summary="修改作品状态",
    description="修改自己作品的状态（如从草稿提交为待审核）",
    response_model=BaseResponse[DesignInfoRes],
)
async def change_design_state(req: ChangeDesignStateReq):
    """
    修改作品状态
    
    Args:
        req: 状态修改请求对象
    """
    # 获取当前登录用户信息
    login_user_info = await account_service.get_login_user_info()

    # 调用 service 修改作品状态
    design = await designer_admin_service.change_design_state(
        req.design_id,
        req.state,
        login_user_info
    )

    return ResponseHelper.success(DesignInfoRes.model_validate(design))


@designer_admin_router.post(
    "/designer-admin/design/restore",
    summary="恢复已删除的作品",
    description="恢复自己已软删除的作品",
    response_model=BaseResponse[bool],
)
async def restore_design(req: DeleteDesignReq):
    """
    恢复已删除的作品
    
    Args:
        req: 包含作品ID的请求对象
    """
    # 获取当前登录用户信息
    login_user_info = await account_service.get_login_user_info()

    # 调用 service 恢复已删除的作品
    await designer_admin_service.restore_design(req.design_id, login_user_info)

    return ResponseHelper.success(True)
