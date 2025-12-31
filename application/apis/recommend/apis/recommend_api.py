from typing import List
from fastapi import APIRouter

from application.service.recommend_service import recommend_service
from application.apis.recommend.schema.response import RecommendItem
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse

recommend = APIRouter(tags=["推荐前端接口"])


@recommend.get(
    "/recommend/list",
    summary="前端获取推荐列表",
    response_model=BaseResponse[List[RecommendItem]]
)
async def get_recommend_list():
    """
    前端获取推荐列表
    返回格式：[{title: string, sub_title: string, video_url: string, image_url: string, type: string}]
    """
    result = await recommend_service.get_recommend_list()
    return ResponseHelper.success(result)

