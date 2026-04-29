"""
设备相关Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.device import DeviceStatus


class DeviceBase(BaseModel):
    """设备基础Schema"""
    name: str
    location: Optional[str] = None
    ip_address: Optional[str] = None
    edge_host: Optional[str] = None  # Edge 节点主机 IP/主机名，用于零配置发现


class DeviceCreate(DeviceBase):
    """创建设备Schema"""
    pass


class DeviceUpdate(BaseModel):
    """更新设备Schema"""
    name: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    edge_host: Optional[str] = None
    status: Optional[DeviceStatus] = None


    edge_host: Optional[str] = None
class DeviceResponse(DeviceBase):
    """设备响应Schema"""
    id: int
    device_token: str
    status: DeviceStatus
    last_heartbeat: Optional[datetime] = None
    calibration_config: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DeviceStreamStatus(BaseModel):
    """设备流状态（内嵌于设备列表）"""
    is_active: bool
    stream_id: Optional[str] = None
    quality: Optional[str] = None
    connection_state: str


class DeviceResponseWithStream(DeviceResponse):
    """设备响应（含流状态，供前端展示）"""
    stream_status: Optional[DeviceStreamStatus] = None


class DeviceListResponse(BaseModel):
    """设备列表响应"""
    items: list[DeviceResponse]
    total: int
    skip: int
    limit: int


class DeviceListWithStreamResponse(BaseModel):
    """设备列表响应（含各设备流状态）"""
    items: list[DeviceResponseWithStream]
    total: int
    skip: int
    limit: int


class HeartbeatResponse(BaseModel):
    """心跳响应"""
    status: str = "ok"
    last_heartbeat: datetime


class DeviceBootstrapResponse(BaseModel):
    """Edge 零配置引导响应"""
    id: int
    name: str
    location: Optional[str] = None
    ip_address: Optional[str] = None
    edge_host: Optional[str] = None
    device_token: str
    
    model_config = ConfigDict(from_attributes=True)