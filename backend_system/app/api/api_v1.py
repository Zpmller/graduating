"""
API v1路由聚合器
"""
from fastapi import APIRouter
from app.api.endpoints import auth, devices, alerts, system, tasks, users, streams, faces

api_router = APIRouter()

# 注册各个端点路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(devices.router, prefix="/devices", tags=["设备管理"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["告警管理"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(streams.router, prefix="", tags=["视频流"])  # 使用空prefix因为路由已经在streams.py中定义了完整路径
api_router.include_router(faces.router, prefix="/faces", tags=["人脸库"])
api_router.include_router(system.router, prefix="/system", tags=["系统"])
