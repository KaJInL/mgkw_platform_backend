from typing import List
from pydantic import BaseModel, Field

from application.apis.recommend.schema.response import RecommendItem


class UpdateRecommendReq(BaseModel):
    """更新推荐列表请求模型"""
    list : List[RecommendItem] = Field(..., description="推荐列表")

