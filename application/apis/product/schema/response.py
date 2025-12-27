from typing import List, Optional, Any
from pydantic import BaseModel
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
    bg_image_url: Optional[str]

class VipProductInfoRes(BaseModel):
    id: int
    name: str
    subtitle: Optional[str]
    description: Optional[str]
    vip_plan_id: Optional[int]
    vip_plan: Optional[VipPlanInfo]
    is_published: bool
    sort: int
    created_at: Optional[str]
    updated_at: Optional[str]
