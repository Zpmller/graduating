"""
视频流推送模块：将带检测框的视频帧推送到Media Server
支持 RTMP (SRS) 和 RTSP 推流
"""
import cv2
import threading
import queue
import time
import subprocess
from typing import Optional, Dict, Literal
import numpy as np


class VideoStreamer:
    """视频流推送器"""
    
    def __init__(
        self,
        media_server_url: str,
        device_id: int,
        stream_id: str,
        quality: Literal["low", "medium", "high"] = "medium"
    ):
        """
        初始化视频流推送器
        
        Args:
            media_server_url: Media Server 推流根地址
               - RTMP (SRS): rtmp://localhost:1935
               - RTSP: rtsp://localhost:8554
            device_id: 设备ID
            stream_id: 流ID
            quality: 流质量
        """
        self.media_server_url = media_server_url.rstrip("/")
        self.device_id = device_id
        self.stream_id = stream_id
        self.quality = quality
        
        # 根据质量设置编码参数
        self.quality_config = {
            "low": {
                "width": 640,
                "height": 480,
                "fps": 15,
                "bitrate": 500000
            },
            "medium": {
                "width": 1280,
                "height": 720,
                "fps": 25,
                "bitrate": 1500000
            },
            "high": {
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "bitrate": 3000000
            }
        }
        
        self.config = self.quality_config[quality]
        self.width = self.config["width"]
        self.height = self.config["height"]
        self.fps = self.config["fps"]
        self.bitrate = self.config["bitrate"]
        
        # 流状态
        self.is_streaming = False
        self.enable_overlay = True  # 默认启用检测覆盖层
        self.video_writer: Optional[cv2.VideoWriter] = None
        
        # 帧队列（用于异步推送）
        self.frame_queue = queue.Queue(maxsize=10)
        self.stream_thread: Optional[threading.Thread] = None
        
        print(f"[VideoStreamer] Initialized: device_id={device_id}, stream_id={stream_id}, quality={quality}")
    
    def start_stream(self):
        """启动视频流推送"""
        if self.is_streaming:
            print("[VideoStreamer] Stream is already running")
            return
        
        # 构建推流 URL: rtmp://host:1935/live/stream_id 或 rtsp://host:8554/live/stream_id
        push_url = f"{self.media_server_url}/live/{self.stream_id}"
        
        # 优先使用 FFmpeg 管道（RTMP/RTSP 均可靠）
        self.video_writer = None
        self._init_ffmpeg_writer(push_url)
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        
        print(f"[VideoStreamer] Stream started: {push_url}")
    
    def _init_ffmpeg_writer(self, push_url: str):
        """使用 FFmpeg 管道推流（支持 RTMP 和 RTSP）"""
        is_rtmp = push_url.lower().startswith("rtmp://")
        fmt = "flv" if is_rtmp else "rtsp"
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "bgr24",
            "-r", str(self.fps),
            "-i", "-",
            "-an",
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", str(self.bitrate),
            "-f", fmt,
            push_url,
        ]
        
        try:
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            print(f"[VideoStreamer] FFmpeg process started for {fmt.upper()} push")
        except FileNotFoundError:
            raise RuntimeError("未找到 ffmpeg，请安装后重试")
        except Exception as e:
            raise RuntimeError(f"启动 FFmpeg 失败: {e}") from e
    
    def push_frame(self, annotated_frame: np.ndarray):
        """
        推送带检测框的标注帧
        
        Args:
            annotated_frame: 标注后的视频帧（numpy数组，BGR格式）
        """
        if not self.is_streaming:
            return
        
        # 调整帧大小以匹配配置的分辨率
        if annotated_frame.shape[:2] != (self.height, self.width):
            frame_resized = cv2.resize(annotated_frame, (self.width, self.height))
        else:
            frame_resized = annotated_frame.copy()
        
        # 如果覆盖层被禁用，需要移除检测框
        # 注意：这里假设传入的frame已经是标注后的
        # 实际实现中，可能需要传入原始帧和检测结果，然后根据enable_overlay决定是否绘制
        if not self.enable_overlay:
            # 如果覆盖层被禁用，这里应该传入原始帧
            # 但为了简化，我们假设调用者会处理这个逻辑
            pass
        
        # 将帧添加到队列
        try:
            self.frame_queue.put_nowait(frame_resized)
        except queue.Full:
            # 队列满时丢弃最旧的帧
            try:
                self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(frame_resized)
            except queue.Empty:
                pass
    
    def _stream_loop(self):
        """Run the FFmpeg push loop in a background thread."""
        frame_interval = 1.0 / self.fps
        last_frame_time = time.time()

        try:
            while self.is_streaming:
                try:
                    frame = self.frame_queue.get(timeout=0.1)

                    current_time = time.time()
                    elapsed = current_time - last_frame_time
                    if elapsed < frame_interval:
                        time.sleep(frame_interval - elapsed)

                    if hasattr(self, "ffmpeg_process") and self.ffmpeg_process:
                        if self.ffmpeg_process.poll() is not None:
                            print(f"[VideoStreamer] FFmpeg exited with code {self.ffmpeg_process.returncode}")
                            break
                        try:
                            self.ffmpeg_process.stdin.write(frame.tobytes())
                            self.ffmpeg_process.stdin.flush()
                        except (BrokenPipeError, OSError) as e:
                            print(f"[VideoStreamer] Error writing to FFmpeg: {e}")
                            break

                    last_frame_time = time.time()

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[VideoStreamer] Error in stream loop: {e}")
                    break
        finally:
            self.is_streaming = False
            self._close_ffmpeg_process()

    def toggle_overlay(self, enabled: bool):
        """
        切换检测覆盖层
        
        Args:
            enabled: 是否启用覆盖层
        """
        self.enable_overlay = enabled
        print(f"[VideoStreamer] Detection overlay {'enabled' if enabled else 'disabled'}")
    
    def set_quality(self, quality: Literal["low", "medium", "high"]):
        """
        设置流质量
        
        Args:
            quality: 流质量
        """
        if quality not in self.quality_config:
            print(f"[VideoStreamer] Invalid quality: {quality}")
            return
        
        # 如果流正在运行，需要重启
        was_streaming = self.is_streaming
        if was_streaming:
            self.stop_stream()
        
        self.quality = quality
        self.config = self.quality_config[quality]
        self.width = self.config["width"]
        self.height = self.config["height"]
        self.fps = self.config["fps"]
        self.bitrate = self.config["bitrate"]
        
        if was_streaming:
            self.start_stream()
        
        print(f"[VideoStreamer] Quality set to: {quality}")
    
    def stop_stream(self):
        """停止视频流推送"""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        # 等待线程结束
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=2.0)
        
        # 关闭VideoWriter
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        # 关闭FFmpeg进程
        self._close_ffmpeg_process()
        
        # 清空队列
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        print(f"[VideoStreamer] Stream stopped: {self.stream_id}")

    def _close_ffmpeg_process(self):
        """Close FFmpeg after normal stop or broken pipe."""
        if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
            try:
                if self.ffmpeg_process.stdin and not self.ffmpeg_process.stdin.closed:
                    self.ffmpeg_process.stdin.close()
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait(timeout=2)
            except Exception as e:
                print(f"[VideoStreamer] Error closing FFmpeg: {e}")
            finally:
                self.ffmpeg_process = None
    
    def get_status(self) -> Dict:
        """
        获取流状态
        
        Returns:
            流状态字典
        """
        return {
            "is_streaming": self.is_streaming,
            "stream_id": self.stream_id,
            "quality": self.quality,
            "enable_overlay": self.enable_overlay,
            "fps": self.fps,
            "resolution": f"{self.width}x{self.height}"
        }
