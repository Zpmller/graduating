"""
Edge 设备配置模块
从后端自动获取设备信息，支持零配置引导（bootstrap）和 Token 方式（/me）
"""
import os
import socket
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass


def _backend_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


@dataclass
class DeviceConfig:
    """设备配置"""
    device_id: int
    device_token: str
    name: str
    ip_address: Optional[str] = None  # 视频源地址（RTSP/摄像头URL等）
    location: Optional[str] = None
    edge_host: Optional[str] = None
    backend_url: str = "http://localhost:8000/api/v1"


def get_local_ip() -> Optional[str]:
    """获取本机用于对外的 IP 地址"""
    # 1. 环境变量优先（用户可显式指定）
    env_host = os.getenv("EDGE_HOST", "").strip()
    if env_host:
        return env_host
    # 2. 尝试通过连接外网获取本机 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    # 3. 回退到 hostname 解析
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return None


def fetch_bootstrap(
    backend_url: str,
    edge_host: Optional[str] = None,
    bootstrap_secret: Optional[str] = None,
) -> Optional[DeviceConfig]:
    """
    通过 bootstrap API 从后端获取设备配置（零配置方式）
    创建设备时在前端填写 edge_host（Edge 所在机器的 IP），Edge 启动时传入本机 IP 即可
    
    Returns:
        DeviceConfig 或 None（未找到设备或请求失败）
    """
    base = (backend_url or os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")).rstrip("/")
    host = edge_host or get_local_ip()
    if not host:
        print("[DeviceConfig] 无法获取本机 IP，请设置环境变量 EDGE_HOST")
        return None

    url = f"{base}/devices/bootstrap?edge_host={host}"
    if bootstrap_secret:
        url += f"&secret={bootstrap_secret}"

    try:
        r = _backend_session().get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return DeviceConfig(
                device_id=data["id"],
                device_token=data["device_token"],
                name=data.get("name", ""),
                ip_address=data.get("ip_address"),
                location=data.get("location"),
                edge_host=data.get("edge_host"),
                backend_url=base,
            )
        elif r.status_code == 404:
            print(f"[DeviceConfig] 未找到 edge_host={host} 对应的设备，请在前端创建设备并填写该 Edge 的主机地址")
        else:
            print(f"[DeviceConfig] Bootstrap 失败: {r.status_code} {r.text[:200]}")
    except requests.exceptions.ConnectionError:
        print(f"[DeviceConfig] 无法连接后端: {base}")
    except Exception as e:
        print(f"[DeviceConfig] Bootstrap 异常: {e}")
    return None


def fetch_me(
    backend_url: str,
    device_token: str,
) -> Optional[DeviceConfig]:
    """
    通过 /devices/me API 获取设备配置（需要已知 device_token）
    适用于已有 token 时的配置同步
    
    Returns:
        DeviceConfig 或 None
    """
    base = (backend_url or os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")).rstrip("/")
    url = f"{base}/devices/me"

    try:
        r = _backend_session().get(
            url,
            headers={"X-Device-Token": device_token},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return DeviceConfig(
                device_id=data["id"],
                device_token=data["device_token"],
                name=data.get("name", ""),
                ip_address=data.get("ip_address"),
                location=data.get("location"),
                edge_host=data.get("edge_host"),
                backend_url=base,
            )
        else:
            print(f"[DeviceConfig] /me 失败: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[DeviceConfig] /me 异常: {e}")
    return None


def _is_backend_localhost(url: str) -> bool:
    """判断后端是否为本地（同机部署）"""
    return "localhost" in url or "127.0.0.1" in url


def fetch_device_config() -> Optional[DeviceConfig]:
    """
    自动获取设备配置
    优先级：
    1. Bootstrap（零配置）：同机部署时用 127.0.0.1，否则用 EDGE_HOST/本机 IP
    2. /me（Token 方式）：若 bootstrap 失败且已配置 DEVICE_TOKEN，则用 /me 获取
    
    同机部署：无需配置 DEVICE_ID/DEVICE_TOKEN，创建设备时 edge_host 填 127.0.0.1 或留空即可。
    """
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1").rstrip("/")
    bootstrap_secret = os.getenv("BOOTSTRAP_SECRET")
    device_token = os.getenv("DEVICE_TOKEN")

    # 1. 尝试 bootstrap（零配置）
    edge_host = os.getenv("EDGE_HOST", "").strip()
    if not edge_host and _is_backend_localhost(backend_url):
        edge_host = "127.0.0.1"  # 同机部署：后端是 localhost 则用 127.0.0.1
    if not edge_host:
        edge_host = get_local_ip()

    cfg = fetch_bootstrap(
        backend_url=backend_url,
        edge_host=edge_host or None,
        bootstrap_secret=bootstrap_secret,
    )
    if cfg:
        print(f"[DeviceConfig] Bootstrap 成功: device_id={cfg.device_id}, name={cfg.name}")
        return cfg

    # 2. 若有 DEVICE_TOKEN，尝试 /me
    if device_token:
        cfg = fetch_me(backend_url=backend_url, device_token=device_token)
        if cfg:
            print(f"[DeviceConfig] /me 成功: device_id={cfg.device_id}, name={cfg.name}")
            return cfg

    # 3. 回退到环境变量（兼容旧部署方式）
    _did = os.getenv("DEVICE_ID")
    if _did and device_token:
        try:
            return DeviceConfig(
                device_id=int(_did),
                device_token=device_token,
                name=f"Device-{_did}",
                backend_url=backend_url,
            )
        except ValueError:
            pass

    return None
