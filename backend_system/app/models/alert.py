"""
告警模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class AlertType(str, enum.Enum):
    """告警类型枚举"""
    FIRE_VIOLATION = "fire_violation"
    SMOKE_VIOLATION = "smoke_violation"
    PPE_VIOLATION = "ppe_violation"
    DISTANCE_VIOLATION = "distance_violation"
    ACCESS_CONTROL = "access_control"


class AlertSeverity(str, enum.Enum):
    """告警严重程度枚举"""
    CRITICAL = "CRITICAL"
    DANGER = "DANGER"
    WARNING = "WARNING"


class Alert(Base):
    """告警表"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, index=True)
    message = Column(String(500))
    timestamp = Column(DateTime, nullable=False, index=True)  # 事件发生时间（由Edge提供）
    image_path = Column(String(512), nullable=True)  # 证据图片路径
    alert_metadata = Column(JSON, nullable=True)  # 元数据（如confidence, bbox等）
    is_acknowledged = Column(Boolean, default=False, nullable=False, index=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # 服务器记录创建时间
    
    # 关系
    device = relationship("Device", back_populates="alerts")
    acknowledged_by_user = relationship("User", back_populates="acknowledged_alerts", foreign_keys=[acknowledged_by])
