# 项目文档索引

本目录只保留当前有效的技术文档。历史修复记录、测试报告和论文写作材料已归档到 `archive/`，不再作为当前接口或部署规范的来源。

## 当前技术文档

| 文档 | 用途 |
| --- | --- |
| [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) | AI Edge 边缘端架构、模块和运行数据流 |
| [AI_EDGE_INTERFACE.md](AI_EDGE_INTERFACE.md) | Edge 与后端、流媒体、控制服务之间的接口约定 |
| [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) | FastAPI 后端架构、数据库模型、服务分层和配置 |
| [BACKEND_INTERFACE.md](BACKEND_INTERFACE.md) | `/api/v1` REST API 当前接口说明 |
| [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) | Vue 前端架构、路由、状态管理和视频播放设计 |
| [FRONTEND_INTERFACE.md](FRONTEND_INTERFACE.md) | 前端 TypeScript 类型和 `src/api` 封装说明 |
| [STREAMING_SETUP.md](STREAMING_SETUP.md) | SRS + RTMP + WHEP/WebRTC 视频流端到端部署 |
| [EDGE_AUTO_CONFIG.md](EDGE_AUTO_CONFIG.md) | Edge bootstrap 零配置、设备 token 和心跳流程 |
| [LOGGING_GUIDE.md](LOGGING_GUIDE.md) | 心跳、告警、流媒体和常见排障日志 |
| [系统使用说明.md](系统使用说明.md) | 面向使用者的启动、设备配置、告警处理和看板操作说明 |

## 归档区

| 路径 | 内容 |
| --- | --- |
| `archive/fixes/` | CORS、认证、接口对齐、CRUD、设备状态等历史修复记录 |
| `archive/test-reports/` | `ai_edge_system`、`backend_system`、`frontend_dashboard` 的历史测试报告 |
| `archive/thesis/` | 论文摘要、开题报告、章节草稿、插图清单等写作材料 |
| `archive/project-notes/` | 早期开发计划和 Agent 过程说明 |

## 维护约定

- 当前接口规范以代码和本目录主接口文档为准。
- `archive/` 下文档只作为变更背景或论文材料参考。
- 修改后端 API 时，同步更新 `BACKEND_INTERFACE.md` 和需要的前端类型说明。
- 修改 Edge 自动配置、推流或设备状态逻辑时，同步更新 `AI_EDGE_INTERFACE.md`、`EDGE_AUTO_CONFIG.md` 和 `STREAMING_SETUP.md`。
- 所有 Markdown 使用 UTF-8 编码保存。
