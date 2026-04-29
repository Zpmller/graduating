"""
配置管理模块
使用Pydantic Settings加载环境变量
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    DATABASE_URL: str = Field(
        default="mysql+aiomysql://root:password@localhost:3306/safety_monitoring",
        description="数据库连接URL"
    )
    DB_POOL_SIZE: int = Field(default=10, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=20, description="数据库连接池最大溢出")
    
    # 安全配置
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        description="JWT密钥"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_EXPIRATION_SECONDS: int = Field(default=3600, description="JWT过期时间（秒）")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # 文件存储配置
    EVIDENCE_DIR: str = Field(default="static/evidence", description="证据图片存储目录")
    FACE_DIR: str = Field(default="static/faces", description="人脸库图片存储目录")
    CALIBRATION_TEMP_DIR: str = Field(default="static/calibration_temp", description="标定临时文件目录")
    CALIBRATION_SCRIPT_PATH: str = Field(default="scripts/calibrate.py", description="标定脚本路径")
    MAX_UPLOAD_SIZE: int = Field(default=10485760, description="最大上传文件大小（字节，10MB）")
    
    # CORS配置
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="允许的CORS源（逗号分隔）"
    )
    
    # 设备心跳配置
    HEARTBEAT_TIMEOUT_SECONDS: int = Field(default=300, description="心跳超时时间（秒，5分钟）")
    
    # 设备状态检测配置
    DEVICE_STATUS_CHECK_INTERVAL: int = Field(default=60, description="设备状态检测间隔（秒，默认60秒）")
    DEVICE_STATUS_CHECK_ENABLED: bool = Field(default=True, description="是否启用设备状态主动检测")
    
    # Media Server配置（SRS）
    MEDIA_SERVER_URL: str = Field(
        default="http://localhost:1985",
        description="Media Server HTTP API 地址（WHEP 等）"
    )
    MEDIA_SERVER_RTMP_URL: str = Field(
        default="rtmp://localhost:1935",
        description="Media Server RTMP 推流地址（Edge 推流用）"
    )
    MEDIA_SERVER_RTSP_URL: str = Field(
        default="rtsp://localhost:8554",
        description="Media Server RTSP 推流地址（备用）"
    )
    MEDIA_SERVER_WS_URL: str = Field(
        default="ws://localhost:8080",
        description="Media Server WebSocket 信令地址（备用）"
    )
    # Edge 零配置引导（Bootstrap）
    BOOTSTRAP_SECRET: Optional[str] = Field(
        default=None,
        description="Bootstrap API 密钥，留空则开放访问，生产环境建议设置"
    )

    # Edge 控制配置
    EDGE_CONTROL_PORT: int = Field(default=8080, description="Edge 控制服务端口")
    EDGE_CONTROL_HOST: str = Field(
        default="",
        description="Edge 控制主机（当设备 ip 为摄像头 RTSP 时使用，空则从 ip 解析 host）"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """将CORS_ORIGINS字符串转换为列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
