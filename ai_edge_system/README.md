# AI Edge System

AI Edge 是现场边缘端程序，负责读取摄像头/视频源、执行 AI 检测和人脸识别、生成告警、上传证据图、发送设备心跳，并按后端控制向 SRS 推送实时视频流。

## 启动

```bash
cd ai_edge_system
pip install -r requirements.txt
python main.py
```

Windows 一键启动可在项目根目录执行：

```bat
start_ai_backend.bat
```

或启动完整系统：

```bat
start_system.bat
```

## 运行前准备

1. 后端已启动，并可访问 `http://localhost:8000/api/v1`。
2. 前端设备管理中已创建设备。
3. 设备的 `edge_host` 与 Edge 主机匹配。
4. 设备的 `ip_address` 填写摄像头或视频源地址。
5. FFmpeg 已安装并加入 PATH。

## 自动配置

Edge 启动后优先通过 bootstrap 获取配置：

```text
GET /api/v1/devices/bootstrap?edge_host=<edge_host>
```

常用环境变量：

| 变量 | 说明 |
| --- | --- |
| `BACKEND_URL` | 后端 API 地址，默认 `http://localhost:8000/api/v1` |
| `EDGE_HOST` | Edge 主机地址；同机可用 `127.0.0.1` |
| `BOOTSTRAP_SECRET` | 与后端一致的 bootstrap 密钥 |
| `DEVICE_TOKEN` | bootstrap 失败时的 token 回退方式 |
| `DEVICE_ID` | 旧部署方式中的设备 ID |

## 主要目录

```text
src/
  api/       # Edge 本地控制服务
  core/      # 检测、识别、配置、上传、推流
  logic/     # 安全规则和测距逻辑
  ui/        # PyQt 主窗口
  utils/     # 摄像头、标定和标签工具
data/        # 数据文件
models/      # 模型文件
scripts/     # 辅助脚本
tests/       # 测试
```

## 数据流

```text
摄像头/视频源 -> OpenCV -> 图像增强 -> YOLO/人脸识别 -> 安全规则
  -> 告警上传到 Backend
  -> 标注视频帧推送到 SRS
```

## 文档

- Edge 架构：`../md/AI_ARCHITECTURE.md`
- Edge 接口：`../md/AI_EDGE_INTERFACE.md`
- 自动配置：`../md/EDGE_AUTO_CONFIG.md`
- 视频流：`../md/STREAMING_SETUP.md`
