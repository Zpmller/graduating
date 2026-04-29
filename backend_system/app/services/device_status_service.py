"""
设备状态检测服务
提供主动检测设备在线状态的功能（ping、HTTP连接、RTSP连接等）
"""
import asyncio
import socket
import subprocess
import platform
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse
import httpx
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.device import Device, DeviceStatus
from app.core.config import settings


class DeviceStatusService:
    """设备状态检测服务"""
    
    def __init__(self):
        self.http_timeout = 3.0  # HTTP连接超时时间（秒）
        self.ping_timeout = 2.0  # Ping超时时间（秒）
        self.ping_count = 1  # Ping次数
        self.rtsp_timeout = 5.0  # RTSP连接超时时间（秒）
    
    def _is_ip_address(self, address: str) -> bool:
        """判断是否为IP地址（IPv4或IPv6）"""
        if not address:
            return False
        
        # 简单检查：不包含协议前缀（http://, rtsp://等）
        if '://' in address:
            return False
        
        # 检查IPv4格式
        parts = address.split('.')
        if len(parts) == 4:
            try:
                return all(0 <= int(part) <= 255 for part in parts)
            except ValueError:
                return False
        
        # 检查IPv6格式（简化版）
        if ':' in address:
            return True
        
        return False
    
    def _extract_ip_from_url(self, url: str) -> Optional[str]:
        """从URL中提取IP地址或主机名"""
        if not url:
            return None
        
        try:
            # 如果包含协议，解析URL
            if '://' in url:
                parsed = urlparse(url)
                host = parsed.hostname
                return host if host else None
            else:
                # 直接是IP或主机名
                return url.split(':')[0] if ':' in url else url
        except Exception:
            return None
    
    def _is_rtsp_url(self, url: str) -> bool:
        """判断是否为RTSP URL"""
        if not url:
            return False
        return url.lower().startswith('rtsp://')
    
    def _parse_rtsp_host_port(self, rtsp_url: str) -> Tuple[Optional[str], Optional[int]]:
        """从 RTSP URL 解析 host 与 port，用于 TCP 备用检测。默认端口 554。"""
        if not rtsp_url or not self._is_rtsp_url(rtsp_url):
            return None, None
        try:
            parsed = urlparse(rtsp_url)
            host = parsed.hostname
            port = parsed.port
            if port is None:
                port = 554
            return (host, port) if host else (None, None)
        except Exception:
            return None, None
    
    async def ping_device(self, ip_address: str) -> bool:
        """
        使用ping检测设备是否在线
        
        Args:
            ip_address: 设备IP地址
            
        Returns:
            True if device is reachable, False otherwise
        """
        if not ip_address:
            return False
        
        # 提取IP地址（如果传入的是URL）
        ip = self._extract_ip_from_url(ip_address)
        if not ip:
            return False
        
        # 判断操作系统，使用不同的ping命令
        system = platform.system().lower()
        
        try:
            if system == 'windows':
                # Windows: ping -n 1 -w 2000 <ip>
                cmd = ['ping', '-n', str(self.ping_count), '-w', str(int(self.ping_timeout * 1000)), ip]
            else:
                # Linux/Mac: ping -c 1 -W 2 <ip>
                cmd = ['ping', '-c', str(self.ping_count), '-W', str(int(self.ping_timeout)), ip]
            
            # 执行ping命令（超时时间稍长于ping_timeout）
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.ping_timeout + 1.0
                )
                
                # 检查返回码：0表示成功
                return process.returncode == 0
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False
                
        except Exception as e:
            print(f"[DeviceStatusService] Ping failed for {ip}: {e}")
            return False
    
    async def check_tcp_connection(self, ip_address: str, port: int = 80, timeout: float = 3.0) -> bool:
        """
        使用TCP连接检测设备是否在线
        
        Args:
            ip_address: 设备IP地址
            port: 端口号（默认80）
            timeout: 连接超时时间（秒）
            
        Returns:
            True if connection successful, False otherwise
        """
        if not ip_address:
            return False
        
        # 提取IP地址
        ip = self._extract_ip_from_url(ip_address)
        if not ip:
            return False
        
        try:
            # 创建socket连接
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            return False
        except Exception as e:
            print(f"[DeviceStatusService] TCP connection failed for {ip}:{port}: {e}")
            return False
    
    async def check_http_connection(self, url: str) -> bool:
        """
        使用HTTP请求检测设备是否在线
        
        Args:
            url: 设备URL（可以是http://ip或完整URL）
            
        Returns:
            True if HTTP request successful, False otherwise
        """
        if not url:
            return False
        
        # 如果URL不包含协议，添加http://
        if '://' not in url:
            url = f"http://{url}"
        
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                # 尝试HEAD请求（更轻量）
                response = await client.head(url, follow_redirects=True)
                return response.status_code < 500  # 4xx也算在线（服务器响应了）
        except httpx.TimeoutException:
            return False
        except httpx.ConnectError:
            return False
        except Exception as e:
            print(f"[DeviceStatusService] HTTP connection failed for {url}: {e}")
            return False
    
    async def check_rtsp_connection(self, rtsp_url: str) -> bool:
        """
        使用RTSP连接检测设备是否在线
        
        Args:
            rtsp_url: RTSP流地址（如：rtsp://192.168.1.100:8554/live/stream_id）
            
        Returns:
            True if RTSP stream is accessible, False otherwise
        """
        if not rtsp_url:
            return False
        
        if not CV2_AVAILABLE:
            print("[DeviceStatusService] OpenCV not available, skipping RTSP check")
            return False
        
        if not self._is_rtsp_url(rtsp_url):
            return False
        
        try:
            # 在线程池中执行OpenCV操作（因为OpenCV的VideoCapture是阻塞的）
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._check_rtsp_sync, rtsp_url),
                timeout=self.rtsp_timeout
            )
            return result
        except asyncio.TimeoutError:
            print(f"[DeviceStatusService] RTSP connection timeout for {rtsp_url}")
            return False
        except Exception as e:
            print(f"[DeviceStatusService] RTSP connection failed for {rtsp_url}: {e}")
            return False
    
    def _check_rtsp_sync(self, rtsp_url: str) -> bool:
        """
        同步检查RTSP流（在executor中运行）
        
        Args:
            rtsp_url: RTSP流地址
            
        Returns:
            True if stream is accessible, False otherwise
        """
        cap = None
        try:
            # 创建VideoCapture对象
            cap = cv2.VideoCapture(rtsp_url)
            
            # 设置超时时间（毫秒）
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(self.rtsp_timeout * 1000))
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(self.rtsp_timeout * 1000))
            
            # 尝试读取一帧
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # 成功读取到帧，说明流可用
                return True
            else:
                # 无法读取帧，流不可用
                return False
                
        except Exception as e:
            print(f"[DeviceStatusService] Error in RTSP sync check: {e}")
            return False
        finally:
            # 释放资源
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
    
    async def check_device_online(self, device: Device) -> bool:
        """
        综合检测设备是否在线
        按优先级尝试：
        - 如果是RTSP URL：RTSP连接检测
        - 否则：ping -> TCP连接 -> HTTP连接
        
        Args:
            device: 设备对象
            
        Returns:
            True if device is online, False otherwise
        """
        ip_address = device.ip_address
        if not ip_address:
            # 没有IP地址，无法主动检测，返回False（保持原状态）
            return False
        
        # 1. 如果是RTSP URL，优先使用RTSP检测
        if self._is_rtsp_url(ip_address):
            if await self.check_rtsp_connection(ip_address):
                return True
            # RTSP检测失败时，尝试对 RTSP 的 host:port 做 TCP 连接检测（备用）
            # 避免因 OpenCV 不可用/超时导致“可用 RTSP 显示不在线”
            host, port = self._parse_rtsp_host_port(ip_address)
            if host and port and await self.check_tcp_connection(host, port, timeout=3.0):
                return True
            # 继续尝试其他方式
        
        # 2. 尝试ping（最快）
        if self._is_ip_address(ip_address):
            if await self.ping_device(ip_address):
                return True
        
        # 3. 尝试TCP连接（端口80）
        if await self.check_tcp_connection(ip_address, port=80, timeout=2.0):
            return True
        
        # 4. 尝试HTTP连接
        if await self.check_http_connection(ip_address):
            return True
        
        return False
    
    async def check_heartbeat_timeout(self, device: Device) -> bool:
        """
        检查设备心跳是否超时（超时或从未心跳时返回 True，以触发主动检测）
        
        Args:
            device: 设备对象
            
        Returns:
            True 表示需要做主动检测（心跳超时或从未心跳），False 表示心跳正常无需检测
        """
        if not device.last_heartbeat:
            # 从未发送过心跳，视为需主动检测，便于通过 RTSP/Ping/HTTP 将设备标为在线
            return True
        
        # 计算心跳时间差
        time_diff = datetime.utcnow() - device.last_heartbeat
        
        # 超过超时时间则需主动检测
        return time_diff.total_seconds() > settings.HEARTBEAT_TIMEOUT_SECONDS
    
    async def update_device_status(
        self,
        device: Device,
        db: AsyncSession,
        force_offline: bool = False
    ) -> bool:
        """
        更新设备状态
        
        Args:
            device: 设备对象
            db: 数据库会话
            force_offline: 是否强制设置为离线
            
        Returns:
            True if status changed, False otherwise
        """
        old_status = device.status
        
        if force_offline:
            new_status = DeviceStatus.OFFLINE
        else:
            # 检查心跳超时
            heartbeat_timeout = await self.check_heartbeat_timeout(device)
            
            if heartbeat_timeout:
                # 心跳超时，尝试主动检测
                is_online = await self.check_device_online(device)
                new_status = DeviceStatus.ONLINE if is_online else DeviceStatus.OFFLINE
            else:
                # 心跳正常，保持在线状态
                new_status = DeviceStatus.ONLINE if device.status == DeviceStatus.ONLINE else DeviceStatus.OFFLINE
        
        # 更新状态
        if old_status != new_status:
            device.status = new_status
            device.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(device)
            print(f"[DeviceStatusService] Device {device.id} ({device.name}) status changed: {old_status.value} -> {new_status.value}")
            return True
        
        return False
    
    async def check_all_devices(self, db: AsyncSession) -> dict:
        """
        检查所有设备的状态
        
        Args:
            db: 数据库会话
            
        Returns:
            统计信息字典
        """
        # 获取所有设备
        result = await db.execute(select(Device))
        devices = result.scalars().all()
        
        stats = {
            'total': len(devices),
            'checked': 0,
            'status_changed': 0,
            'online': 0,
            'offline': 0,
            'maintenance': 0
        }
        
        for device in devices:
            try:
                # 跳过维护状态的设备
                if device.status == DeviceStatus.MAINTENANCE:
                    stats['maintenance'] += 1
                    continue
                
                # 检查并更新状态
                changed = await self.update_device_status(device, db)
                
                if changed:
                    stats['status_changed'] += 1
                
                # 统计当前状态
                if device.status == DeviceStatus.ONLINE:
                    stats['online'] += 1
                elif device.status == DeviceStatus.OFFLINE:
                    stats['offline'] += 1
                
                stats['checked'] += 1
                
            except Exception as e:
                print(f"[DeviceStatusService] Error checking device {device.id}: {e}")
        
        return stats


# 创建单例
device_status_service = DeviceStatusService()
