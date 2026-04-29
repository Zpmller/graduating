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
4. 后端返回 `stream_id`、`whep_url` 和 offer 信息。
5. 前端创建 WebRTC 连接，并调用 `POST /api/v1/devices/{id}/stream/answer`。
6. 播放过程中可调用状态和控制接口。

## 6. 常见问题

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

### 前端 WebRTC 连接失败

检查：

- 浏览器控制台的 ICE/WHEP 错误。
- SRS `1985` 端口是否可访问。
- Docker `8000/udp` 是否开放。
- 后端 `/devices/{id}/stream/status` 返回的 `connection_state` 和 `error`。

## 7. 验证命令

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
