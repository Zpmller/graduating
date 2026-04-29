"""
API依赖注入：认证、授权、数据库会话等
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.device import Device, DeviceStatus
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前登录用户（JWT认证）
    
    Header格式: Authorization: Bearer {token}
    """
    if not authorization:
        raise AuthenticationError("缺少认证token")
    
    # 提取token
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("无效的认证格式")
    
    token = authorization.replace("Bearer ", "").strip()
    
    if not token:
        raise AuthenticationError("token不能为空")
    
    # 解码token
    payload = decode_access_token(token)
    if payload is None:
        raise AuthenticationError("无效或过期的token")
    
    # 获取用户ID
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("token中缺少用户ID")
    
    # 查询用户
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise AuthenticationError("用户不存在或已被禁用")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    角色权限装饰器
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(f"需要以下角色之一: {', '.join(r.value for r in allowed_roles)}")
        return current_user
    
    return role_checker


async def get_device_by_token(
    x_device_token: str = Header(..., alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db)
) -> Device:
    """
    通过设备token获取设备（设备认证）
    
    Header格式: X-Device-Token: {device_token}
    """
    result = await db.execute(
        select(Device).where(Device.device_token == x_device_token)
    )
    device = result.scalar_one_or_none()
    
    if device is None:
        raise AuthenticationError("无效的设备token")
    
    if device.status == DeviceStatus.OFFLINE:
        # 允许离线设备发送告警（可能是心跳超时但设备仍在运行）
        pass
    
    return device
