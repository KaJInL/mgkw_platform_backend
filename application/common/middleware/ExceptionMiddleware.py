import traceback

from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import Request

from application.common.helper import ResponseHelper
from application.core.logger_util import logger


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"❌ Exception {request.url.path} ==> {e}\n{traceback.format_exc()}")
            return ResponseHelper.error(message="服务器异常，请稍后重试")
