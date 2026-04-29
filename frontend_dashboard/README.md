# Frontend Dashboard

Vue 3 管理看板，用于登录、查看系统总览、管理设备/告警/任务/用户，并播放 Edge 推送到 SRS 的实时视频。

## 启动

```bash
cd frontend_dashboard
npm install
npm run dev
```

默认地址：

```text
http://localhost:5173
```

## 常用命令

```bash
npm run dev
npm run build
npm run lint
npm run test
npm run test:coverage
npm run test:report
```

## 技术栈

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- Element Plus
- Tailwind CSS
- Axios
- ECharts
- Vitest

## 主要目录

```text
src/
  api/          # 后端 API 封装
  components/   # 通用、布局、设备、看板、视频组件
  router/       # 路由和登录保护
  store/        # Pinia 状态
  types/        # TypeScript API 类型
  utils/        # WebRTC 等工具
  views/        # 页面
```

## 后端接口

前端通过 `src/api/*.ts` 调用后端 `/api/v1`：

- 登录：`/auth/token`
- 当前用户：`/auth/me`
- 设备：`/devices/`
- 告警：`/alerts/`
- 任务：`/tasks/`
- 用户：`/users/`
- 视频流：`/devices/{id}/stream/*`
- 系统健康：`/system/health`

## 视频播放

前端视频播放通过后端流接口协调：

```text
Frontend -> Backend -> Edge -> SRS -> WebRTC/WHEP -> Frontend
```

前端不直接控制 Edge，也不直接调用 SRS 管理接口。

## 文档

- 前端架构：`../md/FRONTEND_ARCHITECTURE.md`
- 前端接口：`../md/FRONTEND_INTERFACE.md`
- 后端接口：`../md/BACKEND_INTERFACE.md`
- 视频流配置：`../md/STREAMING_SETUP.md`
