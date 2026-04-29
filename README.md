# 矿业动火作业行为安全监测系统

**Mining Hot-Work Safety Monitoring System**

本项目面向矿山动火作业场景，使用边缘侧 AI 视觉分析和云端管理看板，对火焰/火星、安全帽佩戴、气瓶安全距离、授权人员身份等风险进行实时监测、告警与留痕。

系统采用 **Edge-Cloud** 架构：

- **AI Edge**：负责视频采集、目标检测、人脸识别、告警上报和 RTMP 推流。
- **Backend**：负责用户、设备、告警、任务、人脸库、视频流协调和系统健康接口。
- **Frontend**：负责 Web 管理看板、设备/告警/任务/用户管理和实时视频播放。
- **SRS Media Server**：负责接收 Edge RTMP 推流，并通过 WHEP/WebRTC 提供前端播放。

## 仓库结构

| 路径 | 说明 |
| --- | --- |
| `ai_edge_system/` | Python + PyQt5 边缘端程序，包含检测、识别、上传、推流和控制服务 |
| `backend_system/` | FastAPI 后端服务，包含 REST API、数据库模型、静态文件和流媒体协调 |
| `frontend_dashboard/` | Vue 3 + Vite + TypeScript 前端看板 |
| `md/` | 当前有效技术文档与归档文档 |
| `docker-compose.yml` | SRS 流媒体服务 |
| `start_system.bat` | Windows 一键启动 SRS、后端、Edge、前端 |
| `start_ai_backend.bat` | Windows 一键启动后端和 Edge |

## 快速启动

### 环境要求

- Python 3.8+，用于后端和边缘端。
- Node.js 18+，用于前端。
- MySQL 8.0，作为后端数据库。
- FFmpeg，用于 Edge 推流。
- Docker，可选，用于启动 SRS。

### 一键启动

在仓库根目录执行：

```bat
start_system.bat
```

该脚本会依次启动：

- SRS: `http://localhost:1985`
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- AI Edge: PyQt 桌面程序

如果只需要后端和边缘端：

```bat
start_ai_backend.bat
```

### 手动启动

后端：

```bash
cd backend_system
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python scripts/init_db.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend_dashboard
npm install
npm run dev
```

边缘端：

```bash
cd ai_edge_system
pip install -r requirements.txt
python main.py
```

SRS：

```bash
docker compose up -d
```

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | FastAPI, SQLAlchemy async, Alembic, MySQL, JWT, bcrypt, Pydantic Settings |
| 前端 | Vue 3, Vite, TypeScript, Pinia, Vue Router, Element Plus, Tailwind CSS, Axios |
| 边缘端 | Python, PyQt5, OpenCV, Ultralytics YOLO, DeepFace, TensorFlow/Torch, FFmpeg |
| 流媒体 | SRS 5, RTMP, WHEP/WebRTC |

## 当前接口范围

后端 API 统一挂载在 `/api/v1` 下，主要模块包括：

- `/auth`：登录与当前用户。
- `/users`：用户 CRUD。
- `/devices`：设备 CRUD、bootstrap、心跳、标定配置。
- `/alerts`：告警上传、查询、统计、确认。
- `/tasks`：任务 CRUD。
- `/faces`：授权人脸图片上传、列表、图片读取。
- `/devices/{id}/stream/*`：视频流 offer、answer、状态、控制和停止。
- `/system/health`：健康检查。

## 文档入口

当前有效文档位于 [md/README.md](md/README.md)。历史修复记录、历史测试报告和论文写作材料已移动到 `md/archive/`，仅作为过程记录参考；当前接口规范以代码和主技术文档为准。

## 作者与用途

本项目为学术/毕业设计项目。作者：吴秋逸，学号 22211044。
