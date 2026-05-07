# Backend API Interface

所有业务接口默认以 `http://localhost:8000/api/v1` 为基础路径。后端 OpenAPI 文档位于 `http://localhost:8000/docs`。

## 1. 通用约定

### 认证方式

- 管理端用户接口使用 `Authorization: Bearer <access_token>`。
- Edge 设备接口使用 `X-Device-Token: <device_token>`。
- Bootstrap 可选使用查询参数 `secret=<BOOTSTRAP_SECRET>`。

### 分页格式

设备、告警、任务、用户列表使用分页响应：

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

### 错误格式

后端异常一般返回：

```json
{
  "detail": "错误说明",
  "error_code": "OPTIONAL_CODE"
}
```

## 2. 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/auth/token` | 用户登录，返回 JWT |
| `GET` | `/auth/me` | 获取当前登录用户 |

登录请求：

```json
{
  "username": "admin",
  "password": "password"
}
```

登录响应：

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 3. 用户

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/users/` | 用户分页列表，支持 `skip`、`limit` |
| `POST` | `/users/` | 创建用户 |
| `GET` | `/users/{user_id}` | 获取用户详情 |
| `PUT` | `/users/{user_id}` | 更新用户 |
| `DELETE` | `/users/{user_id}` | 删除用户 |

用户角色：`admin`、`operator`、`viewer`。

## 4. 设备

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/devices/` | 设备分页列表 |
| `POST` | `/devices/` | 创建设备并生成 `device_token` |
| `GET` | `/devices/bootstrap` | Edge 根据 `edge_host` 获取设备配置 |
| `GET` | `/devices/me` | Edge 根据 `X-Device-Token` 获取自身配置 |
| `GET` | `/devices/{device_id}` | 获取设备详情 |
| `PUT` | `/devices/{device_id}` | 更新设备 |
| `POST` | `/devices/{device_id}/heartbeat` | Edge 心跳 |
| `GET` | `/devices/{device_id}/calibration/yaml` | 获取标定 YAML |
| `POST` | `/devices/{device_id}/calibration/yaml` | 上传标定 YAML |
| `POST` | `/devices/{device_id}/calibration/images` | 上传标定图片 |

设备字段：

```json
{
  "id": 1,
  "name": "井口动火监控点",
  "location": "一号矿区",
  "ip_address": "rtsp://camera/stream",
  "edge_host": "127.0.0.1",
  "device_token": "generated-token",
  "status": "online",
  "last_heartbeat": "2026-04-29T10:00:00",
  "calibration_config": "...",
  "created_at": "2026-04-29T10:00:00",
  "updated_at": "2026-04-29T10:00:00"
}
```

设备状态：`online`、`offline`、`maintenance`。

设备列表可传 `include_stream_status=true`，返回每台设备的 `stream_status`。

## 5. 告警

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/alerts/` | Edge 上传告警，支持图片表单 |
| `GET` | `/alerts/` | 告警分页列表 |
| `GET` | `/alerts/stats` | 告警统计 |
| `PUT` | `/alerts/{alert_id}/acknowledge` | 确认告警 |

告警类型：

- `fire_violation`
- `smoke_violation`
- `ppe_violation`
- `distance_violation`
- `access_control`

告警等级：

- `CRITICAL`
- `DANGER`
- `WARNING`

列表筛选参数包括 `skip`、`limit`、`device_id`、`type`、`severity`、`is_acknowledged`、`start_date`、`end_date`。

Edge 上传告警时使用 multipart 表单：

- `image`：证据图片。
- `alert_data`：JSON 字符串，包含 `type`、`level`、`message`、`timestamp`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/tasks/` | 任务分页列表，支持 `skip`、`limit`、`status`、`assignee_id` |
| `POST` | `/tasks/` | 创建任务 |
| `GET` | `/tasks/{task_id}` | 获取任务详情 |
| `PUT` | `/tasks/{task_id}` | 更新任务 |
| `DELETE` | `/tasks/{task_id}` | 删除任务 |

任务状态：`pending`、`in_progress`、`completed`。

任务优先级：`high`、`medium`、`low`。

## 7. 视频流

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/devices/{device_id}/stream/offer` | 获取播放 offer/WHEP 信息，支持 `quality` |
| `POST` | `/devices/{device_id}/stream/answer` | 兼容接口：提交 WebRTC answer 并更新流状态；WHEP 主播放链路不依赖 |
| `GET` | `/devices/{device_id}/stream/status` | 获取流状态 |
| `POST` | `/devices/{device_id}/stream/control` | 控制推流 |
| `DELETE` | `/devices/{device_id}/stream` | 停止指定流 |
| `POST` | `/stream/whep/{stream_id}` | WHEP 转发入口 |

当前播放主流程：前端先请求 /devices/{device_id}/stream/offer，再创建 WebRTC offer，并将 SDP 通过 /stream/whep/{stream_id} 交给后端转发到 SRS。/devices/{device_id}/stream/answer 保留用于兼容旧接口和状态跟踪。

流质量：`low`、`medium`、`high`。

控制动作：`start`、`stop`、`toggle_overlay`、`set_quality`。

流状态响应包含：

```json
{
  "device_id": 1,
  "is_active": true,
  "stream_id": "device_1_medium",
  "quality": "medium",
  "detection_overlay_enabled": true,
  "connection_state": "connected",
  "error": null
}
```

## 8. 人脸库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/faces/` | 上传授权人员人脸图片 |
| `GET` | `/faces/` | 获取人脸记录列表 |
| `GET` | `/faces/{face_id}/image` | 下载/显示人脸图片 |

人脸记录包含 `id`、`person_name`、`file_path`、`created_at`。

## 9. 系统

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/system/health` | 健康检查 |

根路径 `/` 返回服务名称、版本和文档入口。
