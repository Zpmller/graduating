
import pytest
from httpx import AsyncClient
import yaml

@pytest.mark.asyncio
async def test_get_calibration_yaml(client: AsyncClient, test_user_token):
    # 1. Create a device (as Admin)
    device_data = {
        "name": "Sync Test Device",
        "location": "Sync Lab",
        "ip_address": "192.168.1.205"
    }
    create_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=device_data
    )
    assert create_res.status_code == 201
    device = create_res.json()
    device_id = device["id"]
    device_token = device["device_token"] # In real app, this is returned or known

    # 2. Upload a config (as Admin)
    valid_yaml = """
camera_matrix: [[1000, 0, 320], [0, 1000, 240], [0, 0, 1]]
dist_coeffs: [0.1, -0.05, 0, 0, 0]
"""
    files = {'file': ('config.yaml', valid_yaml, 'text/yaml')}
    await client.post(
        f"/api/v1/devices/{device_id}/calibration/yaml",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )

    # 3. Get config (as Device)
    # Using X-Device-Token
    res = await client.get(
        f"/api/v1/devices/{device_id}/calibration/yaml",
        headers={"X-Device-Token": device_token}
    )
    
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/x-yaml"
    assert "camera_matrix" in res.text

    # 4. Test invalid token
    res_fail = await client.get(
        f"/api/v1/devices/{device_id}/calibration/yaml",
        headers={"X-Device-Token": "wrong_token"}
    )
    assert res_fail.status_code == 401  # 无效token应该返回401 Unauthorized

    # 5. Test ID mismatch (Token valid for Device A, but requesting Device B)
    # Create Device B
    device_b_data = {"name": "Device B", "location": "Lab", "ip_address": "1.1.1.1"}
    res_b = await client.post("/api/v1/devices/", headers={"Authorization": f"Bearer {test_user_token}"}, json=device_b_data)
    device_b_id = res_b.json()["id"]
    
    res_mismatch = await client.get(
        f"/api/v1/devices/{device_b_id}/calibration/yaml",
        headers={"X-Device-Token": device_token} # Token for Device A
    )
    assert res_mismatch.status_code == 403  # 设备ID不匹配应该返回403 Forbidden
