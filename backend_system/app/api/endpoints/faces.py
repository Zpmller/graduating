"""
人脸库 API：上传、列表、下载图片（供 Edge 同步与授权检测使用）
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.face import FaceRecord
from app.schemas.face import FaceRecordResponse, FaceListResponse
from app.services.face_storage import face_storage_service
from app.core.config import settings

router = APIRouter()


@router.post("/", response_model=FaceRecordResponse, status_code=201)
async def upload_face(
    person_name: str = Form(..., description="授权人员姓名/标识"),
    image: UploadFile = File(..., description="人脸图片"),
    db: AsyncSession = Depends(get_db),
):
    """上传一张人脸图片到人脸库（Edge 注册时或批量同步时调用）"""
    try:
        relative_path = await face_storage_service.save_face_image(image, person_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record = FaceRecord(person_name=person_name, file_path=relative_path)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/", response_model=FaceListResponse)
async def list_faces(db: AsyncSession = Depends(get_db)):
    """获取所有人脸记录（Edge 同步时拉取列表，再按 id 下载图片）"""
    result = await db.execute(select(FaceRecord).order_by(FaceRecord.person_name, FaceRecord.id))
    records = result.scalars().all()
    return FaceListResponse(
        total=len(records),
        items=[FaceRecordResponse.model_validate(r) for r in records],
    )


@router.get("/{face_id}/image")
async def get_face_image(face_id: int, db: AsyncSession = Depends(get_db)):
    """根据 ID 返回人脸图片文件（Edge 同步时下载到本地 face_db）"""
    result = await db.execute(select(FaceRecord).where(FaceRecord.id == face_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Face record not found")
    abs_path = face_storage_service.get_absolute_path(record.file_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(
        path=str(abs_path),
        media_type="image/jpeg",
        filename=Path(record.file_path).name,
    )
