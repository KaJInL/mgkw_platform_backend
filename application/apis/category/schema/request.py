from typing import Optional
from pydantic import BaseModel, Field


# ==================== 分类请求 ====================

class QueryCategoryListReq(BaseModel):
    """查询分类列表请求"""
    keyword: Optional[str] = Field(default=None, description="搜索关键词（分类名称）")
    parent_id: Optional[int] = Field(default=None, description="父级分类ID", alias="parentId")
    
    class Config:
        populate_by_name = True


class CreateCategoryReq(BaseModel):
    """新增分类请求"""
    name: str = Field(description="分类名称", min_length=1, max_length=128)
    parent_id: Optional[int] = Field(default=None, description="父级分类ID", alias="parentId")
    
    class Config:
        populate_by_name = True


class UpdateCategoryReq(BaseModel):
    """修改分类信息请求"""
    category_id: int = Field(description="分类ID", alias="categoryId", gt=0)
    name: Optional[str] = Field(default=None, description="分类名称", min_length=1, max_length=128)
    parent_id: Optional[int] = Field(default=None, description="父级分类ID", alias="parentId")
    
    class Config:
        populate_by_name = True


class DeleteCategoryReq(BaseModel):
    """删除分类请求"""
    category_id: int = Field(description="分类ID", alias="categoryId", gt=0)
    recursive: bool = Field(default=False, description="是否递归删除子分类")
    
    class Config:
        populate_by_name = True


class GetCategoryDetailReq(BaseModel):
    """获取分类详情请求"""
    category_id: int = Field(description="分类ID", alias="categoryId", gt=0)
    
    class Config:
        populate_by_name = True


class GetCategoryTreeReq(BaseModel):
    """获取分类树请求"""
    parent_id: Optional[int] = Field(default=None, description="父级分类ID，为空则获取完整树", alias="parentId")
    max_depth: Optional[int] = Field(default=None, description="最大深度限制", alias="maxDepth", ge=1)
    
    class Config:
        populate_by_name = True


class GetCategoryChildrenReq(BaseModel):
    """获取子分类请求"""
    parent_id: int = Field(description="父级分类ID", alias="parentId", gt=0)
    recursive: bool = Field(default=False, description="是否递归获取所有后代")
    
    class Config:
        populate_by_name = True


class GetCategoryPathReq(BaseModel):
    """获取分类路径请求"""
    category_id: int = Field(description="分类ID", alias="categoryId", gt=0)
    
    class Config:
        populate_by_name = True


# ==================== 系列请求 ====================

class QuerySeriesListReq(BaseModel):
    """查询系列列表请求"""
    keyword: Optional[str] = Field(default=None, description="搜索关键词（系列名称）")
    parent_id: Optional[int] = Field(default=None, description="父级系列ID", alias="parentId")
    
    class Config:
        populate_by_name = True


class CreateSeriesReq(BaseModel):
    """新增系列请求"""
    name: str = Field(description="系列名称", min_length=1, max_length=128)
    parent_id: Optional[int] = Field(default=None, description="父级系列ID", alias="parentId")
    
    class Config:
        populate_by_name = True


class UpdateSeriesReq(BaseModel):
    """修改系列信息请求"""
    series_id: int = Field(description="系列ID", alias="seriesId", gt=0)
    name: Optional[str] = Field(default=None, description="系列名称", min_length=1, max_length=128)
    parent_id: Optional[int] = Field(default=None, description="父级系列ID", alias="parentId")
    
    class Config:
        populate_by_name = True


class DeleteSeriesReq(BaseModel):
    """删除系列请求"""
    series_id: int = Field(description="系列ID", alias="seriesId", gt=0)
    recursive: bool = Field(default=False, description="是否递归删除子系列")
    
    class Config:
        populate_by_name = True


class GetSeriesDetailReq(BaseModel):
    """获取系列详情请求"""
    series_id: int = Field(description="系列ID", alias="seriesId", gt=0)
    
    class Config:
        populate_by_name = True


class GetSeriesTreeReq(BaseModel):
    """获取系列树请求"""
    parent_id: Optional[int] = Field(default=None, description="父级系列ID，为空则获取完整树", alias="parentId")
    max_depth: Optional[int] = Field(default=None, description="最大深度限制", alias="maxDepth", ge=1)
    
    class Config:
        populate_by_name = True


class GetSeriesChildrenReq(BaseModel):
    """获取子系列请求"""
    parent_id: int = Field(description="父级系列ID", alias="parentId", gt=0)
    recursive: bool = Field(default=False, description="是否递归获取所有后代")
    
    class Config:
        populate_by_name = True


class GetSeriesPathReq(BaseModel):
    """获取系列路径请求"""
    series_id: int = Field(description="系列ID", alias="seriesId", gt=0)
    
    class Config:
        populate_by_name = True

