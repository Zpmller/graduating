"""
人脸库 API 的 Pydantic 模型
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FaceRecordResponse(BaseModel):
    """单条人脸记录"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    person_name: str
    file_path: str
    created_at: datetime


class FaceListResponse(BaseModel):
    """人脸列表（用于 Edge 同步）"""
    total: int
    items: list[FaceRecordResponse]
