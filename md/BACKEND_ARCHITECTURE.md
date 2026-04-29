# Backend System Architecture

## 1. 概览

后端位于 `backend_system/`，是系统的云端协调层。它通过 FastAPI 暴露 `/api/v1` REST API，负责用户认证、设备管理、告警入库、任务管理、人脸库文件管理、SRS/WHEP 视频流协调和系统健康检查。

应用入口是 `app/main.py`，路由聚合入口是 `app/api/api_v1.py`。OpenAPI 文档默认可通过 `http://localhost:8000/docs` 查看。

## 2. 技术栈

| 类别 | 实现 |
| --- | --- |
| Web 框架 | FastAPI, Uvicorn |
| 数据库访问 | SQLAlchemy 2.x async, aiomysql |
| 迁移 | Alembic |
| 配置 | Pydantic Settings, `.env` |
| 认证 | JWT, passlib/bcrypt |
| 文件 | FastAPI `UploadFile`, 静态目录挂载 |
| 外部服务 | SRS HTTP API/WHEP, Edge 控制服务 |

## 3. 目录结构

```text
backend_system/
  app/
    api/
      api_v1.py
      deps.py
      endpoints/
    core/
      config.py
      exceptions.py
      security.py
      tasks.py
    db/
      base.py
      session.py
    models/
    schemas/
    services/
    utils/
    main.py
  alembic/
  scripts/
  static/
  tests/
```

## 4. 启动流程

1. `app/main.py` 创建 FastAPI 实例。
2. 配置 CORS，允许 `.env` 中 `CORS_ORIGINS` 的前端地址访问。
3. 注册自定义异常处理器和请求校验异常处理器。
4. 启动时读取配置并检查数据库连接。
5. 将 `api_router` 挂载到 `/api/v1`。
6. 挂载证据图片目录 `/static/evidence` 和人脸图片目录 `/static/faces`。
7. 关闭时停止后台任务。

## 5. 配置项

核心配置定义在 `app/core/config.py`。

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `mysql+aiomysql://root:password@localhost:3306/safety_monitoring` | MySQL 连接地址 |
| `SECRET_KEY` | 示例密钥 | JWT 签名密钥，实际部署必须替换 |
| `JWT_EXPIRATION_SECONDS` | `3600` | token 有效期 |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | 后端监听地址 |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | 允许的前端来源 |
| `EVIDENCE_DIR` | `static/evidence` | 告警证据图片目录 |
| `FACE_DIR` | `static/faces` | 人脸库图片目录 |
| `MEDIA_SERVER_URL` | `http://localhost:1985` | SRS HTTP API/WHEP 地址 |
| `MEDIA_SERVER_RTMP_URL` | `rtmp://localhost:1935` | Edge 推流地址 |
| `BOOTSTRAP_SECRET` | 空 | Edge bootstrap 可选密钥 |
| `EDGE_CONTROL_PORT` | `8080` | Edge 本地控制服务端口 |
| `DEVICE_STATUS_CHECK_ENABLED` | `True` | 是否启用设备主动状态检测 |

## 6. 数据模型

| 模型 | 主要字段 | 说明 |
| --- | --- | --- |
| `User` | `username`, `hashed_password`, `full_name`, `role`, `is_active` | 后台用户，角色为 `admin`、`operator`、`viewer` |
| `Device` | `name`, `location`, `ip_address`, `edge_host`, `device_token`, `status`, `last_heartbeat`, `calibration_config` | 设备与 Edge 节点配置 |
| `Alert` | `device_id`, `type`, `severity`, `message`, `timestamp`, `image_path`, `alert_metadata`, `is_acknowledged` | 风险告警和证据 |
| `Task` | `title`, `description`, `status`, `priority`, `assigned_to`, `due_date` | 整改/巡检任务 |
| `FaceRecord` | `person_name`, `file_path`, `created_at` | 授权人员人脸图片索引 |

## 7. 路由模块

路由统一挂载在 `/api/v1`：

- `auth.py`：登录和当前用户。
- `users.py`：用户分页、创建、读取、更新、删除。
- `devices.py`：设备 CRUD、bootstrap、`/me`、心跳、标定 YAML 和标定图片上传。
- `alerts.py`：Edge 告警上传、分页查询、统计、确认。
- `tasks.py`：任务 CRUD 和筛选。
- `streams.py`：WHEP offer/answer、流状态、控制、停止。
- `faces.py`：授权人脸上传、列表、图片读取。
- `system.py`：健康检查。

## 8. 服务分层

| 服务 | 职责 |
| --- | --- |
| `alert_service.py` | 告警保存、过滤、统计、确认 |
| `stream_service.py` | 流 ID、WHEP、SRS 地址、Edge 控制协调 |
| `device_status_service.py` | 设备在线状态、心跳超时和主动探测 |
| `face_storage.py` | 人脸图片目录和文件保存 |
| `file_storage.py` | 告警证据文件保存 |
| `calibration_service.py` | 标定文件和图片处理 |

## 9. 安全与访问控制

- 用户接口通过 JWT Bearer token 鉴权。
- Edge 设备使用 `X-Device-Token` 访问心跳和告警上报接口。
- Bootstrap 可通过 `BOOTSTRAP_SECRET` 增加共享密钥保护。
- CORS 允许来源由 `CORS_ORIGINS` 控制。
- 静态证据和人脸图片由后端挂载目录提供访问。

## 10. 与其他子系统的关系

- 前端通过 `frontend_dashboard/src/api/*.ts` 调用 `/api/v1` 接口。
- Edge 通过 bootstrap 或 device token 获取设备配置，并向后端发送心跳和告警。
- SRS 由 `docker-compose.yml` 提供，后端负责生成和转发 WHEP 相关信息。
- 前端播放视频时先请求后端流接口，后端再协调 SRS 和 Edge 推流。
