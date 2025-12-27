from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CategoryInfoRes(BaseModel):
    """分类信息响应"""
    id: int = Field(description="分类ID")
    name: str = Field(description="分类名称")
    parent_id: Optional[int] = Field(default=None, description="父级分类ID")
    top_parent_id: Optional[int] = Field(default=None, description="顶级父分类ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class CategoryTreeNodeRes(BaseModel):
    """分类树节点响应"""
    id: int = Field(description="分类ID")
    name: str = Field(description="分类名称")
    parent_id: Optional[int] = Field(default=None, description="父级分类ID")
    top_parent_id: Optional[int] = Field(default=None, description="顶级父分类ID")
    children: List['CategoryTreeNodeRes'] = Field(default_factory=list, description="子分类列表")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class SeriesInfoRes(BaseModel):
    """系列信息响应"""
    id: int = Field(description="系列ID")
    name: str = Field(description="系列名称")
    parent_id: Optional[int] = Field(default=None, description="父级系列ID")
    top_parent_id: Optional[int] = Field(default=None, description="顶级父系列ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class SeriesTreeNodeRes(BaseModel):
    """系列树节点响应"""
    id: int = Field(description="系列ID")
    name: str = Field(description="系列名称")
    parent_id: Optional[int] = Field(default=None, description="父级系列ID")
    top_parent_id: Optional[int] = Field(default=None, description="顶级父系列ID")
    children: List['SeriesTreeNodeRes'] = Field(default_factory=list, description="子系列列表")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        populate_by_name = True
        from_attributes = True

