from typing import List, Optional, Any
from pydantic import BaseModel, Field
from application.common.models.design import DesignState
from application.common.schema.product_schema import ProductWithSkusInfo

class DesignProductInfoRes(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category_id: Optional[int]
    series_id: Optional[int]
    product_id: Optional[int]
    tags: List[Any]
    images: List[str]
    state: DesignState
    is_official: bool
    is_deleted: str

class DesignProductDetailRes(BaseModel):
    has_permission: bool = False  # 是否有权限查看设计详情（resource_url和detail）
    design: Optional[Any] 
    product: Optional[ProductWithSkusInfo]

class VipPlanInfo(BaseModel):
    id: int
    name: str
    days: int
    price: Any
    privileges: Optional[str]
    bg_image_url: Optional[str] = Field(alias="bgImageUrl")

    class Config:
        populate_by_name = True
        from_attributes = True

class VipProductInfoRes(BaseModel):
    id: int
    product_id: int = Field(alias="productId")  # 商品ID（与id相同，方便前端使用）
    name: str
    subtitle: Optional[str]
    description: Optional[str]
    vip_plan_id: Optional[int] = Field(alias="vipPlanId")
    vip_plan: Optional[VipPlanInfo] = Field(alias="vipPlan")
    # SKU 相关字段（VIP 商品只有一个 SKU，取第一个）
    sku_id: Optional[int] = Field(alias="skuId")
    sku_name: Optional[str] = Field(alias="skuName")
    price: Optional[Any]
    original_price: Optional[Any] = Field(alias="originalPrice")
    is_published: bool = Field(alias="isPublished")
    sort: int
    created_at: Optional[str] = Field(alias="createdAt")
    updated_at: Optional[str] = Field(alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True

class PurchasedDesignProductItemRes(BaseModel):
    """用户已购买的设计作品商品项"""
    img_url: Optional[str] = None
    name: str
    product_id: Optional[int] = None
    design_id: Optional[int] = None

class ProductSimpleInfoRes(BaseModel):
    """商品简单信息（仅包含id、封面图片、名称）"""
    id: int = Field(description="商品ID")
    cover_image: Optional[str] = Field(None, description="商品封面图URL")
    name: str = Field(description="商品名称")

    class Config:
        from_attributes = True
