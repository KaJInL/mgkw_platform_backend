from typing import Annotated, Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field
from application.common.models.design import DesignState, LicenseType


class CreateDesignReq(BaseModel):
    """创建设计作品请求"""
    title: str = Field(description="作品标题", min_length=1, max_length=256)
    description: Optional[str] = Field(default=None, description="作品描述")
    detail: Optional[str] = Field(default=None, description="作品详情富文本")
    category_id: Annotated[Optional[int], Field(description="所属分类ID", validation_alias="categoryId", serialization_alias="categoryId")] = None
    series_id: Annotated[Optional[int], Field(description="所属系列ID", validation_alias="seriesId", serialization_alias="seriesId")] = None
    tags: List[str] = Field(default_factory=list, description="作品标签列表")
    images: List[str] = Field(default_factory=list, description="作品展示图片URL列表")
    model_3d_url: Annotated[Optional[str], Field(description="3D模型文件URL", validation_alias="model3DUrl", serialization_alias="model3DUrl")] = None
    resource_url: Annotated[Optional[str], Field(description="设计全部素材的URL链接", validation_alias="resourceUrl", serialization_alias="resourceUrl")] = None

    class Config:
        populate_by_name = True


class UpdateDesignReq(BaseModel):
    """更新设计作品请求"""
    design_id: Annotated[int, Field(description="作品ID", validation_alias="designId", serialization_alias="designId", gt=0)]
    title: Optional[str] = Field(default=None, description="作品标题", min_length=1, max_length=256)
    description: Optional[str] = Field(default=None, description="作品描述")
    detail: Optional[str] = Field(default=None, description="作品详情富文本")
    category_id: Annotated[Optional[int], Field(description="所属分类ID", validation_alias="categoryId", serialization_alias="categoryId")] = None
    series_id: Annotated[Optional[int], Field(description="所属系列ID", validation_alias="seriesId", serialization_alias="seriesId")] = None
    tags: Optional[List[str]] = Field(default=None, description="作品标签列表")
    price: Optional[Decimal] = Field(default=None, description="作品售价", ge=0)
    images: Optional[List[str]] = Field(default=None, description="作品展示图片URL列表")
    model_3d_url: Annotated[Optional[str], Field(description="3D模型文件URL", validation_alias="model3DUrl", serialization_alias="model3DUrl")] = None
    resource_url: Annotated[Optional[str], Field(description="设计全部素材的URL链接", validation_alias="resourceUrl", serialization_alias="resourceUrl")] = None

    class Config:
        populate_by_name = True


class DeleteDesignReq(BaseModel):
    """删除设计作品请求"""
    design_id: Annotated[int, Field(description="作品ID", validation_alias="designId", serialization_alias="designId", gt=0)]
    
    class Config:
        populate_by_name = True


class GetDesignDetailReq(BaseModel):
    """获取设计作品详情请求"""
    design_id: Annotated[int, Field(description="作品ID", validation_alias="designId", serialization_alias="designId", gt=0)]
    
    class Config:
        populate_by_name = True


class QueryMyDesignListReq(BaseModel):
    """查询我的设计作品列表请求"""
    page: int = Field(default=1, description="页码", ge=1)
    page_size: Annotated[int, Field(default=10, description="每页数量", validation_alias="pageSize", serialization_alias="pageSize", ge=1, le=100)]
    state: Optional[DesignState] = Field(default=None, description="作品状态筛选")
    keyword: Optional[str] = Field(default=None, description="搜索关键词（标题、描述）")
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class SearchDesignListReq(BaseModel):
    """搜索设计作品列表请求（公开接口）"""
    page: int = Field(default=1, description="页码", ge=1)
    page_size: Annotated[int, Field(default=10, description="每页数量", validation_alias="pageSize", serialization_alias="pageSize", ge=1, le=100)]
    keyword: Optional[str] = Field(default=None, description="搜索关键词（标题、描述）")
    category_id: Annotated[Optional[int], Field(description="分类ID筛选", validation_alias="categoryId", serialization_alias="categoryId")] = None
    series_id: Annotated[Optional[int], Field(description="系列ID筛选", validation_alias="seriesId", serialization_alias="seriesId")] = None
    is_official: Annotated[Optional[bool], Field(description="是否官方作品", validation_alias="isOfficial", serialization_alias="isOfficial")] = None
    min_price: Annotated[Optional[Decimal], Field(description="最低价格", validation_alias="minPrice", serialization_alias="minPrice", ge=0)] = None
    max_price: Annotated[Optional[Decimal], Field(description="最高价格", validation_alias="maxPrice", serialization_alias="maxPrice", ge=0)] = None
    tags: Optional[List[str]] = Field(default=None, description="标签列表（包含任意一个）")
    
    class Config:
        populate_by_name = True


class ChangeDesignStateReq(BaseModel):
    """修改作品状态请求"""
    design_id: Annotated[int, Field(description="作品ID", validation_alias="designId", serialization_alias="designId", gt=0)]
    state: DesignState = Field(description="新状态")
    
    class Config:
        populate_by_name = True
        use_enum_values = True


# ==================== 设计授权方案相关请求 ====================

class UpdateDesignLicensePlanReq(BaseModel):
    """更新设计授权方案请求"""
    id: int = Field(description="授权方案ID", gt=0)
    description: Optional[str] = Field(default=None, description="授权方案描述")
    base_price: Annotated[Optional[Decimal], Field(default=None, description="基础定价", validation_alias="basePrice", serialization_alias="basePrice", ge=0)]
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class DeleteDesignLicensePlanReq(BaseModel):
    """删除设计授权方案请求"""
    id: int = Field(description="授权方案ID", gt=0)
    
    class Config:
        populate_by_name = True


class GetDesignLicensePlanDetailReq(BaseModel):
    """获取设计授权方案详情请求"""
    id: int = Field(description="授权方案ID", gt=0)
    
    class Config:
        populate_by_name = True


class QueryDesignLicensePlanListReq(BaseModel):
    """查询设计授权方案列表请求"""
    page: int = Field(default=1, description="页码", ge=1)
    page_size: Annotated[int, Field(default=10, description="每页数量", validation_alias="pageSize", serialization_alias="pageSize", ge=1, le=100)] 
    license_type: Annotated[Optional[LicenseType], Field(default=None, description="授权类型筛选", validation_alias="licenseType", serialization_alias="licenseType")] 
    description: Optional[str] = Field(default=None, description="授权方案描述")
    
    class Config:
        populate_by_name = True
        use_enum_values = True

