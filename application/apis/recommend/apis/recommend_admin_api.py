from typing import List
from fastapi import APIRouter

from application.apis.recommend.service.recommend_admin_service import recommend_admin_service
from application.apis.recommend.schema.request import UpdateRecommendReq
from application.apis.recommend.schema.response import RecommendItem
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse

recommend_admin = APIRouter(tags=["推荐商品管理接口"])


@recommend_admin.get(
    "/admin/recommend/list",
    summary="获取推荐列表",
    response_model=BaseResponse[List[RecommendItem]]
)
async def get_recommend_list():
    """
    获取推荐列表
    返回格式：[{title: string, sub_title: string, video_url: string, image_url: string, type: string}]
    """
    result = await recommend_admin_service.get_recommend_list()
    return ResponseHelper.success(result)


@recommend_admin.post(
        "/admin/recommend/update",
    summary="更新推荐列表",
    response_model=BaseResponse[bool]
)
async def update_recommend_list(req: UpdateRecommendReq):
    """
    更新推荐列表
    请求格式：{items: [{title: string, sub_title: string, video_url: string, image_url: string, type: string}]}
    """
    success = await recommend_admin_service.update_recommend_list(req.list)
    if success:
        return ResponseHelper.success(True, message="更新推荐列表成功")
    else:
        return ResponseHelper.error(message="更新推荐列表失败")
