import hashlib
import os
from enum import Enum

from tortoise import fields

from application.common.config import config
from application.common.models import DefaultModel


class UploadedFile(DefaultModel):
    class FileType(str, Enum):
        IMG = "img"
        VIDEO = "video"
        DOCX = "docx"
        EXCEL = "excel"
        PDF = "pdf"
        MODEL = "model"

    filename = fields.CharField(max_length=255, description="文件名")
    file_type = fields.CharEnumField(FileType, max_length=50, description="文件类型")
    file_hash = fields.CharField(max_length=64, unique=True, description="文件 hash")
    file_path = fields.TextField(description="文件路径")
    user_id = fields.IntField(null=True, description="用户 id")

    class Meta:
        table = "uploaded_files"
        table_description = "文件上传表"

    @property
    def url(self) -> str:
        """
        构建文件的访问 URL
        """
        return f"{config.base_url}/media/{self.file_type.value}/{os.path.basename(self.file_path)}"

    @staticmethod
    def compute_file_hash(upload_file) -> str:
        hasher = hashlib.sha256()
        contents = upload_file.file.read()
        hasher.update(contents)
        upload_file.file.seek(0)
        return hasher.hexdigest()

    @classmethod
    def get_file_category(cls, extension: str) -> str | None:
        ext = extension.lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif']:  # 图片
            return cls.FileType.IMG.value
        elif ext in ['mp4', 'mov', 'avi']:  # 视频
            return cls.FileType.VIDEO.value
        elif ext in ['docx', 'doc']:  # 文档
            return cls.FileType.DOCX.value
        elif ext in ['xlsx']:  # 表格
            return cls.FileType.EXCEL.value
        elif ext in ['pdf']:  # pdf
            return cls.FileType.PDF.value
        elif ext in ['glb', 'gltf', 'obj', 'fbx', 'dae', '3ds', 'blend', 'max', 'c4d', 'stl', 'ply']:  # 3D模型文件
            return cls.FileType.MODEL.value
        return None
