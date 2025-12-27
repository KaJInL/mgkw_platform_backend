# middleware/request_context.py
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class Ctx:
    """自定义请求上下文"""

    def __init__(self, request: Request, token: str | None = None):
        self.request = request
        self.token = token


_request_context: ContextVar[Ctx] = ContextVar("ctx")

def _create_ctx(request: Request) -> Ctx:
    """
    从 Request 创建 Ctx 对象
    - 提取 token（可按需扩展：用户、追踪ID等）
    """
    # 这里支持两种 token 头部格式，可根据项目调整
    auth_header = request.headers.get("Authorization") or request.headers.get("X-Token")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
    else:
        token = auth_header

    return Ctx(request=request, token=token)


class RequestContextMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        ctx = _create_ctx(request)  # ✅ 使用独立函数创建
        token = _request_context.set(ctx)
        try:
            response = await call_next(request)
        finally:
            _request_context.reset(token)
        return response


def get_ctx() -> Ctx:
    """获取当前请求上下文对象"""
    return _request_context.get()
