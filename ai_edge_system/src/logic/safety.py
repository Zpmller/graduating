import time
import os
import cv2
import numpy as np
from collections import deque

# Adjust imports based on your project structure and execution point
try:
    from src.utils.camera import Camera
    from src.logic.distance import DistanceEstimator
    from src.core.recognizer import FaceRecognizer
except ImportError:
    # Fallback for relative imports if running from src/logic/
    from ..utils.camera import Camera
    from .distance import DistanceEstimator
    from ..core.recognizer import FaceRecognizer

class SafetyEngine:
    def __init__(self, db_path=None):
        """
        Initialize the Safety Rule Engine with advanced logic.
        """
        if db_path is None:
            # Default: ai_edge_system/data/face_db
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, 'data', 'face_db')

        # 1. Initialize Sub-modules
        self.camera = Camera() # Load default or calibration file if available
        self.distance_estimator = DistanceEstimator(self.camera)
        self.face_recognizer = FaceRecognizer(db_path=db_path)
        
        # 2. Thresholds
        self.MIN_CYLINDER_DISTANCE = 5.0 # meters
        self.MIN_IOU_HELMET = 0.3
        # Bar(D)_t = (1/T) * sum_{k=0}^{T-1} D_{t-k}  — 抑制检测抖动引起的距离波动
        self.CYLINDER_DISTANCE_FILTER_WINDOW = 5  # T
        self._cylinder_dist_history = deque(maxlen=self.CYLINDER_DISTANCE_FILTER_WINDOW)
        
        # 3. State tracking
        self.last_alert_time = 0
        self.alert_cooldown = 2.0
        
        # Multi-frame consistency tracking
        # {class_name: consecutive_frames_count}
        self.consistency_counter = {
            'fire': 0,
            'smoke': 0,
            'no-helmet': 0
        }
        self.CONSISTENCY_THRESHOLD = 3 # Alert only if detected in 3 consecutive frames
        
        # Face Recognition Throttling
        self.known_faces = {} # {track_id: name} - simple caching if tracking is enabled
        self.last_face_check = 0
        self.face_check_interval = 1.0 # Check faces every 1 second
        
        print("SafetyEngine Initialized (Phase 3)")

    def set_cylinder_distance_filter_window(self, T):
        """Resize temporal averaging window T for cylinder distance (min 1). Preserves recent samples when possible."""
        T = max(1, int(T))
        if T == self.CYLINDER_DISTANCE_FILTER_WINDOW:
            return
        self.CYLINDER_DISTANCE_FILTER_WINDOW = T
        prev = list(self._cylinder_dist_history)
        self._cylinder_dist_history = deque(prev[-T:], maxlen=T)

    def check_rules(self, detections, frame_img=None):
        """
        Evaluate safety rules based on detections.
        
        Args:
            detections: List of dicts [{'box': [x1,y1,x2,y2], 'conf': float, 'class_name': str, 'track_id': int (optional)}]
            frame_img: Original video frame (numpy array) - required for Face Rec & Distance (if needed for better prec)
            
        Returns:
            list: A list of violation events/alerts.
        """
        alerts = []
        current_time = time.time()
        
        # Categorize detections
        cylinders = []
        no_helmets = []
        fire_hazards = []
        smoke_hazards = []
        faces = []
        
        for det in detections:
            name = det['class_name']
            if name == 'gas_cylinder':
                cylinders.append(det)
            elif name == 'no-helmet':
                no_helmets.append(det)
            elif name in ['fire', 'sparks']:
                fire_hazards.append(det)
            elif name == 'smoke':
                smoke_hazards.append(det)
            elif name == 'face':
                faces.append(det)

        # --- Rule 1: Fire/Spark Detection (CRITICAL) ---
        if fire_hazards:
            self.consistency_counter['fire'] += 1
        else:
            self.consistency_counter['fire'] = 0

        if self.consistency_counter['fire'] >= self.CONSISTENCY_THRESHOLD:
            alerts.append({
                "type": "fire_violation",
                "message": f"FIRE/SPARK DETECTED! (Count: {len(fire_hazards)})",
                "timestamp": current_time,
                "level": "CRITICAL"
            })
            
        # --- Rule 1.1: Smoke Detection (WARNING) ---
        if smoke_hazards:
            self.consistency_counter['smoke'] += 1
        else:
            self.consistency_counter['smoke'] = 0

        if self.consistency_counter['smoke'] >= self.CONSISTENCY_THRESHOLD:
            alerts.append({
                "type": "smoke_violation",
                "message": f"SMOKE DETECTED! (Count: {len(smoke_hazards)})",
                "timestamp": current_time,
                "level": "WARNING"
            })

        # --- Rule 2: PPE Check (Direct no-helmet detection) ---
        if no_helmets:
            self.consistency_counter['no-helmet'] += 1
        else:
            self.consistency_counter['no-helmet'] = 0

        if self.consistency_counter['no-helmet'] >= self.CONSISTENCY_THRESHOLD:
            if current_time - self.last_alert_time > self.alert_cooldown:
                alerts.append({
                    "type": "ppe_violation",
                    "message": f"Person detected without Helmet! (Count: {len(no_helmets)})",
                    "timestamp": current_time,
                    "level": "WARNING"
                })
                self.last_alert_time = current_time

        # --- Rule 3: Cylinder Distance Check (temporal average Bar(D)_t over T frames) ---
        if len(cylinders) >= 2:
            pairwise = []
            for i in range(len(cylinders)):
                for j in range(i + 1, len(cylinders)):
                    d = self.distance_estimator.calculate_distance(cylinders[i], cylinders[j])
                    if d is not None:
                        pairwise.append(d)
            if pairwise:
                D_t = min(pairwise)
                self._cylinder_dist_history.append(D_t)
            else:
                self._cylinder_dist_history.clear()
        else:
            self._cylinder_dist_history.clear()

        if self._cylinder_dist_history:
            n = len(self._cylinder_dist_history)
            bar_D = sum(self._cylinder_dist_history) / n
            if bar_D < self.MIN_CYLINDER_DISTANCE:
                alerts.append({
                    "type": "distance_violation",
                    "message": (
                        f"Cylinders too close! Filtered dist: {bar_D:.2f}m "
                        f"(avg {n}/{self.CYLINDER_DISTANCE_FILTER_WINDOW} frames) (< {self.MIN_CYLINDER_DISTANCE}m)"
                    ),
                    "timestamp": current_time,
                    "level": "DANGER",
                    "filtered_distance_m": bar_D,
                    "distance_samples": n,
                })

        # --- Rule 4: Access Control (Face Recognition) ---
        if faces and frame_img is not None:
            # Throttle face checks
            if current_time - self.last_face_check > self.face_check_interval:
                self.last_face_check = current_time
                
                for face in faces:
                    # Get crop
                    x1, y1, x2, y2 = map(int, face['box'])
                    # Clip to image bounds
                    h, w = frame_img.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    if x2 > x1 and y2 > y1:
                        face_crop = frame_img[y1:y2, x1:x2]
                        
                        # Recognize
                        result = self.face_recognizer.recognize(face_crop)
                        
                        if result['verified']:
                            # Authorized
                            pass # Or log entry
                        else:
                            alerts.append({
                                "type": "access_control",
                                "message": f"Unknown/Unauthorized Person Detected!",
                                "timestamp": current_time,
                                "level": "WARNING"
                            })

        return alerts