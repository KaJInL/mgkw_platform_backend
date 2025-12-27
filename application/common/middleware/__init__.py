from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from application.common.middleware.ExceptionMiddleware import ExceptionMiddleware
from application.common.middleware.RequestContextMiddleware import RequestContextMiddleware
from .ReplaceResponseMiddleware import ReplaceResponseMiddleware


def register_middleware(app: FastAPI):
    """
    中间件注册
    """
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(ExceptionMiddleware)
    app.add_middleware(ReplaceResponseMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
