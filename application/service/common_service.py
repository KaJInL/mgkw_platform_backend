import os
import shutil

from fastapi import UploadFile

from application import config
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.models.upload_file import UploadedFile
from application.service.account_service import account_service


class UploadFileService:

    async def handle_upload(self, file: UploadFile) -> str:
        # 获取登录的用户id
        login_user_info = await account_service.get_login_user_info()
        user_id = login_user_info.user.id

        file_ext = file.filename.split('.')[-1]
        category = UploadedFile.get_file_category(file_ext)

        if not category:
            raise HttpBusinessException(HttpErrorCodeEnum.FILE_TYPE_NOT_SUPPORTED)

        file_hash = UploadedFile.compute_file_hash(file)
        existing_file = await UploadedFile.get_or_none(file_hash=file_hash)

        if existing_file:
            return existing_file.url

        save_path = self._save_file(file, file_hash, category, file_ext)

        uploaded_file = await UploadedFile.create(
            filename=file.filename,
            file_type=category,
            file_hash=file_hash,
            file_path=save_path,
            user_id=user_id
        )

        return uploaded_file.url

    def _save_file(self, file: UploadFile, file_hash: str, category: str, file_ext: str) -> str:
        """
        保存文件到指定目录，并返回保存路径。
        """
        save_dir = os.path.join(config.upload.dir, category)
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{file_hash}.{file_ext}"
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return f"/{category}/{filename}"


upload_file_service = UploadFileService()
