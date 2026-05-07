import threading
import queue
import requests
import json
import cv2
import time
import os
from datetime import datetime

# 心跳间隔（秒），保持设备在线
HEARTBEAT_INTERVAL = 30


class AlertUploader:
    def __init__(self, backend_url=None, device_token=None, device_id=None):
        self.backend_url = (backend_url or os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")).rstrip("/")
        self.device_token = device_token or os.getenv("DEVICE_TOKEN", "dev_token_default_001")
        _did = device_id if device_id is not None else os.getenv("DEVICE_ID")
        self.device_id = int(_did) if _did not in (None, "") else None
        self.queue = queue.Queue(maxsize=100)
        self.running = True
        self._heartbeat_thread = None
        self._heartbeat_stop = threading.Event()
        self._session = requests.Session()
        self._session.trust_env = False

        self.thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.thread.start()

        if self.device_id is not None:
            self._start_heartbeat()

        print(f"[Uploader] Initialized with Backend: {self.backend_url}")
        print(f"[Uploader] Device Token: {self.device_token}, Device ID: {self.device_id}")

    def set_device_config(self, device_id: int, device_token: str, backend_url: str = None):
        """
        设置/更新设备配置（用于 Edge 启动后从后端自动获取的配置）
        配置生效后会启动心跳，使设备显示为在线
        """
        if device_id is None or not device_token:
            return
        self.device_id = int(device_id)
        self.device_token = device_token
        if backend_url:
            self.backend_url = backend_url.rstrip("/")
        self._start_heartbeat()
        print(f"[Uploader] Device config updated: device_id={self.device_id}")

    def add_alert(self, alert_data, frame):
        """
        Add an alert to the upload queue.
        :param alert_data: Dictionary containing alert info (type, level, message, timestamp)
        :param frame: OpenCV image (numpy array)
        """
        if self.queue.full():
            print("[Uploader] Queue full, dropping alert!")
            return
            
        self.queue.put((alert_data, frame.copy()))

    def _start_heartbeat(self):
        """后台定时向后端发送心跳，使设备显示为在线"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        print(f"[Uploader] Heartbeat started for device_id={self.device_id}")

    def _heartbeat_loop(self):
        while not self._heartbeat_stop.wait(timeout=HEARTBEAT_INTERVAL):
            if self.device_id is None:
                break
            try:
                url = f"{self.backend_url}/devices/{self.device_id}/heartbeat"
                r = self._session.post(
                    url,
                    headers={"X-Device-Token": self.device_token},
                    timeout=5,
                )
                if r.status_code == 200:
                    pass  # 静默成功
                else:
                    print(f"[Uploader] Heartbeat failed: {r.status_code} {r.text[:200]}")
            except requests.exceptions.ConnectionError:
                print(f"[Uploader] Heartbeat: cannot connect to {self.backend_url}")
            except Exception as e:
                print(f"[Uploader] Heartbeat error: {e}")

    def stop(self):
        self.running = False
        self._heartbeat_stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
        self.thread.join(timeout=1.0)

    def _upload_loop(self):
        while self.running:
            try:
                # Get alert from queue with timeout
                item = self.queue.get(timeout=1.0)
                alert_data, frame = item
                
                self._send_request(alert_data, frame)
                
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Uploader] Error in upload loop: {e}")

    def _send_request(self, alert_data, frame):
        url = f"{self.backend_url}/alerts/"
        headers = {
            "X-Device-Token": self.device_token
        }
        
        # Prepare JSON payload
        # Ensure keys match Backend AlertCreate Schema: type, level, message, timestamp
        payload = {
            "type": alert_data.get("type", "unknown_violation"),
            "level": alert_data.get("level", "WARNING"),
            "message": alert_data.get("message", "No description"),
            "timestamp": alert_data.get("timestamp", time.time())
        }
        
        # Encode image
        try:
            is_success, buffer = cv2.imencode(".jpg", frame)
            if not is_success:
                print("[Uploader] Failed to encode image")
                return
                
            files = {
                "image": ("evidence.jpg", buffer.tobytes(), "image/jpeg"),
                "alert_data": (None, json.dumps(payload), "application/json")
            }
            
            response = self._session.post(url, headers=headers, files=files, timeout=5)
            
            if response.status_code == 201:
                print(f"[Uploader] Alert uploaded successfully: {payload['type']}")
            else:
                print(f"[Uploader] Upload failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"[Uploader] Connection Error: Could not connect to {self.backend_url}")
        except Exception as e:
            print(f"[Uploader] Error sending request: {e}")
