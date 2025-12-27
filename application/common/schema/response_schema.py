"""
通用响应模型，用于 Swagger 文档生成

这个模块定义了 FastAPI 接口的标准响应格式，包括：
- BaseResponse: 基础响应模型（支持泛型数据）
- PaginationData: 分页数据模型
- PaginationResponse: 分页响应模型
- ErrorResponse: 错误响应模型
- 常用的具体响应类型（Bool/String/Int/Dict）
"""
from typing import TypeVar, Generic, Optional, Any, List, Dict
from pydantic import BaseModel, Field


T = TypeVar('T')


# ============================================================================
# 基础响应模型
# ============================================================================

class BaseResponse(BaseModel, Generic[T]):
    """
    基础响应模型
    
    用于包装 API 响应，所有接口都应该返回此格式
    """
    code: str = Field(default="0", description="响应码，0表示成功")
    isSuccess: bool = Field(default=True, description="是否成功")
    message: str = Field(default="成功", description="响应消息")
    data: Optional[T] = Field(default_factory=dict, description="响应数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "0",
                "isSuccess": True,
                "message": "成功",
                "data": None
            }
        }


class ErrorResponse(BaseModel):
    """
    错误响应模型
    
    用于 Swagger 文档展示错误情况
    """
    code: str = Field(description="错误码")
    isSuccess: bool = Field(default=False, description="是否成功，固定为 False")
    message: str = Field(description="错误消息")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "500",
                "isSuccess": False,
                "message": "系统错误"
            }
        }


# ============================================================================
# 分页相关模型
# ============================================================================

class PaginationData(BaseModel, Generic[T]):
    """
    分页数据模型
    
    用于包装分页列表数据
    """
    list: List[T] = Field(description="数据列表")
    total: int = Field(description="总数据条数")
    hasNext: bool = Field(description="是否有下一页")

    class Config:
        json_schema_extra = {
            "example": {
                "list": [],
                "total": 0,
                "hasNext": False
            }
        }


class PaginationResponse(BaseModel, Generic[T]):
    """
    分页响应模型
    
    用于包装分页查询的 API 响应
    """
    code: str = Field(default="0", description="响应码，0表示成功")
    isSuccess: bool = Field(default=True, description="是否成功")
    message: str = Field(default="成功", description="响应消息")
    data: Optional[PaginationData[T]] = Field(default=None, description="分页数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "0",
                "isSuccess": True,
                "message": "成功",
                "data": {
                    "list": [],
                    "total": 0,
                    "hasNext": False
                }
            }
        }


# ============================================================================
# 运行时分页结果类
# ============================================================================

class PaginationResult(Generic[T]):
    """
    分页结果类，用于运行时封装分页数据
    
    注意：这是运行时使用的类，不是 Pydantic 模型
    主要用于在 Service 层返回分页数据
    """
    def __init__(self, list: List[T], total: int, has_next: bool):
        self.list = list
        self.total = total
        self.has_next = has_next

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        from application.common.base.base_model import DefaultModel
        return {
            "list": [item.to_dict() if isinstance(item, DefaultModel) else item for item in self.list],
            "total": self.total,
            "hasNext": self.has_next
        }


# 常用的具体响应类型
class BoolDataModel(BaseModel):
    """布尔值数据模型"""
    value: bool = Field(description="布尔值")


class StringDataModel(BaseModel):
    """字符串数据模型"""
    value: str = Field(description="字符串值")


class IntDataModel(BaseModel):
    """整数数据模型"""
    value: int = Field(description="整数值")


class DictDataModel(BaseModel):
    """字典数据模型 - 用于动态数据"""
    class Config:
        extra = "allow"  # 允许额外字段


# 预定义的常用响应类型
BoolResponse = BaseResponse[BoolDataModel]
StringResponse = BaseResponse[StringDataModel]
IntResponse = BaseResponse[IntDataModel]
DictResponse = BaseResponse[DictDataModel]

