# Backend System

FastAPI 后端服务，负责矿业动火作业安全监测系统的 API、数据库、文件存储、设备状态、告警、任务、人脸库和视频流协调。

## 启动

```bash
cd backend_system
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python scripts/init_db.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/system/health`

## 主要目录

```text
app/
  api/          # 路由、依赖和 endpoints
  core/         # 配置、安全、异常和后台任务
  db/           # SQLAlchemy session/base
  models/       # ORM 模型
  schemas/      # Pydantic schema
  services/     # 告警、流、状态、文件、人脸、标定服务
  main.py       # FastAPI 入口
alembic/        # 数据库迁移
scripts/        # 初始化、标定等脚本
static/         # 证据图、人脸图等静态文件
tests/          # 后端测试
```

## API 模块

所有业务接口挂载在 `/api/v1` 下：

- `/auth`：登录和当前用户。
- `/users`：用户 CRUD。
- `/devices`：设备 CRUD、bootstrap、`/me`、心跳、标定文件。
- `/alerts`：告警上传、查询、统计、确认。
- `/tasks`：任务 CRUD。
- `/faces`：授权人脸库。
- `/devices/{id}/stream/*`：视频流 offer、answer、状态、控制和停止。
- `/system/health`：健康检查。

## 关键配置

配置来源为 `.env`，定义见 `app/core/config.py`。

| 配置 | 说明 |
| --- | --- |
| `DATABASE_URL` | MySQL 异步连接地址 |
| `SECRET_KEY` | JWT 签名密钥 |
| `CORS_ORIGINS` | 允许访问后端的前端地址 |
| `EVIDENCE_DIR` | 告警证据图片目录 |
| `FACE_DIR` | 人脸库图片目录 |
| `MEDIA_SERVER_URL` | SRS HTTP API/WHEP 地址 |
| `MEDIA_SERVER_RTMP_URL` | Edge RTMP 推流地址 |
| `BOOTSTRAP_SECRET` | Edge bootstrap 可选密钥 |
| `EDGE_CONTROL_PORT` | Edge 控制服务端口 |

## 流媒体关系

前端不直接控制 Edge。播放流程为：

```text
Frontend -> Backend stream API -> Edge control service -> SRS -> Frontend WebRTC
```

详见 `../md/STREAMING_SETUP.md`。

## 文档

- 后端架构：`../md/BACKEND_ARCHITECTURE.md`
- API 接口：`../md/BACKEND_INTERFACE.md`
- 日志排障：`../md/LOGGING_GUIDE.md`
