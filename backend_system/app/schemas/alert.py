"""
告警相关Schema
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.alert import AlertType, AlertSeverity


class AlertCreate(BaseModel):
    """创建告警Schema（Edge Node使用）"""
    type: AlertType
    level: AlertSeverity = Field(..., description="告警级别，对应severity字段")
    message: str = Field(..., max_length=500)
    timestamp: float = Field(..., description="Unix时间戳")
    metadata: Optional[dict[str, Any]] = Field(None, description="元数据（如confidence, bbox等）")


class AlertResponse(BaseModel):
    """告警响应Schema"""
    id: int
    device_id: int
    device_name: Optional[str] = None
    type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    image_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    is_acknowledged: bool
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_orm_with_mapping(cls, obj):
        """
        从ORM对象创建响应，自动将alert_metadata映射为metadata
        
        这样可以保持API字段名为metadata（符合文档），
        同时数据库字段名为alert_metadata（避免SQLAlchemy冲突）
        """
        data = {
            **{k: v for k, v in obj.__dict__.items() if not k.startswith('_')},
            "metadata": getattr(obj, "alert_metadata", None)
        }
        # 移除alert_metadata，避免重复
        data.pop("alert_metadata", None)
        return cls.model_validate(data)


class AlertListResponse(BaseModel):
    """告警列表响应"""
    items: list[AlertResponse]
    total: int
    skip: int
    limit: int


class AlertStatsResponse(BaseModel):
    """告警统计响应"""
    total_alerts: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    unacknowledged_count: int
    trend_24h: list[dict[str, Any]]


class AlertAcknowledgeRequest(BaseModel):
    """确认告警请求"""
    notes: Optional[str] = None
