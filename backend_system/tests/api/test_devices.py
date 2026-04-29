import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_device(client: AsyncClient, test_user_token):
    response = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Test Device",
            "location": "Test Location",
            "ip_address": "192.168.1.100"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Device"
    assert data["location"] == "Test Location"
    assert "device_token" in data
    assert data["status"] == "offline"

@pytest.mark.asyncio
async def test_list_devices(client: AsyncClient, test_user_token):
    # First create a device
    await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Device 1",
            "location": "Loc 1",
            "ip_address": "10.0.0.1"
        }
    )
    
    response = await client.get(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["name"] == "Device 1"

@pytest.mark.asyncio
async def test_create_device_duplicate_name(client: AsyncClient, test_user_token):
    # Create first device
    await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Duplicate Device",
            "location": "Loc 1",
            "ip_address": "10.0.0.1"
        }
    )
    
    # Try to create second device with same name
    response = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Duplicate Device",
            "location": "Loc 2",
            "ip_address": "10.0.0.2"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "设备名称已存在"
