"""
文件存储服务：处理证据图片的上传和存储
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from app.core.config import settings


class FileStorageService:
    """文件存储服务"""
    
    def __init__(self):
        self.base_dir = Path(settings.EVIDENCE_DIR)
        self.max_size = settings.MAX_UPLOAD_SIZE
    
    def _ensure_directory(self, date_str: str):
        """确保目录存在"""
        date_dir = self.base_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    async def save_evidence_image(
        self,
        file: UploadFile,
        date_str: Optional[str] = None
    ) -> str:
        """
        保存证据图片
        
        Args:
            file: 上传的文件
            date_str: 日期字符串（YYYY-MM-DD），如果为None则使用当前日期
        
        Returns:
            相对路径字符串（用于存储到数据库）
        """
        # 检查文件大小
        file_content = await file.read()
        if len(file_content) > self.max_size:
            raise ValueError(f"文件大小超过限制（最大{self.max_size}字节）")
        
        # 检查文件类型
        if not file.content_type or not file.content_type.startswith("image/"):
            raise ValueError("文件必须是图片格式")
        
        # 确定日期目录
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # 确保目录存在
        date_dir = self._ensure_directory(date_str)
        
        # 生成唯一文件名
        file_ext = Path(file.filename).suffix if file.filename else ".jpg"
        if not file_ext:
            file_ext = ".jpg"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # 保存文件
        file_path = date_dir / unique_filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 返回相对路径（用于数据库存储）
        relative_path = f"{date_str}/{unique_filename}"
        return relative_path
    
    def get_image_url(self, image_path: str) -> str:
        """
        获取图片URL
        
        Args:
            image_path: 数据库中的相对路径
        
        Returns:
            完整的URL路径
        """
        return f"/static/evidence/{image_path}"


# 创建单例
file_storage_service = FileStorageService()
