# Frontend Dashboard Architecture

## 1. 概览

前端位于 `frontend_dashboard/`，是矿业动火作业安全监测系统的 Web 管理看板。它使用 Vue 3、Vite、TypeScript、Pinia、Vue Router、Element Plus 和 Tailwind CSS，实现登录、监控总览、设备管理、告警历史、任务管理、用户管理和实时视频播放。

开发服务默认运行在 `http://localhost:5173`，通过 `VITE_API_BASE_URL` 或默认配置访问后端 `/api/v1`。

## 2. 技术栈

| 类别 | 实现 |
| --- | --- |
| 应用框架 | Vue 3 |
| 构建工具 | Vite |
| 语言 | TypeScript |
| 状态管理 | Pinia |
| 路由 | Vue Router |
| UI | Element Plus, Tailwind CSS |
| HTTP | Axios |
| 图表 | ECharts |
| 视频 | WebRTC/WHEP 工具封装 |
| 测试 | Vitest, Vue Test Utils, jsdom |

## 3. 目录结构

```text
frontend_dashboard/
  src/
    api/
    components/
      common/
      dashboard/
      devices/
      layout/
      video/
    router/
    store/
    types/
    utils/
    views/
    App.vue
    main.ts
  public/
  tests/
  package.json
  vite.config.ts
```

## 4. 应用入口

- `src/main.ts` 创建 Vue 应用，注册 Pinia、Router 和 Element Plus。
- `src/App.vue` 提供根视图。
- `src/router/index.ts` 定义页面路由和登录保护。
- `src/api/axios.ts` 统一创建 Axios 客户端，注入 token，并处理响应错误。

## 5. 页面与功能

| 页面 | 文件 | 功能 |
| --- | --- | --- |
| 登录 | `views/LoginView.vue` | 用户登录并保存 token |
| 总览 | `views/DashboardView.vue` | 设备、告警、任务等概览 |
| 设备 | `views/DevicesView.vue` | 设备列表、创建/编辑、标定、视频播放 |
| 历史 | `views/HistoryView.vue` | 告警查询、筛选、确认 |
| 任务 | `views/TasksView.vue` | 任务创建、筛选、更新 |
| 用户 | `views/UsersView.vue` | 用户管理 |
| 404 | `views/NotFound.vue` | 未匹配路由 |

## 6. 状态管理

Pinia store 按业务域拆分：

- `store/auth.ts`：登录状态、当前用户、token。
- `store/devices.ts`：设备分页、设备状态、标定相关动作。
- `store/alerts.ts`：告警列表、统计和确认。
- `store/tasks.ts`：任务列表和 CRUD。
- `store/users.ts`：用户列表和 CRUD。
- `store/streams.ts`：视频流 offer、状态和控制。

## 7. API 封装

前端接口封装位于 `src/api/`：

- `auth.ts` -> `/auth/token`、`/auth/me`
- `users.ts` -> `/users/`
- `devices.ts` -> `/devices/`、标定接口
- `alerts.ts` -> `/alerts/`、`/alerts/stats`
- `tasks.ts` -> `/tasks/`
- `streams.ts` -> `/devices/{id}/stream/*` 和 WHEP 代理 `/stream/whep/{stream_id}`
- `system.ts` -> `/system/health`

类型定义集中在 `src/types/api.d.ts`，包括用户、设备、告警、任务和视频流类型。

## 8. 视频播放

视频组件位于 `src/components/video/`：

- `VideoPlayer.vue`：单路视频播放。
- `StreamWallCell.vue`：视频墙单元格。
- `utils/webrtc.ts`：WebRTC/WHEP 连接工具。

播放流程：

1. 前端请求 `/devices/{id}/stream/offer`。
2. 后端返回 `stream_id` 和 `whep_url` 信息。
3. 前端创建 WebRTC offer，并将 SDP 提交到后端 WHEP 代理 `POST /stream/whep/{stream_id}`。
4. 后端将 WHEP 请求转发给 SRS，前端使用 SRS answer 建立 WebRTC 播放。
5. SRS 将 Edge RTMP 推流转换为 WebRTC/WHEP 播放。
6. 前端通过状态接口和 store 更新 UI。

## 9. 构建与测试

常用命令：

```bash
npm run dev
npm run build
npm run lint
npm run test
npm run test:coverage
npm run test:report
```

`npm run build` 会先执行 TypeScript 检查，再执行 Vite 构建。

## 10. 与后端的对齐规则

- 新增或修改 API 时，同步更新 `src/api/*.ts` 和 `src/types/api.d.ts`。
- 后端分页接口应保持 `items`、`total`、`skip`、`limit` 结构。
- 设备流状态字段应与后端 `StreamStatusResponse` 保持一致。
- 前端不直接访问 SRS 管理 API，统一通过后端流接口协调。
