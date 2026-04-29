"""
FastAPI应用入口
"""
import logging
import traceback
from pathlib import Path

from fastapi import FastAPI

# 确保 app 模块的 logger 输出到控制台（便于排查 stream/offer 等接口）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import CustomException, custom_exception_handler, validation_exception_handler
from app.api.api_v1 import api_router
from app.db.session import get_db

# 创建FastAPI应用
app = FastAPI(
    title="Mining Hot-Work Safety Monitoring System API",
    description="矿业动火作业行为安全监测系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 请求日志中间件（便于排查 stream/offer 等接口是否到达）
@app.middleware("http")
async def log_requests(request, call_next):
    if "/devices/" in request.url.path and "/stream/" in request.url.path:
        logging.getLogger(__name__).info(f"[Stream] 请求到达: {request.method} {request.url.path}")
    return await call_next(request)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 暴露所有响应头
)

# 注册异常处理器
app.add_exception_handler(CustomException, custom_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

@app.on_event("startup")
async def startup_event():
    """启动时检查"""
    print(f"Loading settings from environment...")
    try:
        # Hide password in logs
        db_url_parts = settings.DATABASE_URL.split("@")
        if len(db_url_parts) > 1:
            print(f"DATABASE_URL host: {db_url_parts[-1]}")
        
        print(f"CORS_ORIGINS: {settings.CORS_ORIGINS}")
        
        # Check DB connection
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            print("Database connection successful!")
            break
    except Exception as e:
        print(f"!!! Database connection failed: {e}")
        print(traceback.format_exc())

# 注册API路由
app.include_router(api_router, prefix="/api/v1")

# 静态文件服务（证据图片）
evidence_dir = Path(settings.EVIDENCE_DIR)
evidence_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")

# 人脸库存储目录（图片也通过 /api/v1/faces/{id}/image 提供下载）
face_dir = Path(settings.FACE_DIR)
face_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/faces", StaticFiles(directory=str(face_dir)), name="faces")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Mining Hot-Work Safety Monitoring System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    from app.core.tasks import background_tasks
    await background_tasks.stop()
    print("Background tasks stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
