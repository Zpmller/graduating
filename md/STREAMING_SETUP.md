# 视频流端到端配置

系统视频链路为：

```text
Edge 标注帧
  -> FFmpeg RTMP 推流
  -> SRS
  -> WHEP/WebRTC
  -> Backend 流接口协调
  -> Frontend 播放
```

## 1. 服务端口

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| SRS RTMP | `rtmp://localhost:1935` | Edge 推流入口 |
| SRS HTTP API/WHEP | `http://localhost:1985` | 后端和前端播放链路使用 |
| SRS HTTP 备用 | `http://localhost:8080` | HTTP-FLV/HLS 备用端口 |
| SRS WebRTC UDP | `8000/udp` | WebRTC 媒体传输 |
| Backend | `http://localhost:8000` | 后端 REST API |
| Frontend | `http://localhost:5173` | Web 看板 |

## 2. 启动顺序

推荐使用根目录脚本：

```bat
start_system.bat
```

手动启动时按以下顺序：

```bash
docker compose up -d
cd backend_system
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd ../ai_edge_system
python main.py
cd ../frontend_dashboard
npm run dev
```

## 3. SRS 配置

`docker-compose.yml` 使用 `ossrs/srs:5`，启动命令为：

```text
./objs/srs -c conf/rtmp2rtc.conf
```

本机访问时 `CANDIDATE` 默认是 `127.0.0.1`。局域网访问时，应将 `docker-compose.yml` 中的 `CANDIDATE` 改为实际局域网 IP，否则 WebRTC candidate 可能不可达。

## 4. 后端相关配置

后端流媒体配置位于 `.env` 或 `app/core/config.py`：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_SERVER_URL` | `http://localhost:1985` | SRS HTTP API/WHEP |
| `MEDIA_SERVER_RTMP_URL` | `rtmp://localhost:1935` | Edge 推流根地址 |
| `EDGE_CONTROL_PORT` | `8080` | Edge 控制服务端口 |
| `EDGE_CONTROL_HOST` | 空 | 当设备 `ip_address` 是摄像头地址时，可显式指定 Edge 主机 |

## 5. 前端播放流程

1. 前端调用 `GET /api/v1/devices/{id}/stream/offer?quality=medium`。
2. 后端检查设备和流状态，并通知 Edge 推流。
3. Edge 使用 FFmpeg 推送到 `rtmp://.../live/{stream_id}`。
4. 后端返回 `stream_id` 和相对路径 `whep_url=/stream/whep/{stream_id}`。
5. 前端创建 WebRTC offer，并将 SDP 通过 `POST /api/v1/stream/whep/{stream_id}` 提交给后端。
6. 后端将 WHEP 请求转发到 SRS `/rtc/v1/whep/?app=live&stream={stream_id}`，并把 SRS answer 返回给前端。
7. `/devices/{id}/stream/answer` 仅保留为兼容/状态接口，当前 WHEP 播放主链路不依赖该接口。
8. 播放过程中可调用状态和控制接口。

## 6. Edge 视频源与并发限制

当前 AI Edge 是单设备/单视频源运行模型：

- 桌面主窗口只有一个 `VideoCapture`、一个检测循环和一个 `VideoStreamer`。
- Edge 本地控制服务当前只有一个全局推流状态 `_api_stream_state`。
- 新的推流请求会停止旧的 API 推流；本机摄像头 `0` 已被主窗口监控时，后端触发的推流会复用主窗口处理后的画面，避免重复打开摄像头。

如果需要多设备同时运行，推荐先采用“一个设备启动一个 AI Edge 进程”的部署方式；真正单进程多路并行需要为每个设备拆分独立采集、检测、推流和状态管理。

Edge 打开视频源的策略：

- 本机摄像头索引（如 `0`）使用 OpenCV DirectShow 后端（`CAP_DSHOW`）。
- RTSP/RTMP/HTTP 视频源使用 OpenCV FFmpeg 后端（`CAP_FFMPEG`），RTSP 强制 TCP，并使用小缓冲降低延迟。
- 网络流读帧失败时会尝试重连，避免一次 RTSP 卡顿直接停止监控。

## 7. 常见问题

### 设备离线

检查：

- Edge 是否已启动。
- 后端是否能访问 Edge。
- 设备是否通过 bootstrap 获取到了 `device_id` 和 `device_token`。
- `/devices/{id}/heartbeat` 是否持续成功。

### 有设备但没有视频

检查：

- FFmpeg 是否安装并在命令行可用。
- SRS 容器是否运行。
- Edge 是否收到后端控制请求。
- `MEDIA_SERVER_RTMP_URL` 是否与 SRS RTMP 端口一致。
- `CANDIDATE` 是否为前端可达地址。
- SRS `/api/v1/streams` 中对应流是否 `publish.active=true` 且 `video` 不为 `null`。
- RTSP 源是否可用，可用 `ffprobe -rtsp_transport tcp "<rtsp_url>"` 验证。

### 本地代理导致 WHEP 或 Edge 控制异常

后端访问 SRS/Edge 的内部 HTTP 请求已显式绕过环境代理（`trust_env=False`），避免系统 `HTTP_PROXY`/`ALL_PROXY` 将 `localhost` 请求导向 SOCKS 代理。依赖中使用 `httpx[socks]` 作为兜底，兼容确实需要 SOCKS 的运行环境。

### 前端 WebRTC 连接失败

检查：

- 浏览器控制台的 ICE/WHEP 错误。
- SRS `1985` 端口是否可访问。
- Docker `8000/udp` 是否开放。
- 后端 `/devices/{id}/stream/status` 返回的 `connection_state` 和 `error`。

## 8. 验证命令

```bash
docker ps
curl http://localhost:1985/api/v1/versions
curl http://localhost:8000/api/v1/system/health
```

Windows PowerShell 可使用：

```powershell
Invoke-WebRequest http://localhost:1985/api/v1/versions
Invoke-WebRequest http://localhost:8000/api/v1/system/health
```
