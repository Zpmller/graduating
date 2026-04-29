"""
告警API端点
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.device import Device
from app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertListResponse,
    AlertStatsResponse,
    AlertAcknowledgeRequest
)
from app.api.deps import get_current_active_user, require_role, get_device_by_token
from app.services.file_storage import file_storage_service
from app.services.alert_service import alert_service
import json

router = APIRouter()


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: str = Form(..., description="JSON格式的告警数据"),
    image: Optional[UploadFile] = File(None, description="证据图片"),
    device: Device = Depends(get_device_by_token),
    db: AsyncSession = Depends(get_db)
):
    """
    创建告警（Edge Node调用）
    
    请求格式：multipart/form-data
    - alert_data: JSON字符串，包含type, level, message, timestamp
    - image: 图片文件（可选）
    """
    try:
        # 解析JSON数据
        alert_json = json.loads(alert_data)
        alert_create = AlertCreate(**alert_json)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的告警数据格式: {str(e)}"
        )
    
    # 转换时间戳为datetime
    event_timestamp = datetime.utcfromtimestamp(alert_create.timestamp)
    
    # 保存图片（如果提供）
    image_path = None
    if image:
        try:
            date_str = event_timestamp.strftime("%Y-%m-%d")
            image_path = await file_storage_service.save_evidence_image(image, date_str)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片保存失败: {str(e)}"
            )
    
    # 创建告警记录
    alert = Alert(
        device_id=device.id,
        type=alert_create.type,
        severity=alert_create.level,  # level对应severity
        message=alert_create.message,
        timestamp=event_timestamp,
        image_path=image_path,
        alert_metadata=alert_create.metadata,  # 保存元数据
        is_acknowledged=False
    )
    
    db.add(alert)
    await db.commit()
    logger.info(f"[Alert] device_id={device.id} type={alert_create.type} level={alert_create.level} msg={(alert_create.message or '')[:50]}")
    await db.refresh(alert)
    
    # 加载设备关系以获取设备名称
    await db.refresh(alert, ["device"])
    
    # 构建响应（使用辅助方法自动处理metadata映射）
    response = AlertResponse.from_orm_with_mapping(alert)
    response.device_name = alert.device.name
    response.image_url = file_storage_service.get_image_url(alert.image_path) if alert.image_path else None
    
    return response


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    device_id: Optional[int] = Query(None),
    type: Optional[AlertType] = Query(None),
    severity: Optional[AlertSeverity] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    is_acknowledged: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取告警列表（支持多种过滤条件）
    """
    alerts, total = await alert_service.get_alerts(
        db=db,
        skip=skip,
        limit=limit,
        device_id=device_id,
        alert_type=type,
        severity=severity,
        start_date=start_date,
        end_date=end_date,
        is_acknowledged=is_acknowledged
    )
    
    # 加载设备关系
    for alert in alerts:
        await db.refresh(alert, ["device"])
    
    # 构建响应
    items = []
    for alert in alerts:
        response = AlertResponse.from_orm_with_mapping(alert)
        response.device_name = alert.device.name
        response.image_url = file_storage_service.get_image_url(alert.image_path) if alert.image_path else None
        items.append(response)
    
    return AlertListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    device_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取告警统计信息
    """
    stats = await alert_service.get_alert_stats(
        db=db,
        start_date=start_date,
        end_date=end_date,
        device_id=device_id
    )
    
    return AlertStatsResponse(**stats)


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    request: Optional[AlertAcknowledgeRequest] = None,
    current_user: User = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    确认告警（操作员和管理员）
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警不存在"
        )
    
    if alert.is_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="告警已被确认"
        )
    
    # 更新确认信息
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(alert)
    await db.refresh(alert, ["device"])
    
    # 构建响应
    response = AlertResponse.from_orm_with_mapping(alert)
    response.device_name = alert.device.name
    response.image_url = file_storage_service.get_image_url(alert.image_path) if alert.image_path else None
    
    return response
