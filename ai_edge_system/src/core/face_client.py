"""
人脸库后端客户端：从后端拉取人脸库到本地、注册时上传到后端。
供 Edge 启动时同步人脸库，授权检测时使用本地 face_db（已从数据库同步）。
"""
import os
import requests
import cv2
import numpy as np


class FaceClient:
    """调用后端人脸库 API：上传、拉取列表、下载图片"""

    def __init__(self, backend_url=None, device_token=None):
        self.backend_url = (backend_url or os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")).rstrip("/")
        self.device_token = device_token or os.getenv("DEVICE_TOKEN", "")
        self._session = requests.Session()
        if self.device_token:
            self._session.headers["X-Device-Token"] = self.device_token

    def upload_face(self, face_img, person_name: str, timeout=10):
        """
        上传一张人脸图片到后端人脸库。
        :param face_img: numpy.ndarray (BGR) 或 图片字节
        :param person_name: 授权人员姓名
        :return: (success: bool, message: str)
        """
        try:
            if isinstance(face_img, np.ndarray):
                is_ok, buf = cv2.imencode(".jpg", face_img)
                if not is_ok:
                    return False, "Failed to encode image"
                image_bytes = buf.tobytes()
            else:
                image_bytes = face_img
            files = {"image": ("face.jpg", image_bytes, "image/jpeg")}
            data = {"person_name": person_name}
            r = self._session.post(
                f"{self.backend_url}/faces/",
                files=files,
                data=data,
                timeout=timeout,
            )
            if r.status_code == 201:
                return True, "OK"
            return False, f"{r.status_code}: {r.text[:200]}"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to backend"
        except Exception as e:
            return False, str(e)

    def list_faces(self, timeout=10):
        """
        获取后端人脸记录列表。
        :return: list[dict] 每项 {id, person_name, file_path, created_at}，失败返回 None
        """
        try:
            r = self._session.get(f"{self.backend_url}/faces/", timeout=timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            return data.get("items") or []
        except Exception:
            return None

    def download_face_image(self, face_id: int, timeout=10):
        """
        根据记录 ID 下载人脸图片字节。
        :return: bytes 或 None
        """
        try:
            r = self._session.get(f"{self.backend_url}/faces/{face_id}/image", timeout=timeout)
            if r.status_code != 200:
                return None
            return r.content
        except Exception:
            return None

    def sync_to_local(self, face_db_path: str, timeout=10):
        """
        从后端拉取所有人脸记录，下载图片并保存到本地 face_db 目录。
        目录结构：face_db_path/PersonName/face_id.jpg，与原有 DeepFace 结构兼容。
        :param face_db_path: 本地 face_db 根目录（如 ai_edge_system/data/face_db）
        :return: (success: bool, message: str)
        """
        items = self.list_faces(timeout=timeout)
        if items is None:
            return False, "Failed to list faces from backend"
        if not items:
            return True, "No faces in backend"
        os.makedirs(face_db_path, exist_ok=True)
        saved = 0
        for rec in items:
            person_name = rec.get("person_name") or "unknown"
            face_id = rec.get("id")
            if face_id is None:
                continue
            content = self.download_face_image(face_id, timeout=timeout)
            if not content:
                continue
            person_dir = os.path.join(face_db_path, person_name)
            os.makedirs(person_dir, exist_ok=True)
            path = os.path.join(person_dir, f"{face_id}.jpg")
            with open(path, "wb") as f:
                f.write(content)
            saved += 1
        return True, f"Synced {saved} face image(s) to {face_db_path}"
