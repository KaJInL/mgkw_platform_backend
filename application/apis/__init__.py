from fastapi import FastAPI, APIRouter

from application.common.config import config
from application.common.exception.handlers import register_exception_handlers


def register_routes(app: FastAPI):
    """
    注册路由
    :param app: fastapi对象
    """
    register_exception_handlers(app)

    # 注册路由
    api_route = APIRouter()
    from .account import account_router
    from .common import common_router
    from .user import user_router
    from .auth import auth_router
    from .category import category_router
    from .design import design_router
    from .product import product_router
    from .order import order_router
    from .payment import payment_router
    from .recommend import recommend_router

    # 先注册具体的业务路由
    api_route.include_router(account_router)
    api_route.include_router(user_router)
    api_route.include_router(auth_router)
    api_route.include_router(category_router)
    api_route.include_router(product_router)
    api_route.include_router(design_router)
    api_route.include_router(order_router)
    api_route.include_router(payment_router)
    api_route.include_router(recommend_router)
    # 最后注册通配符路由（避免匹配冲突）
    api_route.include_router(common_router)
    app.include_router(api_route, prefix=config.prefix)


__all__ = ["register_routes"]
