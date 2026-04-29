"""
视频流服务：管理与 Media Server (SRS) 的交互
Edge 推 RTMP -> SRS -> 前端 WHEP 播放 WebRTC
"""
import asyncio
import json
import time
import uuid
from pathlib import Path
import httpx
from urllib.parse import urlparse
from typing import Optional, Dict, Literal
from app.core.config import settings


def _debug_log(location: str, message: str, data: dict, hypothesis_id: str = "H2"):
    # #region agent log
    try:
        _ws_root = Path(__file__).resolve().parents[3]
        log_path = _ws_root / "debug-870502.log"
        payload = {
            "sessionId": "870502",
            "timestamp": 0,
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        }
        payload["timestamp"] = int(time.time() * 1000)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion


class StreamService:
    """视频流服务"""

    def __init__(self):
        self.media_server_url = getattr(settings, "MEDIA_SERVER_URL", "http://localhost:1985")
        self.media_server_rtmp_url = getattr(
            settings, "MEDIA_SERVER_RTMP_URL", "rtmp://localhost:1935"
        )
        self.media_server_rtsp_url = getattr(
            settings, "MEDIA_SERVER_RTSP_URL", "rtsp://localhost:8554"
        )
        self.media_server_ws_url = getattr(settings, "MEDIA_SERVER_WS_URL", "ws://localhost:8080")
        self.edge_control_port = getattr(settings, "EDGE_CONTROL_PORT", 8080)
        self.edge_control_host = getattr(settings, "EDGE_CONTROL_HOST", "") or ""
        self.active_streams: Dict[str, Dict] = {}

    def generate_stream_id(self, device_id: int) -> str:
        """生成唯一的流ID"""
        return f"stream_{device_id}_{uuid.uuid4().hex[:8]}"

    async def create_offer(
        self,
        device_id: int,
        quality: Literal["low", "medium", "high"] = "medium",
    ) -> Dict:
        """
        创建 WebRTC 播放信息（WHEP）
        Edge 推 RTMP 到 SRS，前端通过 WHEP 从 SRS 拉 WebRTC 流
        """
        existing_streams = [
            sid for sid, info in self.active_streams.items()
            if info["device_id"] == device_id
        ]
        for sid in existing_streams:
            await self.stop_stream(device_id, sid)

        stream_id = self.generate_stream_id(device_id)

        quality_config = {
            "low": {"width": 640, "height": 480, "fps": 15, "bitrate": 500000},
            "medium": {"width": 1280, "height": 720, "fps": 25, "bitrate": 1500000},
            "high": {"width": 1920, "height": 1080, "fps": 30, "bitrate": 3000000},
        }
        config = quality_config[quality]

        # RTMP 推流地址（Edge 推送到 SRS）
        rtmp_push_url = f"{self.media_server_rtmp_url}/live/{stream_id}"

        # WHEP 代理 URL（相对路径，前端会拼上 baseURL）
        whep_url = f"/stream/whep/{stream_id}"

        self.active_streams[stream_id] = {
            "device_id": device_id,
            "stream_id": stream_id,
            "quality": quality,
            "rtmp_push_url": rtmp_push_url,
            "whep_url": whep_url,
            "config": config,
            "status": "connecting",
        }

        return {
            "stream_id": stream_id,
            "whep_url": whep_url,
            "rtmp_push_url": rtmp_push_url,  # 给 Edge 用
            "sdp": None,  # 前端用 WHEP 自建 offer
            "type": "offer",
            "websocket_url": None,
        }

    async def wait_for_stream(
        self, stream_id: str, timeout: float = 10.0, interval: float = 0.5
    ) -> bool:
        """
        轮询 SRS 直到该流已存在且 publish 活跃，避免前端 WHEP 时无源导致 track_muted 黑屏。
        返回 True 表示已就绪，False 表示超时。
        """
        # 使用带尾部斜杠的路径并跟随重定向，避免 SRS 返回 302 导致拿不到 JSON
        api_url = f"{self.media_server_url.rstrip('/')}/api/v1/streams/"
        deadline = time.monotonic() + timeout
        first_poll_logged = False
        last_status = None
        last_streams_count = None
        while time.monotonic() < deadline:
            try:
                async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                    resp = await client.get(f"{api_url}?count=50")
                last_status = resp.status_code
                if resp.status_code != 200:
                    if not first_poll_logged:
                        _debug_log("stream_service:wait_for_stream", "srs api non-200", {"status_code": resp.status_code, "stream_id": stream_id})
                        first_poll_logged = True
                    await asyncio.sleep(interval)
                    continue
                data = resp.json()
                streams_list = data.get("streams") if isinstance(data.get("streams"), list) else []
                last_streams_count = len(streams_list)
                if not first_poll_logged:
                    first_stream_keys = list(streams_list[0].keys()) if streams_list and isinstance(streams_list[0], dict) else []
                    fs = streams_list[0] if streams_list and isinstance(streams_list[0], dict) else {}
                    pub = fs.get("publish") if isinstance(fs.get("publish"), dict) else {}
                    _debug_log("stream_service:wait_for_stream", "srs api 200", {
                        "stream_id": stream_id,
                        "data_keys": list(data.keys()),
                        "streams_count": len(streams_list),
                        "first_stream_keys": first_stream_keys,
                        "first_stream_name": fs.get("name"),
                        "first_stream_stream": fs.get("stream"),
                        "first_publish_active": pub.get("active"),
                    })
                    first_poll_logged = True
                for s in streams_list:
                    if not isinstance(s, dict):
                        continue
                    sname = s.get("name") or s.get("stream") or ""
                    if sname == stream_id:
                        pub = s.get("publish") if isinstance(s.get("publish"), dict) else {}
                        if pub.get("active"):
                            _debug_log("stream_service:wait_for_stream", "stream ready", {"stream_id": stream_id})
                            return True
                await asyncio.sleep(interval)
            except Exception as e:
                if not first_poll_logged:
                    _debug_log("stream_service:wait_for_stream", "srs api error", {"stream_id": stream_id, "detail": str(e)})
                    first_poll_logged = True
                await asyncio.sleep(interval)
        _debug_log("stream_service:wait_for_stream", "timeout", {"stream_id": stream_id, "last_status": last_status, "last_streams_count": last_streams_count})
        return False

    async def process_answer(self, stream_id: str, answer_sdp: str) -> Dict:
        """处理 answer（用于状态跟踪，实际 WebRTC 由前端直连 SRS）"""
        if stream_id not in self.active_streams:
            raise ValueError(f"Stream {stream_id} not found")
        self.active_streams[stream_id]["status"] = "connected"
        return {"status": "connected", "stream_id": stream_id}

    def get_stream_status(self, device_id: int) -> Optional[Dict]:
        """获取设备的流状态"""
        for stream_id, stream_info in self.active_streams.items():
            if stream_info["device_id"] == device_id and stream_info["status"] in (
                "connecting",
                "connected",
            ):
                return {
                    "device_id": device_id,
                    "is_active": True,
                    "stream_id": stream_id,
                    "quality": stream_info["quality"],
                    "detection_overlay_enabled": stream_info.get("detection_overlay_enabled", False),
                    "connection_state": stream_info["status"],
                    "error": None,
                }
        return {
            "device_id": device_id,
            "is_active": False,
            "stream_id": None,
            "quality": None,
            "detection_overlay_enabled": False,
            "connection_state": "disconnected",
            "error": None,
        }

    async def control_stream(
        self,
        device_id: int,
        action: Literal["start", "stop", "toggle_overlay", "set_quality"],
        **kwargs,
    ) -> Dict:
        """控制流"""
        stream_info = None
        for _sid, info in self.active_streams.items():
            if info["device_id"] == device_id:
                stream_info = info
                break
        if not stream_info:
            raise ValueError(f"No active stream found for device {device_id}")
        if action == "toggle_overlay":
            stream_info["detection_overlay_enabled"] = kwargs.get("enable_overlay", True)
        elif action == "set_quality":
            stream_info["quality"] = kwargs.get("quality", "medium")
        elif action == "stop":
            await self.stop_stream(device_id, stream_info["stream_id"])
            return self.get_stream_status(device_id)
        return self.get_stream_status(device_id)

    async def stop_stream(self, device_id: int, stream_id: str) -> Dict:
        """停止流"""
        if stream_id not in self.active_streams:
            raise ValueError(f"Stream {stream_id} not found")
        info = self.active_streams[stream_id]
        if info["device_id"] != device_id:
            raise ValueError(f"Stream {stream_id} does not belong to device {device_id}")
        del self.active_streams[stream_id]
        return {"status": "stopped", "stream_id": stream_id}

    def _get_edge_host(self, source_url: str, edge_host: Optional[str] = None) -> str:
        """
        获取 Edge 控制主机地址（通知推流的目标）
        优先级：edge_host(DB) > EDGE_CONTROL_HOST(env) > 解析 source_url
        注意：source_url 为 RTSP 时解析出的是摄像头 IP，无法送达 Edge，需在 DB 填 edge_host
        """
        if edge_host and edge_host.strip():
            return edge_host.strip()
        if self.edge_control_host:
            return self.edge_control_host.strip()
        if not source_url:
            return "127.0.0.1"
        if "://" in source_url:
            # RTSP/HTTP：host 通常是摄像头，非 Edge
            parsed = urlparse(source_url)
            hn = parsed.hostname or ""
            if hn in ("localhost", "127.0.0.1"):
                return "127.0.0.1"
            # 远程摄像头地址：解析出的是摄像头 IP，无法送达 Edge → 回退 127.0.0.1（同机部署）
            # 若 Edge 在其它机器，必须在设备中填写 edge_host
            return "127.0.0.1"
        # 纯数字或 "0"：本机摄像头，Edge 同机部署 → 127.0.0.1
        if source_url.isdigit() or source_url in ("0", ""):
            return "127.0.0.1"
        return source_url  # 纯 IP（少见）

    async def notify_edge_node_start_stream(
        self,
        source_url: str,
        device_id: int,
        stream_id: str,
        rtmp_push_url: str,
        quality: str,
        edge_host: Optional[str] = None,
    ):
        """
        通知 Edge Node 开始推流（HTTP POST）
        source_url: 视频源地址（数据库 ip_address，RTSP/HTTP/0 等）
        edge_host: Edge 所在主机 IP，必须正确才能送达；ip_address 为 RTSP 时解析出的是摄像头 IP
        """
        host = self._get_edge_host(source_url, edge_host)
        url = f"http://{host}:{self.edge_control_port}/api/stream/control"
        payload = {
            "action": "start_stream",
            "stream_id": stream_id,
            "rtsp_push_url": rtmp_push_url,  # 保持字段名兼容，实际为 rtmp
            "quality": quality,
            "source_url": source_url,  # 数据库中的视频源地址，Edge 拉流用
            "device_id": device_id,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
                # #region agent log
                _debug_log("stream_service:notify_edge", "Edge notify result", {"url": url, "status_code": resp.status_code, "stream_id": stream_id})
                # #endregion
                if resp.status_code >= 400:
                    print(f"[StreamService] Edge notify failed {resp.status_code}: {resp.text}")
                else:
                    print(f"[StreamService] Edge notified: {url} -> {stream_id}")
        except Exception as e:
            # #region agent log
            _debug_log("stream_service:notify_edge", "Edge notify exception", {"url": url, "detail": str(e)})
            # #endregion
            print(f"[StreamService] Failed to notify Edge at {url}: {e}")

    def reset(self):
        """重置服务状态（用于测试）"""
        self.active_streams.clear()


# 创建单例
stream_service = StreamService()
