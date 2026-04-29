"""
人脸图片存储服务：负责人脸图片的保存与路径管理
"""
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from app.core.config import settings


class FaceStorageService:
    """人脸库文件存储"""

    def __init__(self):
        self.base_dir = Path(settings.FACE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = settings.MAX_UPLOAD_SIZE

    def _person_dir(self, person_name: str) -> Path:
        """获取或创建人员目录（按人名分目录，与本地 face_db 结构一致）"""
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in person_name).strip() or "unknown"
        d = self.base_dir / safe_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def save_face_image(self, file: UploadFile, person_name: str) -> str:
        """
        保存人脸图片，返回相对路径（用于存入数据库）。
        相对路径相对于 FACE_DIR，例如: 张三/abc123.jpg
        """
        file_content = await file.read()
        if len(file_content) > self.max_size:
            raise ValueError(f"文件大小超过限制（最大{self.max_size}字节）")
        if not file.content_type or not file.content_type.startswith("image/"):
            raise ValueError("文件必须是图片格式")

        person_dir = self._person_dir(person_name)
        ext = Path(file.filename).suffix if file.filename else ".jpg"
        if not ext:
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = person_dir / filename
        file_path.write_bytes(file_content)
        # 相对路径：人员名/文件名
        relative = f"{person_dir.name}/{filename}"
        return relative

    def get_absolute_path(self, relative_path: str) -> Path:
        """根据数据库中的相对路径得到本地绝对路径"""
        return self.base_dir / relative_path


face_storage_service = FaceStorageService()
