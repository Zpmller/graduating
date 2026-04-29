"""
设备模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text  # 添加 Text
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class DeviceStatus(str, enum.Enum):
    """设备状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class Device(Base):
    """设备表"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    location = Column(String(255))
    ip_address = Column(String(512))  # 视频源地址（RTSP/HTTP/摄像头URL等）
    edge_host = Column(String(255), nullable=True, index=True)  # Edge 节点所在主机 IP/主机名，用于零配置发现与通知
    device_token = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.OFFLINE, nullable=False)
    last_heartbeat = Column(DateTime, nullable=True)
    calibration_config = Column(Text, nullable=True)  # 存储YAML配置内容
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系：设备产生的告警
    alerts = relationship("Alert", back_populates="device")