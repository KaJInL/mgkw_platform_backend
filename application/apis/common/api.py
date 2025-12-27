import asyncio
import os
import time
from datetime import datetime
from pathlib import Path

import redis_lock
from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.responses import FileResponse

from application import config
from application.common.helper import ResponseHelper
from application.core.redis_client import redis_client
from application.service.common_service import upload_file_service
from application.apis.common.dashboard_admin_service import dashboard_admin_service
from application.apis.common.schema.response import DashboardStatsRes
from application.common.schema import BaseResponse

common = APIRouter(tags=["通用接口"])


@common.post("/common/file/upload", summary="文件上传")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件
    :return: 文件访问URL
    """
    url = await upload_file_service.handle_upload(file)
    return ResponseHelper.success({"url": url})


@common.get(
    "/admin/dashboard/stats",
    summary="获取首页统计数据",
    description="获取首页展示的统计数据，包括用户数、商品数、设计作品数、订单数等",
    response_model=BaseResponse[DashboardStatsRes],
)
async def get_dashboard_stats():
    """
    获取首页统计数据
    """
    result = await dashboard_admin_service.get_dashboard_stats()
    return ResponseHelper.success(result)


UPLOAD_DIR = os.path.join(config.upload.dir)


def _get_media_file(media_type: str, filename: str):
    """
    获取媒体文件的内部函数
    """
    # 支持的媒体类型
    allowed_types = ("img", "video", "model", "docx", "excel", "pdf")
    if media_type not in allowed_types:
        raise HTTPException(status_code=404, detail="Media type not found")

    file_path = Path(UPLOAD_DIR) / media_type / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # 根据文件类型设置合适的Content-Type
    media_type_mapping = {
        "img": "image/*",
        "video": "video/*",
        "model": "application/octet-stream",  # 3D模型文件
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"
    }

    return FileResponse(
        path=str(file_path),
        media_type=media_type_mapping.get(media_type, "application/octet-stream")
    )


@common.get("/media/{media_type}/{filename}")
async def get_media(media_type: str, filename: str):
    """
    获取媒体文件（新路径）
    """
    return _get_media_file(media_type, filename)