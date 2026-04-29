"""
用户相关Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class UserBase(BaseModel):
    """用户基础Schema"""
    username: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True


class UserCreate(UserBase):
    """创建用户Schema"""
    password: str


class UserUpdate(BaseModel):
    """更新用户Schema"""
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """用户响应Schema"""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: list[UserResponse]
    total: int
    skip: int
    limit: int


class UserMeResponse(BaseModel):
    """当前用户信息响应"""
    id: int
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)
