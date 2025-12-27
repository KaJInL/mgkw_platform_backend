from typing import Optional, List
from pydantic import BaseModel, Field
from application.common.schema import PaginationReq
from application.common.models.design import DesignState

class QueryDesignProductListReq(PaginationReq):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    state: Optional[DesignState] = Field(None, description="状态")

class AuditDesignProductReq(BaseModel):
    design_id: int = Field(..., description="设计作品ID" ,alias="designId")
    state: DesignState = Field(..., description="审核状态")
    remark: Optional[str] = Field(None, description="审核备注")

class GetDesignProductDetailReq(BaseModel):
    design_id: int = Field(..., description="设计作品ID",alias="designId")

class UpdateSkuReq(BaseModel):
    sku_id: int = Field(..., description="SKU ID", alias="skuId")
    price: float = Field(..., description="售价")

class QueryVipProductListReq(BaseModel):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[int] = Field(None, description="状态")

class CreateVipProductReq(BaseModel):
    name: str = Field(..., description="VIP商品名称")
    description: Optional[str] = Field(None, description="商品描述")
    price: float = Field(..., description="售价")
    duration: int = Field(..., description="有效期(天)")
    sort: Optional[int] = Field(0, description="排序")
    privileges: Optional[str] = Field(None, description="套餐权益富文本")

class UpdateVipProductReq(BaseModel):
    vip_product_id: int = Field(..., description="VIP商品ID", alias="vipProductId")
    name: Optional[str] = Field(None, description="VIP商品名称")
    description: Optional[str] = Field(None, description="商品描述")
    price: Optional[float] = Field(None, description="售价")
    duration: Optional[int] = Field(None, description="有效期(天)")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, description="状态")
    privileges: Optional[str] = Field(None, description="套餐权益富文本")
