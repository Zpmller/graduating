"""
视频流API端点
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query

logger = logging.getLogger(__name__)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.device import Device, DeviceStatus
from app.schemas.stream import (
    StreamOfferRequest,
    StreamOfferResponse,
    StreamAnswerRequest,
    StreamAnswerResponse,
    StreamStatusResponse,
    StreamControlRequest,
    StreamStopResponse
)
from app.api.deps import get_current_active_user
from app.services.stream_service import stream_service

router = APIRouter()
media_server_url = getattr(settings, "MEDIA_SERVER_URL", "http://localhost:1985")


def _cors_headers(request: Request) -> dict:
    """生成 CORS 头，确保错误响应也带 CORS，避免浏览器报 CORS 阻塞"""
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origins_list:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


def _debug_log(location: str, message: str, data: dict, hypothesis_id: str = ""):
    # #region agent log
    try:
        _ws_root = Path(__file__).resolve().parents[4]
        log_path = _ws_root / "debug-870502.log"
        payload = {
            "sessionId": "870502",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion


@router.post("/stream/whep/{stream_id}")
async def whep_proxy(
    stream_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    WHEP 代理：将前端 SDP offer 转发到 SRS，返回 answer（避免 CORS）
    """
    # #region agent log
    _debug_log("streams.py:whep_proxy:entry", "WHEP proxy entry", {"stream_id": stream_id}, "H3")
    # #endregion
    cors_h = _cors_headers(request)
    try:
        # #region agent log
        body = await request.body()
        _debug_log("streams.py:whep_proxy:after_body", "body read ok", {"body_len": len(body)}, "H2")
        # #endregion
        srs_url = f"{media_server_url.rstrip('/')}/rtc/v1/whep/?app=live&stream={stream_id}"
        # #region agent log
        _debug_log("streams.py:whep_proxy:before_post", "before SRS POST", {"srs_url": srs_url}, "H3")
        # #endregion
        async with httpx.AsyncClient(timeout=10.0) as client:
            last_err: Optional[Exception] = None
            for attempt in range(3):
                try:
                    resp = await client.post(
                        srs_url,
                        content=body,
                        headers={"Content-Type": "application/sdp"},
                    )
                    # #region agent log
                    ans = resp.text if hasattr(resp, "text") else (resp.content.decode("utf-8", errors="replace") if resp.content else "")
                    _debug_log("streams.py:whep_proxy:after_post", "SRS responded", {"status_code": resp.status_code, "attempt": attempt + 1, "answer_len": len(ans), "has_m_video": "m=video" in ans}, "H1")
                    try:
                        streams_resp = await client.get(f"{media_server_url.rstrip('/')}/api/v1/streams?count=50")
                        if streams_resp.status_code == 200:
                            streams_data = streams_resp.json()
                            streams_list = streams_data.get("streams") if isinstance(streams_data.get("streams"), list) else []
                            stream_found = False
                            publish_active = False
                            for s in streams_list:
                                if not isinstance(s, dict):
                                    continue
                                sname = s.get("name") or s.get("stream") or ""
                                if sname == stream_id:
                                    stream_found = True
                                    pub = s.get("publish") if isinstance(s.get("publish"), dict) else {}
                                    publish_active = bool(pub.get("active"))
                                    break
                            _debug_log("streams.py:whep_proxy:srs_streams", "SRS streams query", {"stream_id": stream_id, "stream_found": stream_found, "publish_active": publish_active, "streams_count": len(streams_list)}, "H7")
                    except Exception as e7:
                        _debug_log("streams.py:whep_proxy:srs_streams", "SRS streams query error", {"detail": str(e7)}, "H7")
                    # #endregion
                    break
                except httpx.RemoteProtocolError as e:
                    last_err = e
                    # #region agent log
                    _debug_log("streams.py:whep_proxy:retry", "RemoteProtocolError, retrying", {"attempt": attempt + 1, "detail": str(e)}, "H1")
                    # #endregion
                    if attempt < 2:
                        await asyncio.sleep(1.5)
                    else:
                        raise
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type="application/sdp",
            headers=cors_h,
        )
    except httpx.ConnectError as e:
        # #region agent log
        _debug_log("streams.py:whep_proxy:except_connect", "ConnectError", {"detail": str(e)}, "H1")
        # #endregion
        logger.warning(f"[WHEP] SRS 连接失败 stream_id={stream_id}: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"detail": "媒体服务不可用，请确认 SRS 已启动"},
            headers=cors_h,
        )
    except httpx.RemoteProtocolError as e:
        # #region agent log
        _debug_log("streams.py:whep_proxy:except_remote", "RemoteProtocolError", {"detail": str(e)}, "H1")
        # #endregion
        logger.warning(f"[WHEP] SRS 断开连接 stream_id={stream_id}: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"detail": "媒体服务(SRS)连接异常，请确认 SRS 已启动且 Edge 已推流"},
            headers=cors_h,
        )
    except Exception as e:
        # #region agent log
        _debug_log("streams.py:whep_proxy:except", "Exception in WHEP", {"type": type(e).__name__, "detail": str(e)}, "H1,H4,H5")
        # #endregion
        logger.exception(f"[WHEP] 代理异常 stream_id={stream_id}: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers=cors_h,
        )


@router.get("/devices/{device_id}/stream/offer", response_model=StreamOfferResponse)
async def get_stream_offer(
    device_id: int,
    quality: Optional[str] = Query("medium", description="流质量: low, medium, high"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取WebRTC offer以启动视频流
    
    Args:
        device_id: 设备ID
        quality: 流质量（low, medium, high）
        current_user: 当前用户
        db: 数据库会话
    """
    logger.info(f"[Stream] 收到流媒体请求 device_id={device_id} quality={quality} user={current_user.id}")
    
    # 验证质量参数
    if quality not in ["low", "medium", "high"]:
        logger.warning(f"[Stream] 无效质量参数 device_id={device_id} quality={quality}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="质量参数必须是 low, medium 或 high"
        )
    
    # 检查设备是否存在且在线
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        logger.warning(f"[Stream] 设备不存在 device_id={device_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 {device_id} 不存在"
        )

    # 本机摄像头(ip=0)：允许请求流即使设备显示离线，由前端尝试连接后自行判断
    ip_addr = (device.ip_address or "").strip()
    is_local_camera = ip_addr == "0"
    if device.status != DeviceStatus.ONLINE and not is_local_camera:
        logger.warning(f"[Stream] 设备不在线 device_id={device_id} status={device.status.value}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"设备 {device_id} 当前不在线（状态: {device.status.value}）"
        )
    
    try:
        offer_data = await stream_service.create_offer(device_id, quality)

        await stream_service.notify_edge_node_start_stream(
            source_url=device.ip_address or "",
            device_id=device_id,
            stream_id=offer_data["stream_id"],
            rtmp_push_url=offer_data["rtmp_push_url"],
            quality=quality,
            edge_host=(device.edge_host or "").strip() or None,
        )
        # 等待 SRS 上出现推流再返回 offer（若 Edge 未推流则 streams 始终为空，超时后仍返回 offer）
        await stream_service.wait_for_stream(offer_data["stream_id"], timeout=5.0, interval=0.5)

        logger.info(f"[Stream] 流创建成功 device_id={device_id} stream_id={offer_data['stream_id']}")
        return StreamOfferResponse(
            stream_id=offer_data["stream_id"],
            whep_url=offer_data["whep_url"],
            sdp=offer_data.get("sdp"),
            type="offer",
            websocket_url=offer_data.get("websocket_url"),
        )
    except Exception as e:
        logger.exception(f"[Stream] 创建视频流失败 device_id={device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法创建视频流: {str(e)}"
        )


@router.post("/devices/{device_id}/stream/answer", response_model=StreamAnswerResponse)
async def send_stream_answer(
    device_id: int,
    answer_request: StreamAnswerRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送WebRTC answer完成握手
    
    Args:
        device_id: 设备ID
        answer_request: Answer请求
        current_user: 当前用户
        db: 数据库会话
    """
    # 验证设备存在
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 {device_id} 不存在"
        )
    
    # 处理answer
    try:
        result = await stream_service.process_answer(
            answer_request.stream_id,
            answer_request.sdp
        )
        
        return StreamAnswerResponse(
            status=result["status"],
            stream_id=result["stream_id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理answer时出错: {str(e)}"
        )


@router.get("/devices/{device_id}/stream/status", response_model=StreamStatusResponse)
async def get_stream_status(
    device_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取设备的流状态
    
    Args:
        device_id: 设备ID
        current_user: 当前用户
        db: 数据库会话
    """
    # 验证设备存在
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 {device_id} 不存在"
        )
    
    # 获取流状态
    status_data = stream_service.get_stream_status(device_id)
    
    if status_data:
        return StreamStatusResponse(**status_data)
    else:
        return StreamStatusResponse(
            device_id=device_id,
            is_active=False,
            connection_state="disconnected"
        )


@router.post("/devices/{device_id}/stream/control", response_model=StreamStatusResponse)
async def control_stream(
    device_id: int,
    control_request: StreamControlRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    控制视频流（切换覆盖层、调整质量等）
    
    Args:
        device_id: 设备ID
        control_request: 控制请求
        current_user: 当前用户
        db: 数据库会话
    """
    # 验证设备存在
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 {device_id} 不存在"
        )
    
    # 执行控制操作
    try:
        kwargs = {}
        if control_request.action == "toggle_overlay":
            if control_request.enable_overlay is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="toggle_overlay 操作需要 enable_overlay 参数"
                )
            kwargs["enable_overlay"] = control_request.enable_overlay
        elif control_request.action == "set_quality":
            if control_request.quality is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="set_quality 操作需要 quality 参数"
                )
            kwargs["quality"] = control_request.quality
        
        status_data = await stream_service.control_stream(
            device_id,
            control_request.action,
            **kwargs
        )
        
        return StreamStatusResponse(**status_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"控制流时出错: {str(e)}"
        )


@router.delete("/devices/{device_id}/stream", response_model=StreamStopResponse)
async def stop_stream(
    device_id: int,
    stream_id: str = Query(..., description="流ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    停止视频流
    
    Args:
        device_id: 设备ID
        stream_id: 流ID
        current_user: 当前用户
        db: 数据库会话
    """
    # 验证设备存在
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 {device_id} 不存在"
        )
    
    # 停止流
    try:
        result = await stream_service.stop_stream(device_id, stream_id)
        
        return StreamStopResponse(
            status=result["status"],
            stream_id=result["stream_id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止流时出错: {str(e)}"
        )
