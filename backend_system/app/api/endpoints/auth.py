"""
认证API端点
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenRequest, TokenResponse
from app.schemas.user import UserMeResponse
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def login(
    credentials: TokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录，返回JWT token
    """
    # 查询用户
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 创建token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_SECONDS
    )


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息
    """
    return UserMeResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active
    )
