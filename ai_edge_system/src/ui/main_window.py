import sys
import os
import threading
import cv2
import time
import datetime
import winsound # For sound alerts (Windows)
from typing import Optional
from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLineEdit, QFileDialog, 
                             QListWidget, QGroupBox, QComboBox, QMessageBox,
                             QSlider, QSpinBox, QDoubleSpinBox, QFormLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

from src.core.detector import Detector
from src.core.uploader import AlertUploader
from src.core.face_client import FaceClient
from src.core.streamer import VideoStreamer
from src.core.device_config import fetch_device_config, DeviceConfig
from src.logic.safety import SafetyEngine
from src.enhancer import ImageEnhancer
from src.utils.calibration_tool import CalibrationTool
from src.api.stream_control_server import set_main_window, run_control_server

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Mining Hot-Work Safety Monitoring System")
        self.resize(1280, 800)
        
        # Initialize Core Modules
        # Construct absolute path to the model
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, 'models', 'best.pt')
        
        if os.path.exists(model_path):
            print(f"Loading custom model from: {model_path}")
            self.detector = Detector(model_path=model_path)
        else:
            print(f"Custom model not found at {model_path}, using default yolo11m.pt")
            self.detector = Detector(model_path='yolo11m.pt') 
            
        self.safety_engine = SafetyEngine()
        self.enhancer = ImageEnhancer(method='clahe')
        self.uploader = AlertUploader()
        self.face_client = FaceClient()  # 人脸库与后端同步、注册时上传
        
        # Video Streaming State（SRS 使用 RTMP 推流）
        self.video_streamer: Optional[VideoStreamer] = None
        self.stream_config = {
            "device_id": None,
            "media_server_url": os.getenv("MEDIA_SERVER_RTMP_URL")
            or os.getenv("MEDIA_SERVER_RTSP_URL", "rtmp://localhost:1935"),
            "stream_id": None,
            "quality": "medium",
        }

        # Configuration State
        self.conf_threshold = 0.25
        
        # UI Setup
        self.init_ui()
        
        # Camera Setup
        self.cap = None
        self.capture_source = None
        self.capture_backend = cv2.CAP_ANY
        self.capture_is_network = False
        self.frame_read_failures = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_monitoring = False

        # Sound Alert Config
        self.last_sound_time = 0
        self.sound_cooldown = 3.0 # Seconds between beeps
        
        # Visual Alert Persistence
        self.last_visual_alert_time = 0
        self.visual_alert_duration = 1.0  # Keep red frame for 2 seconds
        self.current_visual_message = ""

        # HTTP 控制服务（供后端通知推流）
        self._control_server_thread: Optional[object] = None

        # 设备配置（从后端自动获取，用于心跳、视频源、推流）
        self.device_config: Optional[DeviceConfig] = None

    def showEvent(self, event):
        """窗口显示时启动 HTTP 控制服务"""
        super().showEvent(event)
        if self._control_server_thread is None:
            set_main_window(self)
            port = int(os.getenv("EDGE_CONTROL_PORT", "8080"))
            self._control_server_thread = threading.Thread(
                target=lambda: run_control_server(port),
                daemon=True,
            )
            self._control_server_thread.start()
            self.log_message(f"Edge 控制服务已启动: http://0.0.0.0:{port}/api/stream/control", "info")

        # 自动从后端获取设备配置（在后台线程执行，避免阻塞 UI）
        if self.device_config is None:
            threading.Thread(target=self._load_device_config, daemon=True).start()

    def _sync_faces_from_backend(self):
        """从后端拉取人脸库到本地 face_db（后台线程调用）"""
        db_path = self.safety_engine.face_recognizer.db_path
        ok, msg = self.face_client.sync_to_local(db_path)
        if ok:
            self._clear_face_representations_cache()
            self.log_message(f"人脸库同步: {msg}", "info")
        else:
            self.log_message(f"人脸库同步失败: {msg}", "error")

    def _clear_face_representations_cache(self):
        """清除 DeepFace 缓存，使新同步的图片生效"""
        import glob
        pkl_pattern = os.path.join(self.safety_engine.face_recognizer.db_path, "representations_*.pkl")
        for p in glob.glob(pkl_pattern):
            try:
                os.remove(p)
            except Exception:
                pass

    def sync_faces_from_backend_clicked(self):
        """按钮：从后端同步人脸库"""
        self.btn_sync_faces.setEnabled(False)
        def _run():
            self._sync_faces_from_backend()
            try:
                self.btn_sync_faces.setEnabled(True)
            except RuntimeError:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _load_device_config(self):
        """从后端自动获取设备配置并应用"""
        cfg = fetch_device_config()
        if cfg:
            self.device_config = cfg
            self.uploader.set_device_config(
                device_id=cfg.device_id,
                device_token=cfg.device_token,
                backend_url=cfg.backend_url,
            )
            if cfg.backend_url:
                self.face_client.backend_url = cfg.backend_url.rstrip("/")
            if cfg.device_token:
                self.face_client._session.headers["X-Device-Token"] = cfg.device_token
            # 从后端同步人脸库到本地，供授权检测使用
            threading.Thread(target=self._sync_faces_from_backend, daemon=True).start()
            self.stream_config["device_id"] = cfg.device_id
            # 若后端配置了视频源地址，自动填充到输入框
            if cfg.ip_address and hasattr(self, "source_input"):
                def _set_source():
                    if hasattr(self, "source_input"):
                        self.source_input.setText(cfg.ip_address or "0")
                    self.log_message(f"已加载设备配置: {cfg.name} (ID={cfg.device_id})", "info")
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, _set_source)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main Layout (Horizontal: Video | Sidebar)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # --- Left Side: Video Display ---
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        
        self.video_label = QLabel("Video Feed Disconnected")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white; border: 2px solid #444;")
        self.video_label.setMinimumSize(800, 600)
        
        self.video_layout.addWidget(self.video_label)
        self.main_layout.addWidget(self.video_container, stretch=3)
        
        # --- Right Side: Sidebar (Controls & Logs) ---
        self.sidebar = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        
        # 1. Source Selection Group
        self.source_group = QGroupBox("Video Source")
        self.source_layout = QVBoxLayout()
        
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Camera (0) / RTSP / HTTP / File Path")
        self.source_input.setText("0") # Default to webcam
        
        self.btn_browse = QPushButton("Browse Video File")
        self.btn_browse.clicked.connect(self.browse_file)
        
        self.source_layout.addWidget(self.source_input)
        self.source_layout.addWidget(self.btn_browse)
        self.source_group.setLayout(self.source_layout)
        self.sidebar_layout.addWidget(self.source_group)
        
        # 2. Control Group
        self.control_group = QGroupBox("Controls")
        self.control_layout = QVBoxLayout()
        
        self.btn_start = QPushButton("Start Monitoring")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_start.clicked.connect(self.toggle_monitoring)
        
        self.control_layout.addWidget(self.btn_start)
        
        # 3. User Registration Group
        self.reg_group = QGroupBox("User Registration")
        self.reg_layout = QVBoxLayout()
        
        self.reg_name_input = QLineEdit()
        self.reg_name_input.setPlaceholderText("Enter Name")
        
        self.btn_reg_cam = QPushButton("Register from Camera")
        self.btn_reg_cam.clicked.connect(self.register_from_camera)
        
        self.btn_reg_file = QPushButton("Register from File")
        self.btn_reg_file.clicked.connect(self.register_from_file)
        self.btn_sync_faces = QPushButton("从后端同步人脸库")
        self.btn_sync_faces.clicked.connect(self.sync_faces_from_backend_clicked)
        self.reg_layout.addWidget(self.reg_name_input)
        self.reg_layout.addWidget(self.btn_reg_cam)
        self.reg_layout.addWidget(self.btn_reg_file)
        self.reg_layout.addWidget(self.btn_sync_faces)
        self.reg_group.setLayout(self.reg_layout)
        self.sidebar_layout.addWidget(self.reg_group)

        self.control_group.setLayout(self.control_layout)
        self.sidebar_layout.addWidget(self.control_group)

        # 2.5 Configuration Group
        self.config_group = QGroupBox("Configuration Parameters")
        self.config_layout = QFormLayout()

        # Confidence Threshold Slider
        self.slider_conf = QSlider(Qt.Horizontal)
        self.slider_conf.setRange(1, 100)
        self.slider_conf.setValue(int(self.conf_threshold * 100))
        self.slider_conf.valueChanged.connect(self.update_conf_threshold)
        self.label_conf = QLabel(f"{self.conf_threshold:.2f}")
        self.config_layout.addRow("Confidence:", self.slider_conf)
        self.config_layout.addRow("", self.label_conf)

        # Min Cylinder Distance
        self.spin_dist = QDoubleSpinBox()
        self.spin_dist.setRange(0.5, 20.0)
        self.spin_dist.setSingleStep(0.5)
        self.spin_dist.setValue(self.safety_engine.MIN_CYLINDER_DISTANCE)
        self.spin_dist.setSuffix(" m")
        self.spin_dist.valueChanged.connect(self.update_distance_threshold)
        self.config_layout.addRow("Min Cyl Dist:", self.spin_dist)

        self.spin_cyl_dist_avg = QSpinBox()
        self.spin_cyl_dist_avg.setRange(1, 60)
        self.spin_cyl_dist_avg.setValue(self.safety_engine.CYLINDER_DISTANCE_FILTER_WINDOW)
        self.spin_cyl_dist_avg.setSuffix(" frames")
        self.spin_cyl_dist_avg.setToolTip("气瓶间距 Bar(D) 滑动平均窗口 T")
        self.spin_cyl_dist_avg.valueChanged.connect(self.update_cylinder_dist_filter_window)
        self.config_layout.addRow("Cyl Dist Avg T:", self.spin_cyl_dist_avg)

        # Consistency Threshold (Frames)
        self.spin_consist = QSpinBox()
        self.spin_consist.setRange(1, 60)
        self.spin_consist.setValue(self.safety_engine.CONSISTENCY_THRESHOLD)
        self.spin_consist.setSuffix(" frames")
        self.spin_consist.valueChanged.connect(self.update_consistency_threshold)
        self.config_layout.addRow("Consistency:", self.spin_consist)

        # Alert Cooldown
        self.spin_cooldown = QDoubleSpinBox()
        self.spin_cooldown.setRange(0.5, 60.0)
        self.spin_cooldown.setSingleStep(0.5)
        self.spin_cooldown.setValue(self.safety_engine.alert_cooldown)
        self.spin_cooldown.setSuffix(" s")
        self.spin_cooldown.valueChanged.connect(self.update_alert_cooldown)
        self.config_layout.addRow("Alert Cooldown:", self.spin_cooldown)

        self.config_group.setLayout(self.config_layout)
        self.sidebar_layout.addWidget(self.config_group)

        # 2.6 Tools Group
        self.tools_group = QGroupBox("Tools")
        self.tools_layout = QVBoxLayout()
        
        self.btn_calibration = QPushButton("Camera Calibration")
        self.btn_calibration.clicked.connect(self.open_calibration_tool)
        self.tools_layout.addWidget(self.btn_calibration)
        
        self.tools_group.setLayout(self.tools_layout)
        self.sidebar_layout.addWidget(self.tools_group)
        
        # 3. Alarm/Log Panel
        self.log_group = QGroupBox("System Logs & Alarms")
        self.log_layout = QVBoxLayout()
        
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("background-color: #f0f0f0;")
        
        self.log_layout.addWidget(self.log_list)
        self.log_group.setLayout(self.log_layout)
        self.sidebar_layout.addWidget(self.log_group, stretch=1)
        
        self.main_layout.addWidget(self.sidebar, stretch=1)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.source_input.setText(file_path)

    def open_calibration_tool(self):
        self.calibration_window = CalibrationTool()
        self.calibration_window.show()

    def toggle_monitoring(self):
        if not self.is_monitoring:
            self.start_camera()
        else:
            self.stop_camera()

    def register_from_file(self):
        name = self.reg_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name first.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Open Photo", "", "Image Files (*.jpg *.png *.jpeg)")
        if file_path:
            img = cv2.imread(file_path)
            if img is not None:
                success, msg = self.safety_engine.face_recognizer.register_face(img, name)
                if success:
                    up_ok, up_msg = self.face_client.upload_face(img, name)
                    if up_ok:
                        self.log_message(f"已注册并上传到后端: {name}", "info")
                    else:
                        self.log_message(f"已本地注册，上传后端失败: {up_msg}", "error")
                    QMessageBox.information(self, "Success", f"User {name} registered successfully!")
                    self.log_message(f"Registered user: {name}", "info")
                else:
                    QMessageBox.critical(self, "Error", f"Registration failed: {msg}")
            else:
                QMessageBox.critical(self, "Error", "Could not read image file.")

    def register_from_camera(self):
        name = self.reg_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name first.")
            return

        if not self.cap or not self.cap.isOpened():
            # Try to open default camera temporarily if not monitoring
            temp_cap = cv2.VideoCapture(0)
            if not temp_cap.isOpened():
                QMessageBox.critical(self, "Error", "Cannot open camera for registration.")
                return
            ret, frame = temp_cap.read()
            temp_cap.release()
        else:
            # Use current frame
            ret, frame = self.cap.read()
            
        if ret:
            # Detect face in frame to ensure quality
            # Using simple center crop or detector? 
            # Let's use the detector to find the largest face
            results = self.detector.detect(frame, classes=[0]) # 0 is face in our model? Or we use logic?
            # Actually our YOLO model has 'face' class. Let's assume class 0 is face based on previous memory.
            # Names: ['face', 'fire', 'smoke', 'sparks', 'gas_cylinder', 'helmet', 'no-helmet']  # nc=7
            # So index 0 is face.
            
            detections = self.detector.get_detections_list(results)
            faces = [d for d in detections if d['class_name'] == 'face']
            
            target_face = None
            if faces:
                # Find largest face
                faces.sort(key=lambda x: (x['box'][2]-x['box'][0]) * (x['box'][3]-x['box'][1]), reverse=True)
                largest_face = faces[0]
                x1, y1, x2, y2 = map(int, largest_face['box'])
                
                # Add some padding
                h, w = frame.shape[:2]
                x1 = max(0, x1 - 20)
                y1 = max(0, y1 - 20)
                x2 = min(w, x2 + 20)
                y2 = min(h, y2 + 20)
                
                target_face = frame[y1:y2, x1:x2]
            else:
                # No face detected, ask user if they want to save full frame?
                # Or just warn
                reply = QMessageBox.question(self, "No Face Detected", 
                                           "No face detected by AI. Save full frame anyway?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    target_face = frame
            
            if target_face is not None:
                success, msg = self.safety_engine.face_recognizer.register_face(target_face, name)
                if success:
                    up_ok, up_msg = self.face_client.upload_face(target_face, name)
                    if up_ok:
                        self.log_message(f"已注册并上传到后端: {name}", "info")
                    else:
                        self.log_message(f"已本地注册，上传后端失败: {up_msg}", "error")
                    QMessageBox.information(self, "Success", f"User {name} registered successfully!")
                    self.log_message(f"Registered user from camera: {name}", "info")
                else:
                    QMessageBox.critical(self, "Error", f"Registration failed: {msg}")
        else:
            QMessageBox.critical(self, "Error", "Could not capture frame from camera.")

    def _open_capture(self, source, capture_backend):
        if capture_backend == cv2.CAP_FFMPEG:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|timeout;5000000|max_delay;500000"
            )
            cap = cv2.VideoCapture(source, capture_backend)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
        return cv2.VideoCapture(source, capture_backend)

    def _reconnect_capture(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.cap = self._open_capture(self.capture_source, self.capture_backend)
        if self.cap.isOpened():
            self.frame_read_failures = 0
            self.log_message("Reconnected video source", "info")
            return True
        self.log_message("Reconnect failed: Could not open video source", "error")
        return False

    def start_camera(self):
        source_text = self.source_input.text().strip()
        source = source_text
        capture_backend = cv2.CAP_ANY
        is_network = False
        
        # Try to convert to int for camera index
        if source_text.isdigit():
            source = int(source_text)
            capture_backend = cv2.CAP_DSHOW
        elif source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://')):
            self.log_message(f"Connecting to network stream: {source}...", "info")
            capture_backend = cv2.CAP_FFMPEG
            is_network = True
            
        try:
            if self.cap:
                self.cap.release()
                self.cap = None

            self.capture_source = source
            self.capture_backend = capture_backend
            self.capture_is_network = is_network
            self.frame_read_failures = 0
            self.cap = self._open_capture(source, capture_backend)
            if not self.cap.isOpened():
                raise Exception("Could not open video source")
                
            self.timer.start(30) # ~33 FPS
            self.is_monitoring = True
            self.btn_start.setText("Stop Monitoring")
            self.btn_start.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px;")
            self.log_message(f"Started monitoring source: {source}", "info")
            
            # 自动启动视频流（如果配置了设备信息）
            self._auto_start_video_stream()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start camera: {str(e)}")
            self.log_message(f"Error starting source: {str(e)}", "error")

    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
            
        self.is_monitoring = False
        self.video_label.setText("Monitoring Stopped")
        self.btn_start.setText("Start Monitoring")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.log_message("Monitoring stopped", "info")

    def update_conf_threshold(self, value):
        self.conf_threshold = value / 100.0
        self.label_conf.setText(f"{self.conf_threshold:.2f}")

    def update_distance_threshold(self, value):
        self.safety_engine.MIN_CYLINDER_DISTANCE = value
        self.log_message(f"Config: Min Cylinder Distance set to {value}m", "info")

    def update_cylinder_dist_filter_window(self, value):
        self.safety_engine.set_cylinder_distance_filter_window(value)
        self.log_message(f"Config: Cylinder distance avg window T = {value} frames", "info")

    def update_consistency_threshold(self, value):
        self.safety_engine.CONSISTENCY_THRESHOLD = value
        self.log_message(f"Config: Consistency Threshold set to {value} frames", "info")

    def update_alert_cooldown(self, value):
        self.safety_engine.alert_cooldown = value
        self.log_message(f"Config: Alert Cooldown set to {value}s", "info")

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.frame_read_failures = 0
                # 0. Pre-processing (Enhancement)
                enhanced_frame = self.enhancer.enhance(frame)
                
                # 1. AI Detection
                # Pass both original and enhanced? Usually detection on enhanced if light is bad.
                # Here we detect on enhanced frame.
                results = self.detector.detect(enhanced_frame, conf_threshold=self.conf_threshold)
                
                # 2. Logic & Safety Checks
                # Get simplified detections list
                detections_list = self.detector.get_detections_list(results)
                alerts = self.safety_engine.check_rules(detections_list, enhanced_frame)
                
                # 3. Handle Alerts
                current_time = datetime.datetime.now().timestamp()
                if alerts:
                    # Update visual alert state
                    self.last_visual_alert_time = current_time
                    # Use the message from the first alert
                    self.current_visual_message = alerts[0].get('message', 'VIOLATION DETECTED')

                    # Add alert to upload queue
                    for alert in alerts:
                        self.uploader.add_alert(alert, enhanced_frame)
                    
                    if alerts:
                        for alert in alerts:
                            self.log_message(f"ALERT: {alert.get('message', 'Unknown Violation')}", "alert")
                            
                            # Play sound for critical/high alerts
                            if alert.get('level') in ['CRITICAL', 'DANGER', 'WARNING']:
                                self.play_alert_sound()
                
                # 4. Visualization
                # Draw boxes
                annotated_frame = results[0].plot()
                
                # Draw visual alerts (Persistence Logic)
                if current_time - self.last_visual_alert_time < self.visual_alert_duration:
                    cv2.putText(annotated_frame, "VIOLATION DETECTED", (50, 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                    # Optional: Show specific message below
                    cv2.putText(annotated_frame, self.current_visual_message, (50, 100), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                                
                    cv2.rectangle(annotated_frame, (0, 0), (annotated_frame.shape[1], annotated_frame.shape[0]), (0, 0, 255), 10)
                
                # 5. Push to video stream (if active)
                if self.video_streamer and self.video_streamer.is_streaming:
                    # 根据覆盖层设置决定推送的帧
                    if self.video_streamer.enable_overlay:
                        # 推送带检测框的标注帧
                        self.video_streamer.push_frame(annotated_frame)
                    else:
                        # 推送原始帧（无检测框）
                        self.video_streamer.push_frame(enhanced_frame)
                
                # 6. Display
                self.display_image(annotated_frame)
            else:
                self.frame_read_failures += 1
                if self.capture_is_network:
                    if self.frame_read_failures >= 3:
                        self.log_message("Video stream stalled, reconnecting...", "error")
                        self._reconnect_capture()
                    return
                self.stop_camera()
                self.log_message("Video stream ended", "info")

    def play_alert_sound(self):
        """Play a system beep sound with cooldown."""
        current_time = datetime.datetime.now().timestamp()
        if current_time - self.last_sound_time > self.sound_cooldown:
            # Frequency 1000Hz, Duration 500ms
            winsound.Beep(1000, 500)
            self.last_sound_time = current_time

    def display_image(self, img):
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to fit label
        self.video_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def log_message(self, message, level="info"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        item_text = f"[{timestamp}] {message}"
        
        if level == "alert":
            item_text = f"⚠️ {item_text}"
            
        self.log_list.addItem(item_text)
        
        # Scroll to bottom
        self.log_list.scrollToBottom()
        
        # Optional: Color coding
        item = self.log_list.item(self.log_list.count() - 1)
        if level == "error":
            item.setForeground(Qt.red)
        elif level == "alert":
            item.setForeground(Qt.darkRed)
            item.setBackground(Qt.yellow)
        
    def start_video_stream(
        self,
        device_id: int,
        stream_id: str,
        media_server_url: str,
        quality: str = "medium"
    ):
        """
        启动视频流推送
        
        Args:
            device_id: 设备ID
            stream_id: 流ID（由后端提供）
            media_server_url: Media Server的RTSP地址
            quality: 流质量
        """
        # 停止现有流（如果存在）
        if self.video_streamer:
            self.stop_video_stream()
        
        try:
            self.video_streamer = VideoStreamer(
                media_server_url=media_server_url,
                device_id=device_id,
                stream_id=stream_id,
                quality=quality
            )
            self.video_streamer.start_stream()
            self.stream_config.update({
                "device_id": device_id,
                "stream_id": stream_id,
                "media_server_url": media_server_url,
                "quality": quality
            })
            self.log_message(f"Video stream started: {stream_id}", "info")
        except Exception as e:
            self.log_message(f"Failed to start video stream: {str(e)}", "error")
            self.video_streamer = None
    
    def stop_video_stream(self):
        """停止视频流推送"""
        if self.video_streamer:
            try:
                self.video_streamer.stop_stream()
                stream_id = self.stream_config.get("stream_id", "unknown")
                self.log_message(f"Video stream stopped: {stream_id}", "info")
            except Exception as e:
                self.log_message(f"Error stopping video stream: {str(e)}", "error")
            finally:
                self.video_streamer = None
                self.stream_config["stream_id"] = None
    
    def toggle_stream_overlay(self, enabled: bool):
        """
        切换视频流的检测覆盖层
        
        Args:
            enabled: 是否启用覆盖层
        """
        if self.video_streamer:
            self.video_streamer.toggle_overlay(enabled)
            self.log_message(f"Stream overlay {'enabled' if enabled else 'disabled'}", "info")
        else:
            self.log_message("No active stream to toggle overlay", "error")
    
    def set_stream_quality(self, quality: str):
        """
        设置视频流质量
        
        Args:
            quality: 流质量（low, medium, high）
        """
        if self.video_streamer:
            self.video_streamer.set_quality(quality)
            self.stream_config["quality"] = quality
            self.log_message(f"Stream quality set to: {quality}", "info")
        else:
            self.log_message("No active stream to set quality", "error")
    
    def get_stream_status(self) -> dict:
        """
        获取视频流状态
        
        Returns:
            流状态字典
        """
        if self.video_streamer:
            return self.video_streamer.get_status()
        else:
            return {
                "is_streaming": False,
                "stream_id": None,
                "quality": None,
                "enable_overlay": False
            }
    
    def _auto_start_video_stream(self):
        """
        自动启动视频流（当监控开始时）
        优先使用从后端自动获取的设备配置，否则从环境变量获取，或等待后端通知
        """
        # 设备ID：优先使用自动获取的配置，否则环境变量
        device_id = None
        if self.device_config:
            device_id = str(self.device_config.device_id)
        if not device_id:
            device_id = os.getenv("DEVICE_ID")
        media_server_url = (
            os.getenv("MEDIA_SERVER_RTMP_URL")
            or os.getenv("MEDIA_SERVER_RTSP_URL", "rtmp://localhost:1935")
        )
        stream_quality = os.getenv("STREAM_QUALITY", "medium")
        
        # 如果配置了设备ID，自动启动流
        if device_id:
            try:
                device_id_int = int(device_id)
                # 生成一个默认的stream_id（实际应该从后端获取）
                import uuid
                stream_id = f"auto_stream_{device_id_int}_{uuid.uuid4().hex[:8]}"
                
                self.start_video_stream(
                    device_id=device_id_int,
                    stream_id=stream_id,
                    media_server_url=media_server_url,
                    quality=stream_quality
                )
                self.log_message(f"Auto-started video stream: {stream_id}", "info")
            except Exception as e:
                self.log_message(f"Failed to auto-start video stream: {str(e)}", "error")
        else:
            # 如果没有配置，等待后端通过心跳响应通知
            # 后端会在设备上线时通过HTTP回调通知Edge Node
            self.log_message("Video stream will start when backend notifies", "info")
    
    def closeEvent(self, event):
        self.stop_camera()
        self.stop_video_stream()
        self.uploader.stop()
        event.accept()
