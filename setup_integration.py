import requests
import os
import sys
import json
import time

BACKEND_URL = "http://localhost:8000"
API_V1_STR = "/api/v1"

def check_backend():
    try:
        response = requests.get(f"{BACKEND_URL}/")
        if response.status_code == 200:
            print("✅ Backend is reachable.")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Backend is NOT reachable.")
        print("Please start the backend server first:")
        print("  cd backend_system")
        print("  uvicorn app.main:app --reload")
        return False
    return False

def login(username, password):
    print(f"Attempting to login as {username}...")
    url = f"{BACKEND_URL}{API_V1_STR}/auth/login/access-token"
    payload = {
        "username": username,
        "password": password
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, data=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ Login successful.")
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def create_device(token, name="Integration_Test_Device"):
    print(f"Creating device '{name}'...")
    url = f"{BACKEND_URL}{API_V1_STR}/devices/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Random IP to avoid conflict if running multiple times without cleanup
    import random
    payload = {
        "name": name,
        "location": "Integration Test Lab",
        "ip_address": f"192.168.1.{random.randint(100, 254)}",
        "type": "camera"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 201:
        print("✅ Device created successfully.")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        # Try to find existing device? Or just create a new one with different name?
        # For now, let's assume we can create multiple or just fail.
        print(f"⚠️ Device might already exist: {response.text}")
        # Try to list devices and find it?
        return None
    else:
        print(f"❌ Failed to create device: {response.status_code} - {response.text}")
        return None

def update_env_file(device_data):
    env_path = os.path.join("ai_edge_system", ".env")
    
    print(f"Updating {env_path}...")
    
    new_content = ""
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                if not line.startswith("DEVICE_TOKEN") and not line.startswith("DEVICE_ID") and not line.startswith("BACKEND_URL"):
                    new_content += line
    
    # Append new config
    if not new_content.endswith("\n") and new_content:
        new_content += "\n"
        
    new_content += f"BACKEND_URL={BACKEND_URL}{API_V1_STR}\n"
    new_content += f"DEVICE_TOKEN={device_data['device_token']}\n"
    new_content += f"DEVICE_ID={device_data['id']}\n"
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print("✅ .env file updated.")
    print("\nConfiguration Added:")
    print(f"  BACKEND_URL={BACKEND_URL}{API_V1_STR}")
    print(f"  DEVICE_TOKEN={device_data['device_token']}")
    print(f"  DEVICE_ID={device_data['id']}")

def main():
    if not check_backend():
        return
    
    # Default credentials
    username = "admin"
    password = "admin123"
    
    token = login(username, password)
    if not token:
        print("Please check if the database is initialized and the admin user exists.")
        print("You can initialize the DB by running: python backend_system/scripts/init_db.py")
        return
        
    device_data = create_device(token)
    
    if device_data:
        update_env_file(device_data)
        print("\n🎉 Setup Complete! You can now run the AI Edge System.")
        print("Command: cd ai_edge_system && python main.py")

if __name__ == "__main__":
    main()
