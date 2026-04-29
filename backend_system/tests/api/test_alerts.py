import pytest
import json
import time
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, test_user_token):
    # 1. Create a device to get a token
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Alert Test Device",
            "location": "Alert Loc",
            "ip_address": "10.0.0.10"
        }
    )
    assert device_res.status_code == 201
    device_token = device_res.json()["device_token"]
    
    # 2. Create alert
    alert_payload = {
        "type": "fire_violation",
        "level": "CRITICAL",
        "message": "Fire detected!",
        "timestamp": time.time()
    }
    
    response = await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Fire detected!"
    assert data["device_name"] == "Alert Test Device"
    assert data["is_acknowledged"] is False
    
    return data["id"]

@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient, test_user_token):
    # Ensure at least one alert exists (handled by previous tests if run in order, 
    # but strictly speaking tests should be independent. 
    # For simplicity in this env, we might rely on the DB being cleared per test 
    # but the device needs to be recreated.)
    
    # Create device and alert again
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "List Alert Device",
            "location": "List Loc",
            "ip_address": "10.0.0.11"
        }
    )
    device_token = device_res.json()["device_token"]
    
    alert_payload = {
        "type": "ppe_violation",
        "level": "WARNING",
        "message": "No Helmet",
        "timestamp": time.time()
    }
    await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    
    # List alerts
    response = await client.get(
        "/api/v1/alerts/",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["message"] == "No Helmet"

@pytest.mark.asyncio
async def test_acknowledge_alert(client: AsyncClient, test_user_token):
    # Create device and alert
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Ack Alert Device",
            "location": "Ack Loc",
            "ip_address": "10.0.0.12"
        }
    )
    device_token = device_res.json()["device_token"]
    
    alert_payload = {
        "type": "smoke_violation",
        "level": "DANGER",
        "message": "Smoke detected",
        "timestamp": time.time()
    }
    alert_res = await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    alert_id = alert_res.json()["id"]
    
    # Acknowledge alert
    ack_res = await client.put(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"notes": "Investigating"}
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["is_acknowledged"] is True


@pytest.mark.asyncio
async def test_create_alert_with_metadata(client: AsyncClient, test_user_token):
    """测试创建带metadata字段的告警"""
    # 创建设备
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Metadata Test Device",
            "location": "Metadata Loc",
            "ip_address": "10.0.0.13"
        }
    )
    device_token = device_res.json()["device_token"]
    
    # 创建带metadata的告警
    alert_payload = {
        "type": "fire_violation",
        "level": "CRITICAL",
        "message": "Fire detected with metadata",
        "timestamp": time.time(),
        "metadata": {
            "confidence": 0.95,
            "bbox": [10, 20, 100, 150],
            "detection_model": "yolov8",
            "frame_number": 1234
        }
    }
    
    response = await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Fire detected with metadata"
    assert "metadata" in data
    assert data["metadata"] is not None
    assert data["metadata"]["confidence"] == 0.95
    assert data["metadata"]["bbox"] == [10, 20, 100, 150]
    assert data["metadata"]["detection_model"] == "yolov8"


@pytest.mark.asyncio
async def test_create_alert_without_metadata(client: AsyncClient, test_user_token):
    """测试创建不带metadata字段的告警（metadata应为None）"""
    # 创建设备
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "No Metadata Device",
            "location": "No Metadata Loc",
            "ip_address": "10.0.0.14"
        }
    )
    device_token = device_res.json()["device_token"]
    
    # 创建不带metadata的告警
    alert_payload = {
        "type": "ppe_violation",
        "level": "WARNING",
        "message": "No helmet detected",
        "timestamp": time.time()
        # 不包含metadata字段
    }
    
    response = await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "No helmet detected"
    # metadata字段应该存在但为None
    assert "metadata" in data
    assert data["metadata"] is None


@pytest.mark.asyncio
async def test_list_alerts_with_metadata(client: AsyncClient, test_user_token):
    """测试获取告警列表时metadata字段正确返回"""
    # 创建设备
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "List Metadata Device",
            "location": "List Metadata Loc",
            "ip_address": "10.0.0.15"
        }
    )
    device_token = device_res.json()["device_token"]
    
    # 创建带metadata的告警
    alert_payload = {
        "type": "distance_violation",
        "level": "DANGER",
        "message": "Distance violation",
        "timestamp": time.time(),
        "metadata": {
            "distance": 3.5,
            "min_required": 5.0,
            "object_type": "gas_cylinder"
        }
    }
    await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    
    # 获取告警列表
    response = await client.get(
        "/api/v1/alerts/",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    
    # 查找刚创建的告警
    alert = next((item for item in data["items"] if item["message"] == "Distance violation"), None)
    assert alert is not None
    assert "metadata" in alert
    assert alert["metadata"] is not None
    assert alert["metadata"]["distance"] == 3.5
    assert alert["metadata"]["min_required"] == 5.0


@pytest.mark.asyncio
async def test_acknowledge_alert_preserves_metadata(client: AsyncClient, test_user_token):
    """测试确认告警时metadata字段保持不变"""
    # 创建设备
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Ack Metadata Device",
            "location": "Ack Metadata Loc",
            "ip_address": "10.0.0.16"
        }
    )
    device_token = device_res.json()["device_token"]
    
    # 创建带metadata的告警
    alert_payload = {
        "type": "access_control",
        "level": "WARNING",
        "message": "Unauthorized access",
        "timestamp": time.time(),
        "metadata": {
            "person_id": "unknown",
            "confidence": 0.88,
            "access_point": "Gate A"
        }
    }
    alert_res = await client.post(
        "/api/v1/alerts/",
        headers={"X-Device-Token": device_token},
        data={"alert_data": json.dumps(alert_payload)}
    )
    alert_id = alert_res.json()["id"]
    original_metadata = alert_res.json()["metadata"]
    
    # 确认告警
    ack_res = await client.put(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"notes": "Handled"}
    )
    assert ack_res.status_code == 200
    data = ack_res.json()
    assert data["is_acknowledged"] is True
    # metadata应该保持不变
    assert data["metadata"] == original_metadata
    assert data["metadata"]["person_id"] == "unknown"
    assert data["metadata"]["confidence"] == 0.88
