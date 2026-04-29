"""
任务相关Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    """任务基础Schema"""
    title: str = Field(..., max_length=100)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    """创建任务Schema"""
    pass


class TaskUpdate(BaseModel):
    """更新任务Schema"""
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskResponse(TaskBase):
    """任务响应Schema"""
    id: int
    assignee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """任务列表响应"""
    items: list[TaskResponse]
    total: int
    skip: int
    limit: int
