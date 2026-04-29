# 认证问题修复说明

> **日期**: 2026-02-03  
> **问题**: 设备创建/更新时出现 Authorization header 缺失和 500 错误

## 问题分析

### 1. Authorization Header 缺失错误

**错误信息**:
```json
{
  "detail": [{
    "type": "missing",
    "loc": ["header", "Authorization"],
    "msg": "Field required",
    "input": null
  }],
  "error_code": "VALIDATION_ERROR"
}
```

**原因**:
- FastAPI 的 `Header(..., alias="Authorization")` 在 header 不存在时会抛出验证错误
- 需要将 header 设为可选，然后手动检查

**修复**:
- 修改 `backend_system/app/api/deps.py` 中的 `get_current_user` 函数
- 将 `Header(..., alias="Authorization")` 改为 `Header(None, alias="Authorization")`
- 添加手动检查逻辑

### 2. 500 Internal Server Error

**错误信息**:
```
POST http://localhost:5173/api/v1/devices/ 500 (Internal Server Error)
```

**原因**:
- `.env` 文件中的 `VITE_API_URL=/api/v1` 是相对路径
- 导致请求被发送到前端开发服务器（`http://localhost:5173`）而不是后端服务器（`http://localhost:8000`）
- Vite 开发服务器没有这个路由，返回 500 错误

**修复**:
- 修改 `frontend_dashboard/.env` 文件
- 将 `VITE_API_URL=/api/v1` 改为 `VITE_API_URL=http://localhost:8000/api/v1`

## 修复内容

### 1. 后端修复 (`backend_system/app/api/deps.py`)

```python
async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前登录用户（JWT认证）
    
    Header格式: Authorization: Bearer {token}
    """
    if not authorization:
        raise AuthenticationError("缺少认证token")
    
    # 提取token
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("无效的认证格式")
    
    token = authorization.replace("Bearer ", "").strip()
    
    if not token:
        raise AuthenticationError("token不能为空")
    
    # ... 其余代码保持不变
```

### 2. 前端修复 (`frontend_dashboard/.env`)

```env
# 修改前
VITE_API_URL=/api/v1

# 修改后
VITE_API_URL=http://localhost:8000/api/v1
```

### 3. 前端 axios 拦截器优化 (`frontend_dashboard/src/api/axios.ts`)

```typescript
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // Ensure headers object exists
      if (!config.headers) {
        config.headers = {} as any;
      }
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
```

## 验证步骤

1. **检查后端服务是否运行**:
   ```bash
   # 后端应该在 http://localhost:8000 运行
   curl http://localhost:8000/api/v1/system/health
   ```

2. **检查前端环境变量**:
   - 确认 `.env` 文件中的 `VITE_API_URL` 指向正确的后端地址
   - 重启前端开发服务器（Vite 需要重启才能读取新的环境变量）

3. **检查 localStorage**:
   - 打开浏览器开发者工具
   - 检查 `localStorage.getItem('access_token')` 是否有值
   - 如果没有，需要先登录

4. **测试设备创建**:
   - 登录系统（确保有 admin 权限）
   - 尝试创建设备
   - 检查网络请求，确认：
     - 请求 URL 是 `http://localhost:8000/api/v1/devices/`
     - 请求头包含 `Authorization: Bearer {token}`

## 注意事项

1. **环境变量**:
   - 开发环境：`VITE_API_URL=http://localhost:8000/api/v1`
   - 生产环境：需要根据实际部署情况配置

2. **CORS 配置**:
   - 确保后端 CORS 配置允许前端域名
   - 检查 `backend_system/app/core/config.py` 中的 `CORS_ORIGINS`

3. **Token 存储**:
   - Token 存储在 `localStorage` 中，key 为 `access_token`
   - 如果 token 过期，需要重新登录

4. **权限检查**:
   - 设备创建/更新需要 admin 权限
   - 确保登录用户角色为 `admin`

## 相关文件

- `backend_system/app/api/deps.py` - 认证依赖注入
- `frontend_dashboard/.env` - 前端环境变量
- `frontend_dashboard/src/api/axios.ts` - Axios 配置和拦截器
- `frontend_dashboard/src/store/auth.ts` - 认证状态管理

---

**修复完成时间**: 2026-02-03
