from typing import Optional, List, Annotated
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field
from application.common.models.design import DesignState, LicenseType


class DesignInfoRes(BaseModel):
    """设计作品信息响应"""
    id: int = Field(description="作品ID")
    user_id: int = Field(description="设计师用户ID")
    title: str = Field(description="作品标题")
    description: Optional[str] = Field(default=None, description="作品描述")
    detail: Optional[str] = Field(default=None, description="作品详情富文本")
    category_id: Optional[int] = Field(default=None, description="所属分类ID")
    series_id: Optional[int] = Field(default=None, description="所属系列ID")
    tags: List[str] = Field(default=[], description="作品标签列表")
    images: List[str] = Field(default=[], description="作品展示图片URL列表")
    is_official: str = Field(description="是否为官方设计")
    model_3d_url: Optional[str] = Field(default=None, description="3D模型文件URL")
    resource_url: Optional[str] = Field(default=None, description="设计全部素材的URL链接")
    state: DesignState = Field(description="作品状态")
    is_deleted: str = Field(description="是否已删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class DesignLicensePlanInfoRes(BaseModel):
    """设计授权方案信息响应"""
    id: int = Field(description="授权方案ID")
    license_type: LicenseType = Field(description="授权类型")
    description: Optional[str] = Field(default=None, description="授权方案描述")
    base_price: Annotated[Optional[Decimal], Field(default=None, description="基础定价", serialization_alias="basePrice")]
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        from_attributes = True
        use_enum_values = True

