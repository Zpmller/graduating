"""
后台定时任务管理
"""
import asyncio
import logging
from typing import Optional
from app.core.config import settings
from app.db.session import get_db
from app.services.device_status_service import device_status_service

logger = logging.getLogger(__name__)


class BackgroundTasks:
    """后台任务管理器"""
    
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def device_status_check_task(self):
        """设备状态检测定时任务"""
        logger.info("[BackgroundTasks] Device status check task started")
        
        while self._running:
            try:
                if not settings.DEVICE_STATUS_CHECK_ENABLED:
                    logger.debug("[BackgroundTasks] Device status check is disabled")
                    await asyncio.sleep(settings.DEVICE_STATUS_CHECK_INTERVAL)
                    continue
                
                # 获取数据库会话
                async for db in get_db():
                    try:
                        # 执行设备状态检查
                        stats = await device_status_service.check_all_devices(db)
                        
                        logger.info(
                            f"[BackgroundTasks] Device status check completed: "
                            f"total={stats['total']}, checked={stats['checked']}, "
                            f"status_changed={stats['status_changed']}, "
                            f"online={stats['online']}, offline={stats['offline']}, "
                            f"maintenance={stats['maintenance']}"
                        )
                    except Exception as e:
                        logger.error(f"[BackgroundTasks] Error in device status check: {e}", exc_info=True)
                    finally:
                        break  # 只使用第一个会话
                
                # 等待下次检查
                await asyncio.sleep(settings.DEVICE_STATUS_CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("[BackgroundTasks] Device status check task cancelled")
                break
            except Exception as e:
                logger.error(f"[BackgroundTasks] Unexpected error in device status check task: {e}", exc_info=True)
                # 发生错误时等待一段时间再重试
                await asyncio.sleep(settings.DEVICE_STATUS_CHECK_INTERVAL)
    
    async def start(self):
        """启动所有后台任务"""
        if self._running:
            logger.warning("[BackgroundTasks] Background tasks already running")
            return
        
        self._running = True
        
        # 启动设备状态检测任务
        if settings.DEVICE_STATUS_CHECK_ENABLED:
            self._task = asyncio.create_task(self.device_status_check_task())
            logger.info(f"[BackgroundTasks] Started device status check task (interval: {settings.DEVICE_STATUS_CHECK_INTERVAL}s)")
        else:
            logger.info("[BackgroundTasks] Device status check task is disabled in config")
    
    async def stop(self):
        """停止所有后台任务"""
        if not self._running:
            return
        
        self._running = False
        
        # 取消任务
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("[BackgroundTasks] All background tasks stopped")


# 创建全局任务管理器实例
background_tasks = BackgroundTasks()
