"""
系统API端点：健康检查等
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    健康检查端点（无需认证）
    """
    try:
        # 测试数据库连接
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        database_status = "connected"
    except Exception:
        database_status = "disconnected"
    
    status_code = 200 if database_status == "connected" else 503
    
    return {
        "status": "healthy" if database_status == "connected" else "unhealthy",
        "database": database_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
