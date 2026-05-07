# Frontend API Interface

本文档说明前端当前 TypeScript 类型和 API 封装。源码以 `frontend_dashboard/src/api/*.ts` 和 `frontend_dashboard/src/types/api.d.ts` 为准。

## 1. HTTP 客户端

`src/api/axios.ts` 创建统一 `apiClient`：

- 基础地址来自环境变量或默认后端地址。
- 请求时自动带上登录 token。
- 响应拦截器统一抽取数据和处理错误。

业务 API 文件只描述资源路径，不重复处理认证逻辑。

## 2. 通用类型

```ts
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApiError {
  detail: string | object;
  error_code?: string;
}
```

## 3. 认证

封装文件：`src/api/auth.ts`

| 方法 | 前端函数 | 后端路径 |
| --- | --- | --- |
| `POST` | `authApi.login(credentials)` | `/auth/token` |
| `GET` | `authApi.getCurrentUser()` | `/auth/me` |

核心类型：

- `LoginParams`: `username`, `password`
- `TokenResponse`: `access_token`, `token_type`, `expires_in`
- `User`: `id`, `username`, `full_name`, `role`, `is_active`, `created_at`

## 4. 用户

封装文件：`src/api/users.ts`

| 前端函数 | 后端路径 |
| --- | --- |
| `userApi.getAll(params)` | `GET /users/` |
| `userApi.getById(id)` | `GET /users/{id}` |
| `userApi.create(data)` | `POST /users/` |
| `userApi.update(id, data)` | `PUT /users/{id}` |
| `userApi.delete(id)` | `DELETE /users/{id}` |

角色取值：`admin`、`operator`、`viewer`。

## 5. 设备

封装文件：`src/api/devices.ts`

| 前端函数 | 后端路径 |
| --- | --- |
| `deviceApi.getAll(params)` | `GET /devices/` |
| `deviceApi.getById(id)` | `GET /devices/{id}` |
| `deviceApi.create(data)` | `POST /devices/` |
| `deviceApi.update(id, data)` | `PUT /devices/{id}` |
| `deviceApi.delete(id)` | `DELETE /devices/{id}` |
| `deviceApi.getCalibrationConfig(id)` | `GET /devices/{id}/calibration/yaml` |
| `deviceApi.uploadCalibrationConfig(id, file)` | `POST /devices/{id}/calibration/yaml` |
| `deviceApi.uploadCalibrationImages(id, files)` | `POST /devices/{id}/calibration/images` |

设备类型重点字段：

- `ip_address`：视频源地址，可为 RTSP/HTTP/摄像头 URL。
- `edge_host`：Edge 节点主机名或 IP，用于 bootstrap。
- `device_token`：设备访问后端时使用。
- `stream_status`：传 `include_stream_status=true` 时返回。

## 6. 告警

封装文件：`src/api/alerts.ts`

| 前端函数 | 后端路径 |
| --- | --- |
| `alertApi.getAll(params)` | `GET /alerts/` |
| `alertApi.getStats(params)` | `GET /alerts/stats` |
| `alertApi.acknowledge(id, notes?)` | `PUT /alerts/{id}/acknowledge` |

筛选参数包括 `device_id`、`type`、`severity`、`is_acknowledged`、`start_date`、`end_date`、`skip`、`limit`。

告警类型：

- `fire_violation`
- `smoke_violation`
- `ppe_violation`
- `distance_violation`
- `access_control`

告警等级：`CRITICAL`、`DANGER`、`WARNING`。

## 7. 任务

封装文件：`src/api/tasks.ts`

| 前端函数 | 后端路径 |
| --- | --- |
| `taskApi.getAll(params)` | `GET /tasks/` |
| `taskApi.getById(id)` | `GET /tasks/{id}` |
| `taskApi.create(data)` | `POST /tasks/` |
| `taskApi.update(id, data)` | `PUT /tasks/{id}` |
| `taskApi.delete(id)` | `DELETE /tasks/{id}` |

任务状态：`pending`、`in_progress`、`completed`。

任务优先级：`high`、`medium`、`low`。

## 8. 视频流

封装文件：`src/api/streams.ts`

| 前端函数 | 后端路径 |
| --- | --- |
| `streamApi.getStreamOffer(deviceId, quality?)` | `GET /devices/{id}/stream/offer` |
| `streamApi.sendStreamAnswer(deviceId, streamId, answer)` | `POST /devices/{id}/stream/answer`（兼容/状态接口，当前 WHEP 主播放链路不依赖） |
| `streamApi.getStreamStatus(deviceId)` | `GET /devices/{id}/stream/status` |
| `streamApi.controlStream(deviceId, params)` | `POST /devices/{id}/stream/control` |
| `streamApi.stopStream(deviceId, streamId)` | `DELETE /devices/{id}/stream` |

`StreamControlParams.action` 取值：

- `start`
- `stop`
- `toggle_overlay`
- `set_quality`

视频质量取值：`low`、`medium`、`high`。

## 9. 系统健康

封装文件：`src/api/system.ts`

| 前端函数 | 后端路径 |
| --- | --- |
| `systemApi.health()` | `GET /system/health` |

## 10. 维护规则

- 后端新增字段后，先更新 `src/types/api.d.ts`，再更新对应 store 和页面。
- 后端路径变更时，同步更新 `src/api/*.ts` 和 `md/BACKEND_INTERFACE.md`。
- 前端接口只描述当前 UI 会调用的接口；Edge 专用接口记录在 `AI_EDGE_INTERFACE.md`。
