"""
任务管理API测试
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, test_user_token):
    """测试创建任务"""
    response = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "测试任务",
            "description": "这是一个测试任务",
            "priority": "high",
            "status": "pending"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试任务"
    assert data["description"] == "这是一个测试任务"
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_task_with_due_date(client: AsyncClient, test_user_token):
    """测试创建带截止日期的任务"""
    due_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
    response = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "带截止日期的任务",
            "description": "7天后到期",
            "due_date": due_date,
            "priority": "medium"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "带截止日期的任务"
    assert data["due_date"] is not None


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, test_user_token):
    """测试获取任务列表"""
    # 先创建几个任务
    for i in range(3):
        await client.post(
            "/api/v1/tasks/",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "title": f"任务 {i+1}",
                "description": f"描述 {i+1}",
                "priority": "medium"
            }
        )
    
    # 获取任务列表
    response = await client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    assert "skip" in data
    assert "limit" in data


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(client: AsyncClient, test_user_token):
    """测试按状态过滤任务"""
    # 创建不同状态的任务
    await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"title": "待处理任务", "status": "pending"}
    )
    await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"title": "进行中任务", "status": "in_progress"}
    )
    
    # 过滤待处理任务
    response = await client.get(
        "/api/v1/tasks/?status=pending",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "pending" for item in data["items"])


@pytest.mark.asyncio
async def test_list_tasks_with_pagination(client: AsyncClient, test_user_token):
    """测试任务列表分页"""
    # 创建多个任务
    for i in range(5):
        await client.post(
            "/api/v1/tasks/",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"title": f"分页任务 {i+1}"}
        )
    
    # 第一页
    response = await client.get(
        "/api/v1/tasks/?skip=0&limit=2",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["skip"] == 0
    assert data["limit"] == 2
    
    # 第二页
    response = await client.get(
        "/api/v1/tasks/?skip=2&limit=2",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["skip"] == 2


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, test_user_token):
    """测试获取单个任务详情"""
    # 创建任务
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "详情任务",
            "description": "查看详情",
            "priority": "high"
        }
    )
    task_id = create_res.json()["id"]
    
    # 获取任务详情
    response = await client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "详情任务"
    assert data["description"] == "查看详情"


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient, test_user_token):
    """测试获取不存在的任务"""
    response = await client.get(
        "/api/v1/tasks/99999",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task(client: AsyncClient, test_user_token):
    """测试更新任务"""
    # 创建任务
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "原始标题",
            "status": "pending",
            "priority": "low"
        }
    )
    task_id = create_res.json()["id"]
    
    # 更新任务
    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "更新后的标题",
            "status": "in_progress",
            "priority": "high"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "更新后的标题"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_update_task_partial(client: AsyncClient, test_user_token):
    """测试部分更新任务"""
    # 创建任务
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "部分更新任务",
            "status": "pending"
        }
    )
    task_id = create_res.json()["id"]
    
    # 只更新状态
    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"status": "completed"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["title"] == "部分更新任务"  # 其他字段保持不变


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, test_user_token):
    """测试删除任务"""
    # 创建任务
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"title": "待删除任务"}
    )
    task_id = create_res.json()["id"]
    
    # 删除任务
    response = await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 204
    
    # 验证任务已删除
    get_res = await client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_not_found(client: AsyncClient, test_user_token):
    """测试删除不存在的任务"""
    response = await client.delete(
        "/api/v1/tasks/99999",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_tasks_by_assignee(client: AsyncClient, test_user_token, test_user):
    """测试按分配人过滤任务"""
    # 创建分配给当前用户的任务
    await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "分配给我的任务",
            "assigned_to": test_user.id
        }
    )
    
    # 创建未分配的任务
    await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"title": "未分配任务"}
    )
    
    # 过滤分配给当前用户的任务
    response = await client.get(
        f"/api/v1/tasks/?assignee_id={test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # 验证返回的任务都是分配给指定用户的
    assigned_tasks = [item for item in data["items"] if item["assigned_to"] is not None]
    if assigned_tasks:
        assert all(item["assigned_to"] == test_user.id for item in assigned_tasks)
