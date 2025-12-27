from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from application.common.config import config


class ReplaceResponseMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.exclude_paths = ["/mgkw/common/file/upload"]

    async def dispatch(self, request: Request, call_next):
        # 如果请求路径在排除列表中，直接返回原始响应
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # 获取原始响应
        original_response = await call_next(request)

        # 获取 content-type
        content_type = original_response.headers.get("content-type", "")

        if content_type.startswith("application/json") or content_type.startswith("text/"):
            # 读取响应体内容
            body = b""
            async for chunk in original_response.body_iterator:
                body += chunk

            # 替换内容
            url_mapping = [
                (b"https://mac.kajlee.com/mgkw", config.base_url.encode()),
                (b"http://100.64.0.22:5001/mgkw", config.base_url.encode()),
                (b"http://100.64.0.16:5001/mgkw", config.base_url.encode()),
            ]

            # 使用循环进行替换
            new_body = body
            for old_url, new_url in url_mapping:
                new_body = new_body.replace(old_url, new_url)

            # 拷贝 header，但移除 content-length
            headers = dict(original_response.headers)
            headers.pop("content-length", None)

            # 返回新的响应
            return Response(
                content=new_body,
                status_code=original_response.status_code,
                headers=headers,
                media_type=original_response.media_type,
            )

        # 非文本/JSON响应，直接返回
        return original_response
