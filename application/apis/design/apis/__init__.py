from fastapi import APIRouter

from application.apis.design.apis.designer_admin_api import designer_admin_router
from application.apis.design.apis.design_admin_api import design_admin_router



design_router = APIRouter()
design_router.include_router(designer_admin_router)
design_router.include_router(design_admin_router)

__all__ = [
    "design_router",
]