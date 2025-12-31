from typing import Optional

from pydantic import BaseModel, Field


class RecommendItem(BaseModel):
    """推荐项通用模型"""
    title: str = Field(..., description="标题")
    sub_title: Optional[str] = Field(..., description="副标题")
    video_url: str = Field(..., description="视频URL")
    design_image_url: str = Field(..., description="图片URL")
    type: Optional[str] = Field(..., description="类型")
    design_product_id: int = Field(..., description="设计产品ID")

    class Config:
        from_attributes = True
