"""
用户管理API测试（管理员专用）
"""
import pytest
from httpx import AsyncClient
from app.models.user import UserRole
from app.core.security import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, test_user_token):
    """测试获取用户列表（管理员）"""
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # 至少包含test_user
    assert any(user["username"] == "testuser" for user in data)


@pytest.mark.asyncio
async def test_list_users_non_admin(client: AsyncClient, db_session: AsyncSession):
    """测试非管理员用户无法访问用户列表"""
    # 创建操作员用户
    operator = User(
        username="operator",
        hashed_password=get_password_hash("password"),
        role=UserRole.OPERATOR,
        is_active=True
    )
    db_session.add(operator)
    await db_session.commit()
    await db_session.refresh(operator)
    
    # 获取操作员的token
    login_res = await client.post(
        "/api/v1/auth/token",
        json={"username": "operator", "password": "password"}
    )
    assert login_res.status_code == 200
    operator_token = login_res.json()["access_token"]
    
    # 尝试访问用户列表（应该被拒绝，403 Forbidden）
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 403  # 权限不足


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, test_user_token):
    """测试创建用户（管理员）"""
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "username": "newuser",
            "password": "newpassword123",
            "full_name": "New User",
            "role": "operator",
            "is_active": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["full_name"] == "New User"
    assert data["role"] == "operator"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data  # 密码不应在响应中


@pytest.mark.asyncio
async def test_create_user_duplicate_username(client: AsyncClient, test_user_token):
    """测试创建重复用户名的用户"""
    # 先创建一个用户
    await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "username": "duplicate",
            "password": "password",
            "role": "operator"
        }
    )
    
    # 尝试创建同名用户
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "username": "duplicate",
            "password": "password2",
            "role": "viewer"
        }
    )
    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, test_user_token, test_user):
    """测试获取用户详情（管理员）"""
    response = await client.get(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["username"] == "testuser"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, test_user_token):
    """测试获取不存在的用户"""
    response = await client.get(
        "/api/v1/users/99999",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, test_user_token, db_session: AsyncSession):
    """测试更新用户信息（管理员）"""
    # 创建一个测试用户
    test_user = User(
        username="updatetest",
        hashed_password=get_password_hash("password"),
        full_name="Original Name",
        role=UserRole.OPERATOR,
        is_active=True
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)
    
    # 更新用户信息
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "full_name": "Updated Name",
            "role": "viewer",
            "is_active": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["role"] == "viewer"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_password(client: AsyncClient, test_user_token, db_session: AsyncSession):
    """测试更新用户密码"""
    # 创建测试用户
    test_user = User(
        username="passwordtest",
        hashed_password=get_password_hash("oldpassword"),
        role=UserRole.OPERATOR,
        is_active=True
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)
    
    # 更新密码
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"password": "newpassword123"}
    )
    assert response.status_code == 200
    
    # 验证新密码可以登录
    login_res = await client.post(
        "/api/v1/auth/token",
        json={"username": "passwordtest", "password": "newpassword123"}
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_update_user_partial(client: AsyncClient, test_user_token, db_session: AsyncSession):
    """测试部分更新用户信息"""
    # 创建测试用户
    test_user = User(
        username="partialtest",
        hashed_password=get_password_hash("password"),
        full_name="Original",
        role=UserRole.OPERATOR,
        is_active=True
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)
    
    # 只更新full_name
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"full_name": "Updated"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated"
    assert data["role"] == "operator"  # 其他字段保持不变


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, test_user_token, db_session: AsyncSession):
    """测试删除用户（管理员）"""
    # 创建测试用户
    test_user = User(
        username="deletetest",
        hashed_password=get_password_hash("password"),
        role=UserRole.OPERATOR,
        is_active=True
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)
    user_id = test_user.id
    
    # 删除用户
    response = await client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 204
    
    # 验证用户已删除
    get_res = await client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_self(client: AsyncClient, test_user_token, test_user):
    """测试不能删除自己的账户"""
    response = await client.delete(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 400
    assert "不能删除自己的账户" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient, test_user_token):
    """测试删除不存在的用户"""
    response = await client.delete(
        "/api/v1/users/99999",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient, test_user_token, db_session: AsyncSession):
    """测试用户列表分页"""
    # 创建多个用户
    for i in range(5):
        user = User(
            username=f"pagination{i}",
            hashed_password=get_password_hash("password"),
            role=UserRole.OPERATOR,
            is_active=True
        )
        db_session.add(user)
    await db_session.commit()
    
    # 获取用户列表（应该包含所有用户）
    response = await client.get(
        "/api/v1/users/?skip=0&limit=100",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6  # test_user + 5个新用户
