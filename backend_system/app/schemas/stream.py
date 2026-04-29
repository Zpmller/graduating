"""
视频流相关Schema
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class StreamOfferRequest(BaseModel):
    """请求流offer"""
    quality: Optional[Literal["low", "medium", "high"]] = Field(default="medium", description="流质量")


class StreamOfferResponse(BaseModel):
    """流 offer 响应（WHEP 模式）"""
    stream_id: str = Field(description="流ID")
    whep_url: str = Field(description="WHEP 播放 URL，前端 POST SDP offer 获取 answer")
    sdp: Optional[str] = Field(default=None, description="兼容字段，WHEP 模式下为空")
    type: Literal["offer"] = "offer"
    websocket_url: Optional[str] = Field(default=None, description="兼容字段，WHEP 模式下为空")


class StreamAnswerRequest(BaseModel):
    """流answer请求"""
    stream_id: str = Field(description="流ID")
    sdp: str = Field(description="WebRTC SDP answer")
    type: Literal["answer"] = "answer"


class StreamAnswerResponse(BaseModel):
    """流answer响应"""
    status: str = Field(default="connected", description="连接状态")
    stream_id: str = Field(description="流ID")


class StreamStatusResponse(BaseModel):
    """流状态响应"""
    device_id: int
    is_active: bool
    stream_id: Optional[str] = None
    quality: Optional[Literal["low", "medium", "high"]] = None
    detection_overlay_enabled: bool = False
    connection_state: Literal["connecting", "connected", "disconnected", "failed"] = "disconnected"
    error: Optional[str] = None


class StreamControlRequest(BaseModel):
    """流控制请求"""
    action: Literal["start", "stop", "toggle_overlay", "set_quality"] = Field(description="控制动作")
    enable_overlay: Optional[bool] = Field(None, description="启用覆盖层（用于toggle_overlay）")
    quality: Optional[Literal["low", "medium", "high"]] = Field(None, description="流质量（用于set_quality）")


class StreamStopResponse(BaseModel):
    """停止流响应"""
    status: str = Field(default="stopped", description="状态")
    stream_id: str = Field(description="流ID")
