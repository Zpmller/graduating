"""
人脸库模型：存储授权人员人脸图片信息
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base


class FaceRecord(Base):
    """人脸记录表：person_name 对应本地 face_db 下的子目录名/授权人员名"""
    __tablename__ = "face_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    person_name = Column(String(100), nullable=False, index=True)  # 授权人员姓名/标识
    file_path = Column(String(255), nullable=False)  # 相对路径，如 faces/张三/xxx.jpg
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
