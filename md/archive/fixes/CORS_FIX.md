# CORS问题修复说明

> **日期**: 2026-02-03  
> **问题**: 添加设备时出现CORS错误和500错误

## 问题分析

### 1. CORS错误

**错误信息**:
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/devices/' from origin 'http://localhost:5173' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**原因**:
- 当后端返回500错误时，异常处理器返回的响应没有包含CORS头
- FastAPI的CORSMiddleware虽然配置正确，但异常处理器返回的响应可能绕过了中间件

**修复**:
- 在所有异常处理器中添加CORS头
- 确保所有错误响应都包含 `Access-Control-Allow-Origin` 和 `Access-Control-Allow-Credentials` 头

### 2. 500 Internal Server Error

**可能原因**:
1. 数据库操作失败
2. 字段验证失败
3. 服务器内部错误

**需要检查**:
- 后端服务器日志
- 数据库连接状态
- 设备创建逻辑

## 修复内容

### 1. 全局异常处理器 (`backend_system/app/main.py`)

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    error_msg = f"Global Exception: {str(exc)}\n{traceback.format_exc()}"
    print(error_msg)  # 打印到控制台
    
    # 获取请求的Origin，用于CORS响应头
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.cors_origins_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "message": str(exc),
            "trace": traceback.format_exc() if settings.DEBUG else None
        },
        headers=headers
    )
```

### 2. 自定义异常处理器 (`backend_system/app/core/exceptions.py`)

```python
async def custom_exception_handler(request: Request, exc: CustomException):
    """自定义异常处理器"""
    status_code = getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST)
    
    # 添加CORS头
    from app.core.config import settings
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.cors_origins_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    
    return JSONResponse(
        status_code=status_code,
        content={...},
        headers=headers
    )
```

### 3. 验证异常处理器 (`backend_system/app/core/exceptions.py`)

```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """验证异常处理器"""
    # 添加CORS头
    from app.core.config import settings
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.cors_origins_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={...},
        headers=headers
    )
```

### 4. 数据库异常处理器 (`backend_system/app/core/exceptions.py`)

```python
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理器"""
    # 添加CORS头
    from app.core.config import settings
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.cors_origins_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={...},
        headers=headers
    )
```

## 验证步骤

1. **重启后端服务器**:
   ```bash
   # 停止当前服务器，然后重新启动
   cd backend_system
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **检查CORS配置**:
   - 确认 `.env` 文件中的 `CORS_ORIGINS` 包含 `http://localhost:5173`
   - 检查后端启动日志，确认CORS配置已加载

3. **测试设备创建**:
   - 打开浏览器开发者工具（Network标签）
   - 尝试创建设备
   - 检查响应头，确认包含：
     - `Access-Control-Allow-Origin: http://localhost:5173`
     - `Access-Control-Allow-Credentials: true`

4. **检查后端日志**:
   - 如果仍然出现500错误，查看后端控制台输出
   - 检查错误堆栈跟踪，找出具体错误原因

## 调试500错误

如果仍然出现500错误，请检查：

1. **数据库连接**:
   ```bash
   # 检查数据库是否运行
   mysql -u root -p -e "SELECT 1"
   ```

2. **后端日志**:
   - 查看后端控制台输出的错误信息
   - 检查 `Global Exception` 日志

3. **设备创建数据**:
   - 确认请求数据格式正确
   - 检查必填字段是否都有值
   - 确认设备名称不重复

4. **数据库表结构**:
   ```sql
   -- 检查devices表是否存在
   SHOW TABLES LIKE 'devices';
   
   -- 检查表结构
   DESCRIBE devices;
   ```

## 相关文件

- `backend_system/app/main.py` - FastAPI应用入口和全局异常处理器
- `backend_system/app/core/exceptions.py` - 自定义异常处理器
- `backend_system/app/core/config.py` - CORS配置
- `backend_system/.env` - 环境变量配置

## 注意事项

1. **CORS配置**:
   - 确保 `.env` 文件中的 `CORS_ORIGINS` 包含所有需要的前端地址
   - 开发环境：`http://localhost:5173`, `http://localhost:3000`
   - 生产环境：需要配置实际的前端域名

2. **异常处理顺序**:
   - FastAPI的异常处理器按注册顺序执行
   - 全局异常处理器会捕获所有未处理的异常

3. **调试模式**:
   - 如果 `DEBUG=True`，错误响应会包含详细的堆栈跟踪
   - 生产环境应设置 `DEBUG=False`

---

**修复完成时间**: 2026-02-03  
**下一步**: 重启后端服务器并测试设备创建功能
