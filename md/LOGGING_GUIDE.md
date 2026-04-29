# 日志与排障指南

本文档用于快速定位心跳、告警上传、视频流和服务启动问题。

## 1. 后端日志

手动启动后端：

```bash
cd backend_system
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

重点观察：

- 启动时数据库连接是否成功。
- CORS 配置是否符合前端地址。
- `/devices/{id}/stream/*` 请求是否到达。
- 上传告警时是否返回 201。
- 设备心跳是否返回 200。

健康检查：

```bash
curl http://localhost:8000/api/v1/system/health
```

PowerShell：

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/system/health
```

## 2. Edge 日志

手动启动：

```bash
cd ai_edge_system
python main.py
```

重点观察：

- `[DeviceConfig] Bootstrap 成功`。
- `[Uploader] Heartbeat started`。
- `[Uploader] Alert uploaded successfully`。
- `[VideoStreamer] FFmpeg process started`。
- `[VideoStreamer] Stream started`。

常见异常：

| 日志 | 含义 | 处理 |
| --- | --- | --- |
| `无法连接后端` | Edge 无法访问 `BACKEND_URL` | 检查后端是否启动、地址是否带 `/api/v1` |
| `未找到 edge_host` | 后端没有匹配设备 | 检查设备 `edge_host` |
| `Heartbeat failed` | token、设备 ID 或后端状态异常 | 检查 `device_token` 和设备记录 |
| `未找到 ffmpeg` | FFmpeg 不在 PATH | 安装 FFmpeg 并加入 PATH |

## 3. SRS 日志

容器状态：

```bash
docker ps
```

查看 SRS 版本接口：

```bash
curl http://localhost:1985/api/v1/versions
```

查看日志：

```bash
docker logs safety-media-server --tail 100
docker logs safety-media-server -f
```

重点观察：

- RTMP `/live/{stream_id}` 是否有 publish。
- WHEP 请求是否到达。
- WebRTC candidate 是否为前端可访问地址。

## 4. 前端日志

启动：

```bash
cd frontend_dashboard
npm run dev
```

浏览器控制台重点观察：

- API 请求是否指向正确后端。
- 登录后是否保存 token。
- `/devices/{id}/stream/offer` 是否成功。
- WebRTC ICE/WHEP 是否报错。

## 5. 快速检查清单

| 问题 | 检查项 |
| --- | --- |
| 登录失败 | 后端是否启动、账号是否存在、CORS 是否允许前端地址 |
| 设备离线 | Edge bootstrap、心跳接口、`edge_host`、token |
| 告警没有出现 | Edge 上传日志、后端 `/alerts/` 响应、证据目录权限 |
| 视频黑屏 | SRS、FFmpeg、RTMP 地址、WHEP 地址、WebRTC candidate |
| 标定上传失败 | 文件类型、后端 `CALIBRATION_TEMP_DIR`、设备 ID |

## 6. 常用地址

- 后端文档：`http://localhost:8000/docs`
- 后端健康：`http://localhost:8000/api/v1/system/health`
- SRS API：`http://localhost:1985/api/v1/versions`
- 前端：`http://localhost:5173`
