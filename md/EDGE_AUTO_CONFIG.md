# Edge 自动配置与数据流

Edge 自动配置的目标是让边缘端尽量少写本地配置。现场只需要在后端创建设备，并设置 `edge_host`，Edge 启动后即可从后端获取设备 ID、token、视频源和位置等信息。

## 1. 核心字段

| 字段 | 所属位置 | 说明 |
| --- | --- | --- |
| `edge_host` | 后端设备表 | Edge 所在机器的 IP 或主机名 |
| `ip_address` | 后端设备表 | 摄像头/视频源地址，可为 RTSP URL |
| `device_token` | 后端设备表 | Edge 心跳和告警上传凭证 |
| `BACKEND_URL` | Edge 环境变量 | 后端 `/api/v1` 地址 |
| `EDGE_HOST` | Edge 环境变量 | 显式指定本机可访问地址 |

## 2. 推荐配置流程

1. 启动后端。
2. 在前端设备管理页创建设备。
3. 填写设备名称、位置、视频源地址。
4. 填写 `edge_host`：
   - 后端和 Edge 同机：`127.0.0.1`。
   - 局域网部署：填写 Edge 主机局域网 IP。
5. 启动 Edge。
6. Edge 请求 bootstrap，获得设备配置。
7. Edge 开始心跳和告警上传。

## 3. Bootstrap 请求

Edge 调用：

```http
GET /api/v1/devices/bootstrap?edge_host=<edge_host>
```

如果后端设置了 `BOOTSTRAP_SECRET`：

```http
GET /api/v1/devices/bootstrap?edge_host=<edge_host>&secret=<secret>
```

## 4. 自动探测规则

Edge 获取 `edge_host` 的顺序：

1. 优先使用环境变量 `EDGE_HOST`。
2. 如果 `BACKEND_URL` 指向 localhost，默认使用 `127.0.0.1`。
3. 尝试通过本机网络连接获取对外 IP。
4. 尝试解析主机名。

## 5. 回退规则

如果 bootstrap 失败：

1. 若存在 `DEVICE_TOKEN`，调用 `/devices/me`。
2. 若存在 `DEVICE_ID` 和 `DEVICE_TOKEN`，使用旧方式本地构造设备配置。
3. 若仍失败，Edge 无法启动心跳和后端告警上传，需要检查设备创建和网络配置。

## 6. 心跳数据流

```text
Edge
  -> POST /api/v1/devices/{device_id}/heartbeat
  -> Backend 更新 last_heartbeat/status
  -> Frontend 设备列表显示在线状态
```

默认心跳间隔为 30 秒。后端根据 `HEARTBEAT_TIMEOUT_SECONDS` 和主动检测配置判定设备是否离线。

## 7. 告警数据流

```text
Edge 检测到风险
  -> AlertUploader 队列
  -> POST /api/v1/alerts/
  -> Backend 保存告警和证据图
  -> Frontend 历史告警/总览展示
```

## 8. 视频数据流

```text
Frontend 请求播放
  -> Backend 生成 stream_id 并控制 Edge
  -> Edge FFmpeg 推 RTMP 到 SRS
  -> SRS 转 WHEP/WebRTC
  -> Frontend 播放
```

## 9. 排查重点

- 前端设备里的 `edge_host` 是否等于 Edge 启动时识别到的主机地址。
- `BACKEND_URL` 是否以 `/api/v1` 结尾。
- 后端和 Edge 是否能互相访问。
- 若设置了 `BOOTSTRAP_SECRET`，两端值是否一致。
- Edge 是否持续发送心跳。
