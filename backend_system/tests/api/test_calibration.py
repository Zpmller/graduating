import pytest
from httpx import AsyncClient
import yaml
import os
import cv2
import numpy as np
import sys

def generate_checkerboard_image(rows=9, cols=6, square_size=50):
    """Generate a synthetic checkerboard image with rows x cols INNER CORNERS"""
    # To get rows x cols corners, we need at least (rows+1) x (cols+1) squares
    grid_rows = rows + 1
    grid_cols = cols + 1
    
    width = (grid_cols + 2) * square_size
    height = (grid_rows + 2) * square_size
    img = np.ones((height, width), dtype=np.uint8) * 255
    
    for r in range(grid_rows):
        for c in range(grid_cols):
            if (r + c) % 2 == 1:
                pt1 = ((c + 1) * square_size, (r + 1) * square_size)
                pt2 = ((c + 2) * square_size, (r + 2) * square_size)
                cv2.rectangle(img, pt1, pt2, 0, -1)
                
    return cv2.imencode('.jpg', img)[1].tobytes()

@pytest.mark.asyncio
async def test_upload_calibration_yaml(client: AsyncClient, test_user_token):
    # 1. Create a device first
    device_data = {
        "name": "Calibration Test Device",
        "location": "Lab",
        "ip_address": "192.168.1.200"
    }
    create_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=device_data
    )
    assert create_res.status_code == 201
    device_id = create_res.json()["id"]

    # 2. Upload valid YAML
    valid_yaml = """
    camera_matrix: [[1000, 0, 320], [0, 1000, 240], [0, 0, 1]]
    dist_coeffs: [0.1, -0.05, 0, 0, 0]
    """
    # Create a temporary file for upload
    files = {'file': ('config.yaml', valid_yaml, 'text/yaml')}
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/calibration/yaml",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["calibration_config"] is not None
    # Parse back to check content
    parsed_yaml = yaml.safe_load(data["calibration_config"])
    assert "camera_matrix" in parsed_yaml

    # 3. Upload invalid YAML
    invalid_yaml = "invalid: [yaml: content" # Malformed
    files_invalid = {'file': ('config.yaml', invalid_yaml, 'text/yaml')}
    
    response_invalid = await client.post(
        f"/api/v1/devices/{device_id}/calibration/yaml",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files_invalid
    )
    assert response_invalid.status_code == 400

@pytest.mark.asyncio
async def test_calibrate_with_images(client: AsyncClient, test_user_token):
    # 1. Create a device
    device_data = {
        "name": "Image Calibration Device",
        "location": "Lab 2",
        "ip_address": "192.168.1.201"
    }
    create_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=device_data
    )
    device_id = create_res.json()["id"]

    # 2. Upload images
    # Create valid checkerboard images
    img_content = generate_checkerboard_image()
    
    # Need multiple images for better calibration, but for testing one might pass 
    # if the script allows, but usually we need multiple. 
    # Let's send a few copies (same image won't give depth but corners will be found)
    files = [
        ('files', ('img1.jpg', img_content, 'image/jpeg')),
        ('files', ('img2.jpg', img_content, 'image/jpeg')),
        ('files', ('img3.jpg', img_content, 'image/jpeg'))
    ]
    
    # We are now using the REAL script path configured in .env
    
    response = await client.post(
        f"/api/v1/devices/{device_id}/calibration/images",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )
    
    if response.status_code != 200:
        print(f"Calibration failed. Response: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["calibration_config"] is not None
    
    # Parse YAML to verify structure
    config = yaml.safe_load(data["calibration_config"])
    assert "camera_matrix" in config
    assert "dist_coeffs" in config

@pytest.mark.asyncio
async def test_get_device_includes_calibration(client: AsyncClient, test_user_token):
    # 1. Create device and upload config
    device_data = {
        "name": "Get Config Device",
        "location": "Lab 3",
        "ip_address": "192.168.1.202"
    }
    create_res = await client.post(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=device_data
    )
    device_id = create_res.json()["id"]
    
    valid_yaml = "test: 123"
    files = {'file': ('config.yaml', valid_yaml, 'text/yaml')}
    await client.post(
        f"/api/v1/devices/{device_id}/calibration/yaml",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )
    
    # 2. Get device info
    response = await client.get(
        f"/api/v1/devices/{device_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["calibration_config"] == valid_yaml
