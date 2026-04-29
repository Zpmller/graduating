#!/usr/bin/env python3
"""
将本地 face_db 目录下的所有人脸图片自动上传到后端数据库。
用法（在 ai_edge_system 目录下执行）:
  python upload_face_db_to_backend.py
  BACKEND_URL=http://your-server:8000/api/v1 python upload_face_db_to_backend.py
"""
import os
import sys

# 确保可导入 src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.face_client import FaceClient


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    face_db_path = os.path.join(base_dir, "data", "face_db")
    if not os.path.isdir(face_db_path):
        print(f"本地人脸库目录不存在: {face_db_path}")
        return 1

    client = FaceClient()
    print(f"后端地址: {client.backend_url}")
    total = 0
    ok = 0
    for person_name in os.listdir(face_db_path):
        person_dir = os.path.join(face_db_path, person_name)
        if not os.path.isdir(person_dir):
            continue
        for fn in os.listdir(person_dir):
            path = os.path.join(person_dir, fn)
            if not os.path.isfile(path):
                continue
            lower = fn.lower()
            if not (lower.endswith(".jpg") or lower.endswith(".jpeg") or lower.endswith(".png")):
                continue
            total += 1
            with open(path, "rb") as f:
                content = f.read()
            success, msg = client.upload_face(content, person_name)
            if success:
                ok += 1
                print(f"  [OK] {person_name}/{fn}")
            else:
                print(f"  [FAIL] {person_name}/{fn}: {msg}")
    print(f"上传完成: {ok}/{total} 张")
    return 0 if (total == 0 or ok == total) else 1


if __name__ == "__main__":
    sys.exit(main())
