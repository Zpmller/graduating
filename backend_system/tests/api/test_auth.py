import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user_token):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "admin"

@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    # Missing header results in 422 validation error
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    # Invalid token results in 401 (Unauthorized)
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
