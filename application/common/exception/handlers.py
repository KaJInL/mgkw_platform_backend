import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from tortoise.exceptions import IntegrityError

from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.helper import ResponseHelper
from application.core.logger_util import logger


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(HttpBusinessException)
    async def business_exception_handler(request: Request, exc: HttpBusinessException):
        logger.error(f"❌ 业务异常 url: {request.url.path} ==> {exc.message}\n堆栈信息:\n{traceback.format_exc()}")
        return ResponseHelper.error(code=exc.code, message=exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        """
        处理参数校验异常，提取具体的错误信息
        """
        logger.error(f"❌ 参数校验错误 url: {request.url.path} ==> {exc}\n堆栈信息:\n{traceback.format_exc()}")
        
        # 提取第一个错误信息
        error_messages = []
        for error in exc.errors():
            # 获取字段位置
            loc = error.get('loc', ())
            # 跳过 'body' 前缀，只显示实际字段名
            field = '.'.join(str(l) for l in loc if l != 'body')
            
            # 获取错误类型和消息
            error_type = error.get('type', '')
            msg = error.get('msg', '')
            
            # 自定义错误消息（针对 ValidationUtils 的错误）
            if error_type == 'value_error':
                # 这是我们自定义的 ValueError，直接使用其消息
                error_messages.append(msg)
            elif error_type == 'missing':
                error_messages.append(f"缺少必填字段: {field}")
            elif error_type == 'string_type':
                error_messages.append(f"字段 {field} 必须是字符串类型")
            elif error_type == 'int_type':
                error_messages.append(f"字段 {field} 必须是整数类型")
            elif error_type == 'string_too_short':
                error_messages.append(f"字段 {field} 长度太短")
            elif error_type == 'string_too_long':
                error_messages.append(f"字段 {field} 长度太长")
            else:
                # 使用原始消息
                if field:
                    error_messages.append(f"{field}: {msg}")
                else:
                    error_messages.append(msg)
        
        # 返回第一个错误消息，如果没有则使用默认消息
        error_message = error_messages[0] if error_messages else "参数校验错误"
        
        return ResponseHelper.error(
            code=HttpErrorCodeEnum.PARAM_EMPTY.code,
            message=error_message
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request, exc: IntegrityError):
        logger.error(f"❌ 数据重复 url: {request.url.path} ==> {exc}\n堆栈信息:\n{traceback.format_exc()}")
        return ResponseHelper.error_with_error_code(HttpErrorCodeEnum.DATA_DUPLICATE)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc: Exception):
        logger.error(f"❌ 系统错误 url: {request.url.path} ==> {exc}\n异常类型: {type(exc).__name__}\n堆栈信息:\n{traceback.format_exc()}")
        return ResponseHelper.error()

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        logger.error(f"❌ KeyError 异常 url: {request.url.path} ==> {exc}\n堆栈信息:\n{traceback.format_exc()}")
        return ResponseHelper.error()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # 处理HTTP方法错误 (405 Method Not Allowed)
        if exc.status_code == 405:
            logger.error(f"❌ HTTP方法错误 url: {request.url.path} ==> {exc.detail}\n堆栈信息:\n{traceback.format_exc()}")
            return ResponseHelper.error_with_error_code(HttpErrorCodeEnum.METHOD_NOT_ALLOWED)
        # 其他HTTP异常继续抛出
        logger.error(f"❌ HTTP异常 url: {request.url.path} ==> {exc.detail}\nHTTP状态码: {exc.status_code}\n堆栈信息:\n{traceback.format_exc()}")
        return ResponseHelper.error()
