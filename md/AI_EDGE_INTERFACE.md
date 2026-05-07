# AI Edge Interface

本文档记录 Edge 与后端、SRS、前端控制链路之间的当前接口约定。实现以 `ai_edge_system/src/core/device_config.py`、`uploader.py`、`streamer.py` 和 `src/api/stream_control_server.py` 为准。

## 1. 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BACKEND_URL` | `http://localhost:8000/api/v1` | 后端 API 基础地址 |
| `EDGE_HOST` | 自动探测或 `127.0.0.1` | Edge 主机地址，用于 bootstrap |
| `BOOTSTRAP_SECRET` | 空 | 与后端 `BOOTSTRAP_SECRET` 对应 |
| `DEVICE_TOKEN` | 空或旧默认值 | 设备 token，用于 `/devices/me` 和上传 |
| `DEVICE_ID` | 空 | 旧部署方式中的设备 ID |

## 2. Bootstrap 配置

Edge 首选接口：

```http
GET /api/v1/devices/bootstrap?edge_host=127.0.0.1
GET /api/v1/devices/bootstrap?edge_host=192.168.1.10&secret=shared-secret
```

成功响应包含：

```json
{
  "id": 1,
  "device_token": "generated-token",
  "name": "井口动火监控点",
  "ip_address": "rtsp://camera/stream",
  "location": "一号矿区",
  "edge_host": "127.0.0.1"
}
```

Edge 使用该响应更新本地 `DeviceConfig`，并启动心跳和告警上传。

## 3. Token 配置回退

如果 bootstrap 失败且配置了 `DEVICE_TOKEN`，Edge 调用：

```http
GET /api/v1/devices/me
X-Device-Token: <device_token>
```

该方式适用于已有 token 的部署。若 `/devices/me` 也失败，Edge 才尝试旧的 `DEVICE_ID` + `DEVICE_TOKEN` 环境变量。

## 4. 心跳接口

```http
POST /api/v1/devices/{device_id}/heartbeat
X-Device-Token: <device_token>
```

Edge 默认每 30 秒发送一次心跳。后端用心跳更新设备在线状态和 `last_heartbeat`。

## 5. 告警上传接口

```http
POST /api/v1/alerts/
X-Device-Token: <device_token>
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `image` | JPEG 文件 | 当前帧或证据图 |
| `alert_data` | JSON 字符串 | 告警类型、等级、消息和时间 |

`alert_data` 示例：

```json
{
  "type": "fire_violation",
  "level": "WARNING",
  "message": "检测到火焰风险",
  "timestamp": 1777456800.0
}
```

## 6. 人脸库同步

后端人脸库接口：

```http
GET /api/v1/faces/
GET /api/v1/faces/{face_id}/image
POST /api/v1/faces/
```

Edge 的人脸客户端用于同步授权人员图片，供本地识别逻辑使用。上传接口一般由后台管理端或维护脚本使用。

## 7. Edge 控制服务

Edge 本地控制服务用于后端发起推流控制。默认端口由后端 `EDGE_CONTROL_PORT=8080` 决定，主机地址优先使用设备 `edge_host`。

控制能力包括：

- 开始推流。
- 本机摄像头索引（如 `0`）使用 OpenCV DirectShow 后端（`CAP_DSHOW`）。
- RTSP/RTMP/HTTP 源使用 OpenCV FFmpeg 后端（`CAP_FFMPEG`），RTSP 强制 TCP，并设置小缓冲降低延迟。
- 网络流读帧失败时会尝试重连；H264 偶发坏帧告警不一定表示链路不可用。
- `.local` 主机名依赖 mDNS/Bonjour，在 Windows 上可能无法解析；现场部署时优先使用摄像头实际 IP 的 RTSP URL。

- 切换检测覆盖层。
- 设置推流质量。
- 查询本地流状态。

后端对外统一提供 `/api/v1/devices/{device_id}/stream/*`，前端不直接调用 Edge 控制服务。

## 8. 推流接口

Edge 推送到 SRS：

```text
rtmp://localhost:1935/live/{stream_id}
```

`stream_id` 由后端流服务生成并传给 Edge。前端通过后端获取 WHEP 播放地址，不直接拼接 RTMP 地址。


### 8.1 视频源打开策略

- 本机摄像头索引（如 `0`）使用 OpenCV DirectShow 后端（`CAP_DSHOW`）。
- RTSP/RTMP/HTTP 源使用 OpenCV FFmpeg 后端（`CAP_FFMPEG`），RTSP 强制 TCP，并设置小缓冲降低延迟。
- 网络流读帧失败时会尝试重连；H264 偶发坏帧告警不一定表示链路不可用。
- `.local` 主机名依赖 mDNS/Bonjour，在 Windows 上可能无法解析；现场部署时优先使用摄像头实际 IP 的 RTSP URL。

### 8.2 并发限制

当前 AI Edge 进程是单设备/单视频源模型：主窗口只有一个采集对象、一个检测循环和一个推流器；本地控制服务也只有一个全局推流状态。新的 API 推流请求会停止旧的 API 推流。多设备并行建议先采用多个 AI Edge 进程分别绑定不同设备。

### 8.3 本地代理

Edge 访问后端的 bootstrap、心跳、告警和人脸同步请求会绕过系统环境代理，避免 `localhost` 或局域网请求被 `HTTP_PROXY`/`ALL_PROXY` 误导到外部代理。

## 9. 质量参数

| 质量 | 分辨率 | FPS | 码率 |
| --- | --- | --- | --- |
| `low` | 640x480 | 15 | 500 kbps |
| `medium` | 1280x720 | 25 | 1500 kbps |
| `high` | 1920x1080 | 30 | 3000 kbps |

## 10. 接口维护规则

- 设备配置字段变化时，同步更新后端 schema、前端类型和本文档。
- Edge 上传告警字段变化时，同步更新 `BACKEND_INTERFACE.md`。
- 视频流控制参数变化时，同步更新 `STREAMING_SETUP.md` 和前端 `streams.ts` 说明。
- Edge 上传告警字段变化时，同步更新 `BACKEND_INTERFACE.md`。
- 视频流控制参数变化时，同步更新 `STREAMING_SETUP.md` 和前端 `streams.ts` 说明。
