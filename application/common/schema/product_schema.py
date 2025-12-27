"""
产品相关的 Schema 定义
"""
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class SkuInfo(BaseModel):
    """SKU 信息"""
    id: int = Field(description="SKU ID")
    product_id: int = Field(description="所属商品ID")
    name: str = Field(description="SKU名称")
    price: Decimal = Field(description="售价")
    original_price: Optional[Decimal] = Field(None, description="原价")
    stock: int = Field(description="库存数量")
    code: Optional[str] = Field(None, description="商品编码")
    attributes: dict = Field(default_factory=dict, description="SKU属性")
    is_enabled: bool = Field(description="是否启用")
    weight: Optional[Decimal] = Field(None, description="重量")
    vip_plan_id: Optional[int] = Field(None, description="会员套餐ID")
    design_license_plan_id: Optional[int] = Field(None, description="设计授权方案ID")
    design_id: Optional[int] = Field(None, description="设计作品ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class ProductWithSkusInfo(BaseModel):
    """产品信息（包含 SKU 列表）"""
    id: int = Field(description="商品ID")
    name: str = Field(description="商品名称")
    subtitle: Optional[str] = Field(None, description="商品副标题")
    cover_image: str = Field(description="商品封面图URL")
    image_urls: List[str] = Field(default_factory=list, description="商品图片列表")
    video_url: Optional[str] = Field(None, description="商品视频URL")
    description: Optional[str] = Field(None, description="商品简介")
    detail_html: Optional[str] = Field(None, description="商品详情富文本")
    category_id: int = Field(description="分类ID")
    series_id: int = Field(description="系列ID")
    is_published: bool = Field(description="是否上架")
    creator_user_id: int = Field(description="商品创建者用户ID")
    check_state: str = Field(description="审核状态")
    check_reason: Optional[str] = Field(None, description="审核拒绝原因")
    checker_user_id: Optional[int] = Field(None, description="审核管理员ID")
    checked_at: Optional[str] = Field(None, description="审核时间")
    sort: int = Field(description="排序值")
    tags: List[str] = Field(default_factory=list, description="商品标签列表")
    product_type: str = Field(description="商品类型")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    skus: List[SkuInfo] = Field(default_factory=list, description="SKU列表")

    class Config:
        from_attributes = True

