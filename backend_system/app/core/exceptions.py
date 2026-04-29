"""
自定义异常处理
"""
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError


class CustomException(Exception):
    """自定义异常基类"""
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class AuthenticationError(CustomException):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, "AUTH_ERROR")
        self.status_code = status.HTTP_401_UNAUTHORIZED  # 认证错误应该返回401


class AuthorizationError(CustomException):
    """授权错误"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "AUTHORIZATION_ERROR")
        self.status_code = status.HTTP_403_FORBIDDEN  # 权限错误应该返回403


class NotFoundError(CustomException):
    """资源未找到错误"""
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message, "NOT_FOUND")


async def custom_exception_handler(request: Request, exc: CustomException):
    """自定义异常处理器"""
    # 如果异常有status_code属性，使用它；否则默认400
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
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        headers=headers
    )


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
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        headers=headers
    )


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
        content={
            "detail": "数据库操作失败",
            "error_code": "DATABASE_ERROR",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        headers=headers
    )
