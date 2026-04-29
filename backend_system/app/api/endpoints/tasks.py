"""
任务管理API端点
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.db.session import get_db
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse
)
from app.api.deps import get_current_active_user

router = APIRouter()


def build_task_response(task: Task) -> TaskResponse:
    """构建任务响应，包含assignee_name"""
    response = TaskResponse.model_validate(task)
    if task.assigned_to and hasattr(task, 'assigned_user') and task.assigned_user:
        response.assignee_name = task.assigned_user.full_name or task.assigned_user.username
    return response


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    status: Optional[TaskStatus] = Query(None),
    assigned_to: Optional[int] = Query(None, alias="assignee_id"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务列表
    
    支持过滤：
    - status: 任务状态
    - assignee_id: 分配给的用户ID
    """
    # 构建查询
    query = select(Task)
    conditions = []
    
    if status:
        conditions.append(Task.status == status)
    
    if assigned_to is not None:
        conditions.append(Task.assigned_to == assigned_to)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # 获取总数
    count_query = select(Task)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    # 分页查询
    query = query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    # 加载用户关系
    for task in tasks:
        if task.assigned_to:
            await db.refresh(task, ["assigned_user"])
    
    items = [build_task_response(task) for task in tasks]
    
    return TaskListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新任务
    """
    task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assigned_to=task_data.assigned_to,
        due_date=task_data.due_date
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    if task.assigned_to:
        await db.refresh(task, ["assigned_user"])
    
    return build_task_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务详情
    """
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.assigned_to:
        await db.refresh(task, ["assigned_user"])
    
    return build_task_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新任务
    """
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 更新字段
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    
    if task.assigned_to:
        await db.refresh(task, ["assigned_user"])
    
    return build_task_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除任务
    """
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    await db.delete(task)
    await db.commit()
    
    return None
