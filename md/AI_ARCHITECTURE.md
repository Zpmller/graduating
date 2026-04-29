# AI Edge System Architecture

## 1. 概览

AI Edge 位于 `ai_edge_system/`，是部署在现场或摄像头附近的边缘端程序。它通过 PyQt5 提供桌面界面，负责拉取视频源、执行 AI 检测与识别、生成告警、向后端发送心跳和告警数据，并在需要时向 SRS 推送带检测画面的 RTMP 视频流。

入口文件是 `main.py`，主窗口实现位于 `src/ui/main_window.py`。

## 2. 技术栈

| 类别 | 实现 |
| --- | --- |
| 桌面界面 | PyQt5 |
| 视频处理 | OpenCV |
| 检测模型 | Ultralytics YOLO |
| 人脸识别 | DeepFace / ArcFace 相关能力 |
| 深度学习依赖 | TensorFlow, Torch |
| 推流 | FFmpeg, RTMP |
| 后端通信 | requests |
| 配置 | 环境变量 + 后端 bootstrap |

## 3. 启动流程

1. `main.py` 设置 TensorFlow 日志级别，并先导入 Torch 以规避 Windows DLL 冲突。
2. 创建 `QApplication`。
3. 加载 `src.ui.main_window.MainWindow`。
4. 主窗口初始化摄像头、检测、上传、推流、控制服务等组件。
5. 程序进入 PyQt 事件循环。

## 4. 核心模块

| 模块 | 职责 |
| --- | --- |
| `src/core/device_config.py` | 从后端自动获取设备配置，支持 bootstrap、`/devices/me` 和环境变量回退 |
| `src/core/detector.py` | YOLO 检测封装 |
| `src/core/recognizer.py` | 人脸识别逻辑 |
| `src/core/face_client.py` | 从后端人脸库同步授权人员图片/信息 |
| `src/core/uploader.py` | 告警队列上传和设备心跳 |
| `src/core/streamer.py` | 使用 FFmpeg 将标注帧推送到 SRS |
| `src/api/stream_control_server.py` | 后端控制 Edge 开始/停止推流、切换覆盖层和质量 |
| `src/logic/safety.py` | 安全规则判断和告警生成 |
| `src/logic/distance.py` | 单目测距与气瓶距离计算 |
| `src/enhancer.py` | 低照度图像增强 |
| `src/utils/camera.py` | 摄像头/视频源读取 |
| `src/utils/calibration_tool.py` | 标定工具 |

## 5. 设备配置策略

Edge 启动后优先使用后端自动配置：

1. 读取 `BACKEND_URL`，默认 `http://localhost:8000/api/v1`。
2. 读取 `EDGE_HOST`；如果后端是 localhost，则默认使用 `127.0.0.1`。
3. 请求 `/devices/bootstrap?edge_host=<host>`。
4. 如配置了 `BOOTSTRAP_SECRET`，同时携带 `secret` 参数。
5. 成功后得到 `device_id`、`device_token`、视频源地址和 Edge 主机信息。
6. 如果 bootstrap 失败且配置了 `DEVICE_TOKEN`，请求 `/devices/me`。
7. 如果仍失败，回退到旧的 `DEVICE_ID` + `DEVICE_TOKEN` 环境变量方式。

## 6. 数据流

```text
摄像头/视频源
  -> OpenCV 读帧
  -> 图像增强
  -> YOLO 检测
  -> 人脸识别
  -> 安全规则判断
  -> UI 展示
  -> 告警队列
  -> 后端 /alerts/

标注帧
  -> VideoStreamer
  -> FFmpeg
  -> SRS RTMP
  -> SRS WHEP/WebRTC
  -> 前端播放
```

## 7. 告警与心跳

`AlertUploader` 维护后台上传线程和心跳线程：

- 告警通过队列异步上传，避免阻塞视频处理。
- 心跳每 30 秒调用 `/devices/{device_id}/heartbeat`。
- 请求头使用 `X-Device-Token`。
- 告警上传使用 multipart 表单，包含 JPEG 证据图和 `alert_data` JSON。

## 8. 推流

`VideoStreamer` 根据质量选择分辨率、帧率和码率：

| 质量 | 分辨率 | FPS | 码率 |
| --- | --- | --- | --- |
| `low` | 640x480 | 15 | 500 kbps |
| `medium` | 1280x720 | 25 | 1500 kbps |
| `high` | 1920x1080 | 30 | 3000 kbps |

推流 URL 形如：

```text
rtmp://localhost:1935/live/{stream_id}
```

## 9. 训练与模型

`train.py` 用于模型训练或微调流程。运行时模型文件位于 `models/`，训练和数据文件位于 `data/`。实际部署应确认模型路径、类别映射和安全规则配置与现场场景一致。

## 10. 运维注意事项

- Windows 下需确保 FFmpeg 可在命令行中访问。
- 首次启动前应在后端创建设备，并填写正确的 `edge_host` 和视频源地址。
- 如果 Edge 与后端同机运行，`edge_host` 可使用 `127.0.0.1`。
- 如果局域网部署，`EDGE_HOST` 应设置为后端可访问的 Edge 主机 IP。
- 推流失败时先检查 SRS、FFmpeg、设备 token 和后端流控制接口。
