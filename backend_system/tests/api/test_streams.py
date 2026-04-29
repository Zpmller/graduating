"""
视频流API端点测试
"""
import pytest
from httpx import AsyncClient
from app.models.device import DeviceStatus


@pytest.mark.asyncio
async def test_get_stream_offer_success(client: AsyncClient, test_user_token):
    """测试成功获取视频流offer"""
    # 1. 创建设备并设置为在线状态
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Stream Test Device",
            "location": "Stream Location",
            "ip_address": "192.168.1.200"
        }
    )
    assert device_res.status_code == 201
    device_id = device_res.json()["id"]
    
    # 2. 设置设备为在线状态（模拟心跳）
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    # 3. 请求流offer
    response = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        params={"quality": "medium"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "sdp" in data
    assert data["type"] == "offer"
    assert "websocket_url" in data
    assert "stream_id" in data
    assert data["stream_id"].startswith("stream_")
    
    return data["stream_id"]


@pytest.mark.asyncio
async def test_get_stream_offer_device_not_found(client: AsyncClient, test_user_token):
    """测试设备不存在时获取offer"""
    response = await client.get(
        "/api/v1/devices/99999/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_stream_offer_device_offline(client: AsyncClient, test_user_token):
    """测试设备离线时获取offer"""
    # 创建设备（默认离线）
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Offline Device",
            "location": "Offline Location",
            "ip_address": "192.168.1.201"
        }
    )
    device_id = device_res.json()["id"]
    
    # 尝试获取offer
    response = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 503
    assert "不在线" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_stream_offer_invalid_quality(client: AsyncClient, test_user_token):
    """测试无效质量参数"""
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Quality Test Device",
            "location": "Quality Location",
            "ip_address": "192.168.1.202"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    # 使用无效质量参数
    response = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        params={"quality": "invalid"}
    )
    assert response.status_code == 400
    assert "质量参数" in response.json()["detail"]


@pytest.mark.asyncio
async def test_send_stream_answer(client: AsyncClient, test_user_token):
    """测试发送WebRTC answer"""
    # 创建设备并获取offer
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Answer Test Device",
            "location": "Answer Location",
            "ip_address": "192.168.1.203"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    # 获取offer
    offer_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    stream_id = offer_res.json()["stream_id"]
    
    # 发送answer
    answer_data = {
        "stream_id": stream_id,
        "sdp": "v=0\r\no=- 9876543210 9876543210 IN IP4 0.0.0.0\r\n...",
        "type": "answer"
    }
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=answer_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["stream_id"] == stream_id


@pytest.mark.asyncio
async def test_send_stream_answer_invalid_stream_id(client: AsyncClient, test_user_token):
    """测试无效stream_id的answer"""
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Invalid Answer Device",
            "location": "Invalid Location",
            "ip_address": "192.168.1.204"
        }
    )
    device_id = device_res.json()["id"]
    
    answer_data = {
        "stream_id": "invalid_stream_id",
        "sdp": "v=0\r\n...",
        "type": "answer"
    }
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=answer_data
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_stream_status_no_active_stream(client: AsyncClient, test_user_token):
    """测试获取无活跃流的状态"""
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Status Test Device",
            "location": "Status Location",
            "ip_address": "192.168.1.205"
        }
    )
    device_id = device_res.json()["id"]
    
    response = await client.get(
        f"/api/v1/devices/{device_id}/stream/status",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert data["is_active"] is False
    assert data["connection_state"] == "disconnected"


@pytest.mark.asyncio
async def test_get_stream_status_with_active_stream(client: AsyncClient, test_user_token):
    """测试获取有活跃流的状态"""
    # 创建设备并启动流
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Active Stream Device",
            "location": "Active Location",
            "ip_address": "192.168.1.206"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    # 获取offer并发送answer（启动流）
    offer_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    stream_id = offer_res.json()["stream_id"]
    
    await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "stream_id": stream_id,
            "sdp": "v=0\r\n...",
            "type": "answer"
        }
    )
    
    # 获取状态
    response = await client.get(
        f"/api/v1/devices/{device_id}/stream/status",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert data["is_active"] is True
    assert data["stream_id"] == stream_id
    assert data["connection_state"] == "connected"


@pytest.mark.asyncio
async def test_control_stream_toggle_overlay(client: AsyncClient, test_user_token):
    """测试切换流覆盖层"""
    # 创建设备并启动流
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Control Test Device",
            "location": "Control Location",
            "ip_address": "192.168.1.207"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线并启动流
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    offer_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    stream_id = offer_res.json()["stream_id"]
    
    await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "stream_id": stream_id,
            "sdp": "v=0\r\n...",
            "type": "answer"
        }
    )
    
    # 切换覆盖层
    control_data = {
        "action": "toggle_overlay",
        "enable_overlay": True
    }
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/stream/control",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=control_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["detection_overlay_enabled"] is True


@pytest.mark.asyncio
async def test_control_stream_set_quality(client: AsyncClient, test_user_token):
    """测试设置流质量"""
    # 创建设备并启动流
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Quality Control Device",
            "location": "Quality Control Location",
            "ip_address": "192.168.1.208"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线并启动流
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    offer_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    stream_id = offer_res.json()["stream_id"]
    
    await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "stream_id": stream_id,
            "sdp": "v=0\r\n...",
            "type": "answer"
        }
    )
    
    # 设置质量
    control_data = {
        "action": "set_quality",
        "quality": "high"
    }
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/stream/control",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=control_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["quality"] == "high"


@pytest.mark.asyncio
async def test_control_stream_missing_parameter(client: AsyncClient, test_user_token):
    """测试控制流时缺少必需参数"""
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Missing Param Device",
            "location": "Missing Location",
            "ip_address": "192.168.1.209"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线并启动流
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    offer_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    stream_id = offer_res.json()["stream_id"]
    
    await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "stream_id": stream_id,
            "sdp": "v=0\r\n...",
            "type": "answer"
        }
    )
    
    # 缺少enable_overlay参数
    control_data = {
        "action": "toggle_overlay"
    }
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/stream/control",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=control_data
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_stop_stream(client: AsyncClient, test_user_token):
    """测试停止流"""
    # 创建设备并启动流
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Stop Stream Device",
            "location": "Stop Location",
            "ip_address": "192.168.1.210"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线并启动流
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    offer_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/offer",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    stream_id = offer_res.json()["stream_id"]
    
    await client.post(
        f"/api/v1/devices/{device_id}/stream/answer",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "stream_id": stream_id,
            "sdp": "v=0\r\n...",
            "type": "answer"
        }
    )
    
    # 停止流
    response = await client.delete(
        f"/api/v1/devices/{device_id}/stream",
        headers={"Authorization": f"Bearer {test_user_token}"},
        params={"stream_id": stream_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped"
    assert data["stream_id"] == stream_id
    
    # 验证流已停止
    status_res = await client.get(
        f"/api/v1/devices/{device_id}/stream/status",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert status_res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_stop_stream_invalid_stream_id(client: AsyncClient, test_user_token):
    """测试停止不存在的流"""
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Invalid Stop Device",
            "location": "Invalid Stop Location",
            "ip_address": "192.168.1.211"
        }
    )
    device_id = device_res.json()["id"]
    
    response = await client.delete(
        f"/api/v1/devices/{device_id}/stream",
        headers={"Authorization": f"Bearer {test_user_token}"},
        params={"stream_id": "invalid_stream_id"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_stream_offer_different_qualities(client: AsyncClient, test_user_token):
    """测试不同质量级别的offer"""
    device_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Quality Levels Device",
            "location": "Quality Levels Location",
            "ip_address": "192.168.1.212"
        }
    )
    device_id = device_res.json()["id"]
    
    # 设置设备在线
    await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers={"X-Device-Token": device_res.json()["device_token"]},
        json={"status": "online"}
    )
    
    # 测试不同质量级别
    for quality in ["low", "medium", "high"]:
        response = await client.get(
            f"/api/v1/devices/{device_id}/stream/offer",
            headers={"Authorization": f"Bearer {test_user_token}"},
            params={"quality": quality}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sdp" in data
        assert "stream_id" in data
