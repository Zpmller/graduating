# 设备在线状态主动检测功能

## 概述

本系统实现了设备在线状态的主动检测功能，包括：
1. **心跳超时检测**：检查设备心跳是否超时
2. **主动连接检测**：主动尝试连接设备地址（ping、TCP、HTTP）来检测设备是否在线

## 功能特性

### 1. 心跳超时检测
- 检查设备的 `last_heartbeat` 字段
- **从未发送过心跳**或**超过 `HEARTBEAT_TIMEOUT_SECONDS`（默认300秒）**时，都会触发主动连接检测
- 这样纯 RTSP 摄像头（无心跳）也可通过 RTSP 检测被标记为在线

### 2. 主动连接检测
系统按以下优先级尝试检测设备在线状态：

**如果设备IP地址是RTSP URL（rtsp://开头）：**
1. **RTSP连接检测**（优先）
   - 使用OpenCV的VideoCapture尝试打开RTSP流
   - 尝试读取一帧视频，如果能读取到说明流可用
   - 超时时间：5秒
   - 需要安装 `opencv-python-headless` 依赖

**如果设备IP地址是普通IP或URL：**
1. **Ping检测**（最快）
   - 使用系统ping命令检测设备IP是否可达
   - 支持Windows和Linux/Mac系统
   - 超时时间：2秒

2. **TCP连接检测**
   - 尝试连接设备的80端口（HTTP端口）
   - 超时时间：2秒

3. **HTTP连接检测**
   - 尝试发送HTTP HEAD请求
   - 超时时间：3秒
   - 如果服务器返回4xx或5xx错误，也算在线（说明服务器响应了）

### 3. 定时任务
- 后台定时任务定期检查所有设备状态
- 默认检查间隔：60秒（可通过配置修改）
- 自动更新设备状态为 `ONLINE` 或 `OFFLINE`

## 配置说明

在 `.env` 文件中添加以下配置：

```env
# 设备心跳配置
HEARTBEAT_TIMEOUT_SECONDS=300  # 心跳超时时间（秒，默认5分钟）

# 设备状态检测配置
DEVICE_STATUS_CHECK_INTERVAL=60  # 设备状态检测间隔（秒，默认60秒）
DEVICE_STATUS_CHECK_ENABLED=True  # 是否启用设备状态主动检测
```

## 工作流程

```
定时任务启动（每60秒）
    ↓
获取所有设备列表
    ↓
对每个设备：
    ├─ 跳过维护状态的设备
    ├─ 检查心跳（无心跳或超时则需主动检测）
    │   ├─ 有最近心跳 → 保持当前状态
    │   └─ 无心跳或超时 → 执行主动检测
    │       ├─ 如果是RTSP URL
    │       │   └─ RTSP连接检测
    │       │       ├─ 成功 → 状态设为 ONLINE
    │       │       └─ 失败 → 继续其他检测
    │       ├─ Ping检测
    │       ├─ TCP连接检测（端口80）
    │       └─ HTTP连接检测
    │           ├─ 成功 → 状态设为 ONLINE
    │           └─ 失败 → 状态设为 OFFLINE
    └─ 更新数据库
```

## 代码结构

### 1. 设备状态检测服务
**文件**: `backend_system/app/services/device_status_service.py`

主要类：`DeviceStatusService`
- `ping_device()`: Ping检测
- `check_tcp_connection()`: TCP连接检测
- `check_http_connection()`: HTTP连接检测
- `check_rtsp_connection()`: RTSP连接检测（新增）
- `check_device_online()`: 综合检测（按优先级尝试，支持RTSP）
- `check_heartbeat_timeout()`: 心跳超时检测
- `update_device_status()`: 更新设备状态
- `check_all_devices()`: 检查所有设备

### 2. 定时任务管理
**文件**: `backend_system/app/core/tasks.py`

主要类：`BackgroundTasks`
- `device_status_check_task()`: 设备状态检测定时任务
- `start()`: 启动所有后台任务
- `stop()`: 停止所有后台任务

### 3. 应用启动集成
**文件**: `backend_system/app/main.py`

- `startup_event()`: 应用启动时启动后台任务
- `shutdown_event()`: 应用关闭时停止后台任务

## 使用示例

### 手动检测单个设备

```python
from app.services.device_status_service import device_status_service
from app.db.session import get_db

async def check_device():
    async for db in get_db():
        # 获取设备
        device = await db.get(Device, device_id=1)
        
        # 检测设备是否在线
        is_online = await device_status_service.check_device_online(device)
        print(f"Device {device.name} is {'online' if is_online else 'offline'}")
        
        # 更新设备状态
        await device_status_service.update_device_status(device, db)
        break
```

### 手动触发全量检测

```python
from app.services.device_status_service import device_status_service
from app.db.session import get_db

async def check_all():
    async for db in get_db():
        stats = await device_status_service.check_all_devices(db)
        print(f"Checked {stats['checked']} devices, {stats['status_changed']} status changed")
        break
```

## 日志输出

定时任务会输出以下日志：

```
[BackgroundTasks] Device status check task started
[BackgroundTasks] Device status check completed: total=5, checked=4, status_changed=1, online=3, offline=1, maintenance=1
[DeviceStatusService] Device 1 (Zone-A-Welding) status changed: online -> offline
```

## 注意事项

1. **权限要求**
   - Ping检测需要系统权限（通常需要管理员权限）
   - 如果ping失败，会自动尝试TCP和HTTP检测

2. **网络环境**
   - 确保后端服务器能够访问设备IP地址
   - 如果设备在NAT后面，可能需要配置端口转发

3. **性能考虑**
   - 检测间隔不要设置太短（建议≥30秒）
   - 每个设备的检测可能需要2-5秒
   - 设备数量较多时，建议增加检测间隔

4. **维护状态**
   - 处于 `MAINTENANCE` 状态的设备不会被检测
   - 避免在维护期间误判设备状态

5. **IP地址格式**
   - 支持IPv4地址（如：192.168.1.100）
   - 支持URL格式（如：http://192.168.1.100）
   - 支持RTSP URL（如：rtsp://192.168.1.100:8554/live/stream_id）
   - **RTSP URL会优先使用RTSP连接检测**，如果检测失败，会继续尝试ping/TCP/HTTP检测

6. **RTSP检测依赖**
   - 需要安装 `opencv-python-headless` 依赖（已在requirements.txt中）
   - 如果OpenCV不可用，RTSP检测会被跳过，自动使用其他检测方式

## 故障排查

### 问题：设备一直显示离线，但实际在线

1. 检查设备IP地址配置是否正确
2. 检查后端服务器是否能ping通设备IP
3. 检查防火墙是否阻止了连接
4. 查看日志中的错误信息

### 问题：检测任务没有运行

1. 检查 `DEVICE_STATUS_CHECK_ENABLED` 是否为 `True`
2. 查看应用启动日志，确认任务已启动
3. 检查是否有异常错误导致任务停止

### 问题：检测太慢

1. 增加 `DEVICE_STATUS_CHECK_INTERVAL` 间隔时间
2. 检查网络延迟
3. 考虑只对关键设备进行检测

## RTSP检测说明

### 工作原理
1. 检测设备IP地址是否为RTSP URL（以 `rtsp://` 开头）
2. 如果是RTSP URL，使用OpenCV的VideoCapture尝试打开流
3. 设置超时时间（默认5秒）
4. 尝试读取一帧视频数据
5. 如果成功读取到帧，说明RTSP流可用，设备在线
6. 如果RTSP检测失败，会继续尝试ping/TCP/HTTP检测

### 使用场景
- 设备IP地址字段存储的是RTSP流地址
- 需要验证视频流是否可用
- 适用于视频监控设备

### 示例
```python
# 设备IP地址为RTSP URL
device.ip_address = "rtsp://192.168.1.100:8554/live/stream_123"

# 检测时会优先使用RTSP检测
is_online = await device_status_service.check_device_online(device)
```

## 未来改进

1. **支持更多检测方式**
   - SNMP检测
   - 自定义端口检测
   - RTSP认证支持（用户名密码）

2. **智能检测策略**
   - 根据设备类型选择最佳检测方式
   - 动态调整检测间隔

3. **检测结果缓存**
   - 缓存检测结果，避免频繁检测
   - 失败重试机制

4. **告警通知**
   - 设备状态变化时发送告警
   - 集成到现有的告警系统
