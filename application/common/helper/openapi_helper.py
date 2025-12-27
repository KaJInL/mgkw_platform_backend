"""
OpenAPI/Swagger 文档辅助函数
用于自定义 API 路由的响应文档
"""
from typing import Dict, Any, List, Optional, Type, TypeVar
from pydantic import BaseModel

from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.schema import BaseResponse, ErrorResponse

T = TypeVar('T', bound=BaseModel)


def generate_responses(
    success_model: Optional[Type[BaseModel]] = None,
    error_codes: Optional[List[HttpErrorCodeEnum]] = None,
    include_default_errors: bool = True,
    hide_422: bool = True
) -> Dict[int, Dict[str, Any]]:
    """
    生成 FastAPI 路由的 responses 参数,用于 Swagger 文档
    
    :param success_model: 成功响应的数据模型 (如 BaseResponse[SysConfResponse])
    :param error_codes: 可能返回的错误码列表 (来自 HttpErrorCodeEnum)
    :param include_default_errors: 是否包含默认错误 (ERROR, PARAM_EMPTY)
    :param hide_422: 是否隐藏 422 验证错误响应
    :return: responses 字典,可直接用于路由装饰器
    
    使用示例:
    ```python
    @admin.post(
        "/admin/sys_conf/create",
        summary="创建系统配置",
        response_model=BaseResponse[SysConfResponse],
        responses=generate_responses(
            success_model=BaseResponse[SysConfResponse],
            error_codes=[HttpErrorCodeEnum.DATA_DUPLICATE]
        )
    )
    ```
    """
    responses: Dict[int, Dict[str, Any]] = {}
    
    # 添加 200 成功响应
    if success_model:
        responses[200] = {
            "description": "成功",
            "model": success_model
        }
    
    # 收集所有错误码
    all_error_codes: List[HttpErrorCodeEnum] = []
    
    if include_default_errors:
        # 默认包含通用错误
        all_error_codes.extend([
            HttpErrorCodeEnum.ERROR,
            HttpErrorCodeEnum.PARAM_EMPTY
        ])
    
    if error_codes:
        # 添加自定义错误码
        all_error_codes.extend(error_codes)
    
    # 为每个错误码生成文档 (所有业务错误都返回 HTTP 200)
    if all_error_codes:
        error_examples = {}
        for error_code in all_error_codes:
            error_examples[error_code.code] = {
                "summary": error_code.message,
                "value": {
                    "code": error_code.code,
                    "isSuccess": False,
                    "message": error_code.message
                }
            }
        
        responses[200]["content"] = {
            "application/json": {
                "examples": error_examples
            }
        }
    
    # 隐藏 422 验证错误
    if hide_422:
        responses[422] = {"model": None}
    
    return responses


def generate_simple_responses(
    error_codes: Optional[List[HttpErrorCodeEnum]] = None,
    hide_422: bool = True
) -> Dict[int, Dict[str, Any]]:
    """
    生成简化的 responses,只包含错误码,不指定 success_model
    适用于已经在装饰器中定义了 response_model 的情况
    
    :param error_codes: 可能返回的错误码列表
    :param hide_422: 是否隐藏 422 验证错误响应
    :return: responses 字典
    
    使用示例:
    ```python
    @admin.post(
        "/admin/sys_conf/create",
        summary="创建系统配置",
        response_model=BaseResponse[SysConfResponse],
        responses=generate_simple_responses(
            error_codes=[HttpErrorCodeEnum.DATA_DUPLICATE]
        )
    )
    ```
    """
    responses: Dict[int, Dict[str, Any]] = {}
    
    # 收集所有错误码
    all_error_codes: List[HttpErrorCodeEnum] = [
        HttpErrorCodeEnum.ERROR,
        HttpErrorCodeEnum.PARAM_EMPTY
    ]
    
    if error_codes:
        all_error_codes.extend(error_codes)
    
    # 生成错误码示例
    error_examples = {}
    for error_code in all_error_codes:
        error_examples[error_code.code] = {
            "summary": error_code.message,
            "value": {
                "code": error_code.code,
                "isSuccess": False,
                "message": error_code.message
            }
        }
    
    responses[200] = {
        "description": "响应说明",
        "content": {
            "application/json": {
                "examples": error_examples
            }
        }
    }
    
    # 隐藏 422 验证错误
    if hide_422:
        responses[422] = {"model": None}
    
    return responses


def error_response_example(
    error_code: HttpErrorCodeEnum,
    custom_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成单个错误响应示例
    
    :param error_code: 错误码枚举
    :param custom_message: 自定义错误消息 (可选,默认使用枚举中的消息)
    :return: 错误响应示例字典
    """
    return {
        "code": error_code.code,
        "isSuccess": False,
        "message": custom_message or error_code.message
    }

