"""



????API??



"""



import logging



import secrets







logger = logging.getLogger(__name__)



from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, status, Query



from sqlalchemy.ext.asyncio import AsyncSession



from sqlalchemy import select, func



from app.db.session import get_db



from app.models.user import User, UserRole



from app.models.device import Device, DeviceStatus



from app.schemas.device import (



    DeviceCreate,



    DeviceUpdate,



    DeviceResponse,



    DeviceListResponse,



    DeviceListWithStreamResponse,



    DeviceResponseWithStream,



    DeviceStreamStatus,



    HeartbeatResponse,



    DeviceBootstrapResponse,



)



from app.api.deps import get_current_active_user, require_role, get_device_by_token



from datetime import datetime



# ??



from typing import Optional, List, Union



from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File



from app.services.calibration_service import calibration_service



from app.services.stream_service import stream_service



from app.core.config import settings







router = APIRouter()











def generate_device_token() -> str:



    """Generate device token (UUID format)."""



    return secrets.token_urlsafe(32)











@router.get("/", response_model=Union[DeviceListResponse, DeviceListWithStreamResponse])



async def list_devices(



    skip: int = Query(0, ge=0),



    limit: int = Query(100, ge=1, le=200),



    status_filter: Optional[DeviceStatus] = Query(None, alias="status"),



    include_stream_status: bool = Query(False, description="?????????????"),



    current_user: User = Depends(get_current_active_user),



    db: AsyncSession = Depends(get_db)



):



    """



    ???????????????????????



    """



    query = select(Device)



    



    if status_filter:



        query = query.where(Device.status == status_filter)



    



    # ????



    count_query = select(func.count(Device.id))



    if status_filter:



        count_query = count_query.where(Device.status == status_filter)



    total_result = await db.execute(count_query)



    total = total_result.scalar() or 0



    



    # ????



    query = query.order_by(Device.created_at.desc()).offset(skip).limit(limit)



    result = await db.execute(query)



    devices = result.scalars().all()



    



    if not include_stream_status:



        return DeviceListResponse(



            items=[DeviceResponse.model_validate(device) for device in devices],



            total=total,



            skip=skip,



            limit=limit



        )



    



    # ?????????????????????



    items = []



    for device in devices:



        base = DeviceResponse.model_validate(device)



        stream_info = stream_service.get_stream_status(device.id)



        stream_status = DeviceStreamStatus(



            is_active=stream_info.get("is_active", False),



            stream_id=stream_info.get("stream_id"),



            quality=stream_info.get("quality"),



            connection_state=stream_info.get("connection_state", "disconnected"),



        ) if stream_info else None



        items.append(DeviceResponseWithStream(**base.model_dump(), stream_status=stream_status))



    



    return DeviceListWithStreamResponse(



        items=items,



        total=total,



        skip=skip,



        limit=limit



    )











@router.get("/bootstrap", response_model=DeviceBootstrapResponse)



async def device_bootstrap(



    edge_host: str = Query(..., description="Edge ???? IP ????????????"),



    bootstrap_secret: Optional[str] = Query(None, alias="secret"),



    db: AsyncSession = Depends(get_db),



):



    """



    Edge ???????? edge_host ????????????? token?



    ?????edge_host ? 127.0.0.1 ??????? edge_host ??????



    """

    try:



        if settings.BOOTSTRAP_SECRET and bootstrap_secret != settings.BOOTSTRAP_SECRET:

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="???????")



        edge_host_clean = edge_host.strip().lower()



        if not edge_host_clean:



            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="edge_host ????")







        device = None

        # ??????? edge_host ???????? NULL ?????



        result = await db.execute(



            select(Device).where(



                Device.edge_host.is_not(None),



                func.lower(Device.edge_host) == edge_host_clean,



            )



        )



        device = result.scalar_one_or_none()

        # ?????127.0.0.1/localhost ??? edge_host ?????



        if not device and edge_host_clean in ("127.0.0.1", "localhost"):



            from sqlalchemy import or_



            result = await db.execute(



                select(Device).where(



                    or_(



                        Device.edge_host.is_(None),



                        Device.edge_host == "",



                        func.lower(Device.edge_host) == "127.0.0.1",



                        func.lower(Device.edge_host) == "localhost",



                    )



                )



            )



            devices = result.scalars().all()

            if len(devices) == 1:



                device = devices[0]



            elif len(devices) == 0:



                # ???????????? 1 ?????????????????



                count_result = await db.execute(select(Device))



                all_devices = count_result.scalars().all()

                if len(all_devices) == 1:



                    device = all_devices[0]







        if not device:

            raise HTTPException(



                status_code=status.HTTP_404_NOT_FOUND,



                detail=f"???edge_host={edge_host} ?????????????????Edge ?????? 127.0.0.1 ????",



            )

        response_data = DeviceBootstrapResponse.model_validate(device)

        return response_data



    except HTTPException:



        raise



    except Exception as e:



        logger.exception(f"[Bootstrap] 500 error edge_host={edge_host}: {e}")

        raise HTTPException(



            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,



            detail=f"Bootstrap ????: {str(e)}",



        )











@router.get("/me", response_model=DeviceResponse)



async def get_my_device(



    device: Device = Depends(get_device_by_token),



):



    """



    ?? X-Device-Token ????????Edge ????



    ?? Edge ??????????????? device_id



    """



    return DeviceResponse.model_validate(device)











@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)



async def create_device(



    device_data: DeviceCreate,



    current_user: User = Depends(require_role(UserRole.ADMIN)),



    db: AsyncSession = Depends(get_db)



):



    """



    ??????????



    """



    # ?????????



    result = await db.execute(



        select(Device).where(Device.name == device_data.name)



    )



    if result.scalar_one_or_none():



        raise HTTPException(



            status_code=status.HTTP_400_BAD_REQUEST,



            detail="???????"



        )



    



    # ????



    device = Device(



        name=device_data.name,



        location=device_data.location,



        ip_address=device_data.ip_address,



        edge_host=device_data.edge_host,



        device_token=generate_device_token(),



        status=DeviceStatus.OFFLINE



    )



    



    db.add(device)



    await db.commit()



    await db.refresh(device)



    



    return DeviceResponse.model_validate(device)











@router.get("/{device_id}", response_model=DeviceResponse)



async def get_device(



    device_id: int,



    current_user: User = Depends(get_current_active_user),



    db: AsyncSession = Depends(get_db)



):



    """



    ??????



    """



    result = await db.execute(



        select(Device).where(Device.id == device_id)



    )



    device = result.scalar_one_or_none()



    



    if device is None:



        raise HTTPException(



            status_code=status.HTTP_404_NOT_FOUND,



            detail="?????"



        )



    



    return DeviceResponse.model_validate(device)











@router.put("/{device_id}", response_model=DeviceResponse)



async def update_device(



    device_id: int,



    device_data: DeviceUpdate,



    current_user: User = Depends(require_role(UserRole.ADMIN)),



    db: AsyncSession = Depends(get_db)



):



    """



    ????????????



    """



    result = await db.execute(



        select(Device).where(Device.id == device_id)



    )



    device = result.scalar_one_or_none()



    



    if device is None:



        raise HTTPException(



            status_code=status.HTTP_404_NOT_FOUND,



            detail="?????"



        )



    



    # ??????



    if device_data.name and device_data.name != device.name:



        name_check = await db.execute(



            select(Device).where(Device.name == device_data.name)



        )



        if name_check.scalar_one_or_none():



            raise HTTPException(



                status_code=status.HTTP_400_BAD_REQUEST,



                detail="???????"



            )







    # ????



    update_data = device_data.model_dump(exclude_unset=True)



    for field, value in update_data.items():



        # ????????



        if hasattr(device, field):



            setattr(device, field, value)



    



    device.updated_at = datetime.utcnow()



    



    try:



        await db.flush()



        await db.commit()



        await db.refresh(device)







        response = DeviceResponse.model_validate(device)



        return response



    except Exception as e:



        await db.rollback()



        # ????????



        import traceback



        error_trace = traceback.format_exc()



        print(f"[??????] ??ID: {device_id}, ??: {str(e)}")



        print(f"[????]\n{error_trace}")



        raise HTTPException(



            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,



            detail=f"??????: {str(e)}"



        )











@router.post("/{device_id}/heartbeat", response_model=HeartbeatResponse)



async def device_heartbeat(



    device_id: int,



    device: Device = Depends(get_device_by_token),



    db: AsyncSession = Depends(get_db)



):



    """



    ???????last_heartbeat?status?



    """



    logger.info(f"[Heartbeat] device_id={device_id} name={device.name}")



    # ????ID??



    if device.id != device_id:



        raise HTTPException(



            status_code=status.HTTP_403_FORBIDDEN,



            detail="??ID???"



        )



    



    # ?????????????



    was_offline = device.status != DeviceStatus.ONLINE



    



    # ?????????



    device.last_heartbeat = datetime.utcnow()



    device.status = DeviceStatus.ONLINE



    device.updated_at = datetime.utcnow()



    



    await db.commit()



    



    # ???????????????



    if was_offline and device.ip_address:



        try:



            # ????????medium???



            offer_data = await stream_service.create_offer(device.id, "medium")



            # edge_host ??????? Edge???? ip_address ??



            edge_host = (device.edge_host or "").strip() or None



            await stream_service.notify_edge_node_start_stream(



                source_url=device.ip_address or "",



                device_id=device.id,



                stream_id=offer_data["stream_id"],



                rtmp_push_url=offer_data["rtmp_push_url"],



                quality="medium",



                edge_host=edge_host,



            )



            



            # ????????answer??????????



            # Edge Node???????????WebRTC??



        except Exception as e:



            # ??????????????



            print(f"[Device Heartbeat] Failed to auto-start stream for device {device_id}: {e}")



    



    await db.refresh(device)



    



    return HeartbeatResponse(



        status="ok",



        last_heartbeat=device.last_heartbeat



    )











@router.get("/{device_id}/calibration/yaml")



async def get_calibration_yaml(



    device_id: int,



    device: Device = Depends(get_device_by_token),



    db: AsyncSession = Depends(get_db)



):



    """



    ?????????????????



    """



    if device.id != device_id:



        raise HTTPException(



            status_code=status.HTTP_403_FORBIDDEN,



            detail="??ID???"



        )



        



    if not device.calibration_config:



        raise HTTPException(



            status_code=status.HTTP_404_NOT_FOUND,



            detail="???????"



        )



        



    from fastapi.responses import Response



    return Response(content=device.calibration_config, media_type="application/x-yaml")



















@router.post("/{device_id}/calibration/yaml", response_model=DeviceResponse)



async def upload_calibration_yaml(



    device_id: int,



    file: UploadFile = File(...),



    current_user: User = Depends(require_role(UserRole.ADMIN)),



    db: AsyncSession = Depends(get_db)



):



    """



    ????YAML????????



    """



    result = await db.execute(select(Device).where(Device.id == device_id))



    device = result.scalar_one_or_none()



    



    if device is None:



        raise HTTPException(status_code=404, detail="Device not found")



        



    yaml_content = await calibration_service.process_yaml_upload(file)



    



    device.calibration_config = yaml_content



    device.updated_at = datetime.utcnow()



    



    await db.commit()



    await db.refresh(device)



    



    return DeviceResponse.model_validate(device)











@router.post("/{device_id}/calibration/images", response_model=DeviceResponse)



async def calibrate_with_images(



    device_id: int,



    files: List[UploadFile] = File(...),



    current_user: User = Depends(require_role(UserRole.ADMIN)),



    db: AsyncSession = Depends(get_db)



):



    """



    ??????????????



    """



    result = await db.execute(select(Device).where(Device.id == device_id))



    device = result.scalar_one_or_none()



    



    if device is None:



        raise HTTPException(status_code=404, detail="Device not found")



        



    yaml_content = await calibration_service.run_calibration_script(files)



    



    device.calibration_config = yaml_content



    device.updated_at = datetime.utcnow()



    



    await db.commit()



    await db.refresh(device)



    



    return DeviceResponse.model_validate(device)



