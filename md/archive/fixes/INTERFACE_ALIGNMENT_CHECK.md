# 接口对齐检查报告

> **项目**: 矿山热作业安全监控系统  
> **日期**: 2026-02-03  
> **版本**: 1.0

## 1. 概述

本报告详细检查了后端API接口和前端API调用的对齐情况，包括：
- 请求/响应类型匹配
- 字段定义一致性
- 分页响应格式
- 参数定义

## 2. 设备接口对齐检查

### 2.1 GET /devices/ - 获取设备列表

**后端实现** (`backend_system/app/api/endpoints/devices.py:35-68`):
```python
@router.get("/", response_model=DeviceListResponse)
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    status_filter: Optional[DeviceStatus] = Query(None, alias="status"),
    ...
)
# 返回: DeviceListResponse(items, total, skip, limit)
```

**前端实现** (`frontend_dashboard/src/api/devices.ts:6-8`):
```typescript
getAll: (params?: { skip?: number; limit?: number; status?: string }): Promise<PaginatedResponse<Device>>
```

**对齐状态**: ✅ **基本对齐**
- 分页参数：skip, limit ✅
- 过滤参数：status ✅
- 响应格式：PaginatedResponse 和 DeviceListResponse 结构一致 ✅

### 2.2 GET /devices/{id} - 获取设备详情

**后端响应** (`backend_system/app/schemas/device.py:30-40`):
```python
class DeviceResponse(DeviceBase):
    id: int
    device_token: str
    status: DeviceStatus
    last_heartbeat: Optional[datetime] = None
    calibration_config: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

**前端类型** (`frontend_dashboard/src/types/api.d.ts:49-56`):
```typescript
export interface Device {
  id: number;
  name: string;
  location: string;
  ip_address: string;
  status: DeviceStatus;
  last_heartbeat: string | null;
}
```

**对齐状态**: ⚠️ **字段不完整**
- ✅ 对齐字段：id, name, location, ip_address, status, last_heartbeat
- ❌ 缺失字段：
  - `device_token` - 设备认证令牌（可能不需要在前端显示）
  - `calibration_config` - 标定配置（可能不需要在前端显示）
  - `created_at` - 创建时间
  - `updated_at` - 更新时间

**建议**: 
- 如果前端不需要这些字段，当前实现可以接受
- 如果需要显示创建/更新时间，应添加到前端类型定义

### 2.3 POST /devices/ - 创建设备

**后端请求** (`backend_system/app/schemas/device.py:17-19`):
```python
class DeviceCreate(DeviceBase):
    pass  # name, location, ip_address
```

**前端请求** (`frontend_dashboard/src/types/api.d.ts:58-62`):
```typescript
export interface CreateDeviceParams {
  name: string;
  location: string;
  ip_address: string;
}
```

**对齐状态**: ✅ **完全对齐**

### 2.4 PUT /devices/{id} - 更新设备

**后端请求** (`backend_system/app/schemas/device.py:22-27`):
```python
class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[DeviceStatus] = None
```

**前端请求** (`frontend_dashboard/src/api/devices.ts:21-23`):
```typescript
update: (id: number, data: Partial<CreateDeviceParams>): Promise<Device>
```

**对齐状态**: ⚠️ **部分对齐**
- ✅ 字段：name, location, ip_address
- ❌ 缺失：`status` 字段（后端支持更新状态，前端类型定义不支持）

**建议**: 前端 `CreateDeviceParams` 不包含 `status`，但后端 `DeviceUpdate` 支持更新 `status`。应该：
- 创建 `UpdateDeviceParams` 类型，包含 `status` 字段
- 或确认前端不需要更新设备状态功能

### 2.5 DELETE /devices/{id} - 删除设备

**对齐状态**: ✅ **完全对齐**

---

## 3. 用户接口对齐检查

### 3.1 GET /users/ - 获取用户列表

**后端实现** (`backend_system/app/api/endpoints/users.py:22-36`):
```python
@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    ...
)
# 返回: list[UserResponse]  ❌ 没有分页信息！
```

**前端实现** (`frontend_dashboard/src/api/users.ts:6-8`):
```typescript
getAll: (params?: { skip?: number; limit?: number }): Promise<User[]>
```

**对齐状态**: ⚠️ **不一致**
- **问题**: 后端接受 `skip` 和 `limit` 参数，但返回的是 `list[UserResponse]`，没有分页信息（total, skip, limit）
- **前端期望**: `User[]`（没有分页信息，与后端一致）
- **建议**: 
  1. 后端应该返回 `UserListResponse`（包含 items, total, skip, limit），与其他接口保持一致
  2. 或者前端不需要分页，后端移除 skip/limit 参数

### 3.2 GET /users/{id} - 获取用户详情

**后端响应** (`backend_system/app/schemas/user.py:31-36`):
```python
class UserResponse(UserBase):
    id: int
    created_at: datetime
```

**前端类型** (`frontend_dashboard/src/types/api.d.ts:16-22`):
```typescript
export interface User {
  id: number;
  username: string;
  full_name?: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
}
```

**对齐状态**: ⚠️ **字段不完整**
- ✅ 对齐字段：id, username, full_name, role, is_active
- ❌ 缺失字段：`created_at` - 创建时间

**建议**: 如果前端需要显示用户创建时间，应添加到类型定义

### 3.3 POST /users/ - 创建用户

**后端请求** (`backend_system/app/schemas/user.py:18-20`):
```python
class UserCreate(UserBase):
    password: str
```

**前端请求** (`frontend_dashboard/src/types/api.d.ts:29-34`):
```typescript
export interface CreateUserParams {
  username: string;
  full_name?: string;
  password: string;
  role: 'admin' | 'operator' | 'viewer';
}
```

**对齐状态**: ✅ **完全对齐**

### 3.4 PUT /users/{id} - 更新用户

**后端请求** (`backend_system/app/schemas/user.py:23-28`):
```python
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
```

**前端请求** (`frontend_dashboard/src/types/api.d.ts:36-38`):
```typescript
export interface UpdateUserParams extends Partial<CreateUserParams> {
  is_active?: boolean;
}
```

**对齐状态**: ✅ **完全对齐**

### 3.5 DELETE /users/{id} - 删除用户

**对齐状态**: ✅ **完全对齐**

---

## 4. 任务接口对齐检查

### 4.1 GET /tasks/ - 获取任务列表

**后端实现** (`backend_system/app/api/endpoints/tasks.py:23-76`):
```python
@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    status: Optional[TaskStatus] = Query(None),
    assigned_to: Optional[int] = Query(None, alias="assignee_id"),
    ...
)
# 返回: TaskListResponse(items, total, skip, limit)
```

**前端实现** (`frontend_dashboard/src/api/tasks.ts:6-8`):
```typescript
getAll: (params?: TaskFilterParams): Promise<PaginatedResponse<Task>>
```

**对齐状态**: ✅ **完全对齐**
- 分页参数：skip, limit ✅
- 过滤参数：status, assignee_id ✅
- 响应格式：PaginatedResponse 和 TaskListResponse 结构一致 ✅

### 4.2 GET /tasks/{id} - 获取任务详情

**后端响应** (`backend_system/app/schemas/task.py:35-41`):
```python
class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
```

**前端类型** (`frontend_dashboard/src/types/api.d.ts:108-119`):
```typescript
export interface Task {
  id: number;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'high' | 'medium' | 'low';
  assigned_to?: number;
  assignee_name?: string;  // ⚠️ 后端没有这个字段
  due_date?: string;
  created_at: string;
  updated_at: string;
}
```

**对齐状态**: ⚠️ **字段不一致**
- ✅ 对齐字段：id, title, description, status, priority, assigned_to, due_date, created_at, updated_at
- ⚠️ 额外字段：`assignee_name` - 前端有，但后端 `TaskResponse` 没有
- **注意**: 后端代码中会加载 `assigned_user` 关系（`tasks.py:127`），但响应Schema中没有 `assignee_name` 字段

**建议**: 
- 后端 `TaskResponse` 应该添加 `assignee_name` 字段（从 `assigned_user` 关系获取）
- 或前端移除 `assignee_name` 字段

### 4.3 POST /tasks/ - 创建任务

**对齐状态**: ✅ **完全对齐**

### 4.4 PUT /tasks/{id} - 更新任务

**对齐状态**: ✅ **完全对齐**

### 4.5 DELETE /tasks/{id} - 删除任务

**对齐状态**: ✅ **完全对齐**

---

## 5. 报警接口对齐检查

### 5.1 GET /alerts/ - 获取报警列表

**后端实现** (`backend_system/app/api/endpoints/alerts.py:94-139`):
```python
@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    device_id: Optional[int] = Query(None),
    type: Optional[AlertType] = Query(None),
    severity: Optional[AlertSeverity] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    is_acknowledged: Optional[bool] = Query(None),
    ...
)
# 返回: AlertListResponse(items, total, skip, limit)
```

**前端实现** (`frontend_dashboard/src/api/alerts.ts:6-16`):
```typescript
getAll: (params?: AlertFilterParams): Promise<PaginatedResponse<Alert>>
```

**对齐状态**: ✅ **完全对齐**
- 所有过滤参数都匹配 ✅
- 响应格式一致 ✅

### 5.2 GET /alerts/stats - 获取报警统计

**后端响应** (`backend_system/app/schemas/alert.py:61-67`):
```python
class AlertStatsResponse(BaseModel):
    total_alerts: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    unacknowledged_count: int
    trend_24h: list[dict[str, Any]]
```

**前端类型** (`frontend_dashboard/src/types/api.d.ts:100-105`):
```typescript
export interface AlertStats {
  total_alerts: number;
  by_type: Record<AlertType, number>;
  by_severity: Record<AlertSeverity, number>;
  trend_24h: Array<{ hour: string; count: number }>;
}
```

**对齐状态**: ⚠️ **字段不一致**
- ✅ 对齐字段：total_alerts, by_type, by_severity, trend_24h
- ❌ 缺失字段：`unacknowledged_count` - 后端有，前端类型定义没有

**建议**: 前端类型定义应添加 `unacknowledged_count` 字段

### 5.3 PUT /alerts/{id}/acknowledge - 确认报警

**对齐状态**: ✅ **完全对齐**

---

## 6. 总结

### 6.1 对齐情况统计

| 接口模块 | 完全对齐 | 部分对齐 | 不一致 | 总计 |
|---------|---------|---------|--------|------|
| **设备接口** | 3 | 2 | 0 | 5 |
| **用户接口** | 3 | 2 | 0 | 5 |
| **任务接口** | 4 | 1 | 0 | 5 |
| **报警接口** | 2 | 1 | 0 | 3 |
| **总计** | 12 | 6 | 0 | 18 |

### 6.2 发现的问题

#### 🔴 严重问题

1. **用户列表接口分页不一致**
   - **位置**: `GET /users/`
   - **问题**: 后端接受 `skip`/`limit` 参数但返回普通列表，没有分页信息
   - **影响**: 前端无法实现分页功能
   - **建议**: 修改后端返回 `UserListResponse`（包含 items, total, skip, limit）

#### ⚠️ 中等问题

2. **设备更新接口缺少status字段**
   - **位置**: `PUT /devices/{id}`
   - **问题**: 后端支持更新 `status`，但前端类型定义不支持
   - **建议**: 创建 `UpdateDeviceParams` 类型，包含 `status` 字段

3. **任务响应缺少assignee_name字段**
   - **位置**: `GET /tasks/{id}`
   - **问题**: 前端类型有 `assignee_name`，但后端响应Schema没有
   - **建议**: 后端 `TaskResponse` 添加 `assignee_name` 字段

4. **报警统计缺少unacknowledged_count字段**
   - **位置**: `GET /alerts/stats`
   - **问题**: 后端响应有 `unacknowledged_count`，前端类型定义没有
   - **建议**: 前端类型定义添加该字段

#### 💡 轻微问题（可选）

5. **设备响应缺少部分字段**
   - `device_token`, `calibration_config`, `created_at`, `updated_at`
   - **建议**: 如果前端需要显示，添加到类型定义

6. **用户响应缺少created_at字段**
   - **建议**: 如果前端需要显示，添加到类型定义

### 6.3 修复优先级

1. **P0（必须修复）**: 用户列表接口分页问题
2. **P1（建议修复）**: 设备更新status字段、任务assignee_name字段、报警统计unacknowledged_count字段
3. **P2（可选）**: 其他缺失字段（如果前端需要显示）

---

## 7. 修复建议

### 7.1 修复用户列表接口分页

**后端修改** (`backend_system/app/schemas/user.py`):
```python
class UserListResponse(BaseModel):
    """用户列表响应"""
    items: list[UserResponse]
    total: int
    skip: int
    limit: int
```

**后端端点修改** (`backend_system/app/api/endpoints/users.py:22-36`):
```python
@router.get("/", response_model=UserListResponse)
async def list_users(...):
    # 计算总数
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar() or 0
    
    # 查询列表
    query = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )
```

**前端修改** (`frontend_dashboard/src/api/users.ts:6-8`):
```typescript
getAll: (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<User>>
```

### 7.2 修复设备更新接口

**前端类型定义** (`frontend_dashboard/src/types/api.d.ts`):
```typescript
export interface UpdateDeviceParams {
  name?: string;
  location?: string;
  ip_address?: string;
  status?: DeviceStatus;  // 添加此字段
}
```

**前端API修改** (`frontend_dashboard/src/api/devices.ts:21-23`):
```typescript
update: (id: number, data: UpdateDeviceParams): Promise<Device>
```

### 7.3 修复任务响应assignee_name字段

**后端Schema修改** (`backend_system/app/schemas/task.py:35-41`):
```python
class TaskResponse(TaskBase):
    id: int
    assignee_name: Optional[str] = None  # 添加此字段
    created_at: datetime
    updated_at: datetime
```

**后端端点修改** (`backend_system/app/api/endpoints/tasks.py`):
```python
# 在返回响应前，设置 assignee_name
if task.assigned_to and task.assigned_user:
    response.assignee_name = task.assigned_user.full_name or task.assigned_user.username
```

### 7.4 修复报警统计unacknowledged_count字段

**前端类型定义** (`frontend_dashboard/src/types/api.d.ts:100-105`):
```typescript
export interface AlertStats {
  total_alerts: number;
  by_type: Record<AlertType, number>;
  by_severity: Record<AlertSeverity, number>;
  unacknowledged_count: number;  // 添加此字段
  trend_24h: Array<{ hour: string; count: number }>;
}
```

---

**报告生成时间**: 2026-02-03  
**检查工具**: 代码对比和类型分析
