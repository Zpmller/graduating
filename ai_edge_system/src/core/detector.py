import cv2
from ultralytics import YOLO
import numpy as np
import torch

class Detector:
    def __init__(self, model_path='yolo11m.pt', device='0'):
        """
        Initialize the YOLOv11 detector.
        
        Args:
            model_path (str): Path to the .pt model file. 
                              Defaults to 'yolo11m.pt' (COCO pretrained) for initial testing.
                              For production, use the custom trained model path (e.g., 'models/mining_safety_v1/weights/best.pt').
        """
        print(f"Loading YOLO model from {model_path}...")
        
        # Handle device fallback
        if device == '0' and not torch.cuda.is_available():
            print("Warning: CUDA device '0' requested but not available. Falling back to 'cpu'.")
            device = 'cpu'
            
        self.device = device
        self.model = YOLO(model_path)
        # Class names mapping
        self.names = self.model.names
        print(f"Model loaded. Classes: {self.names}")

    def detect(self, frame, conf_threshold=0.25, classes=None):
        """
        Perform object detection on a single frame.
        
        Args:
            frame (numpy.ndarray): Input image/frame.
            conf_threshold (float): Confidence threshold for detections.
            classes (list): Optional list of class indices to filter.
            
        Returns:
            list: List of detection results (ultralytics.engine.results.Results).
        """
        # verbose=False to reduce console spam
        results = self.model(frame, conf=conf_threshold, classes=classes, device=self.device, verbose=False)
        return results

    def get_detections_list(self, results):
        """
        Convert ultralytics Results object to a simplified list of dicts.
        
        Args:
            results (list): Output from self.detect()
            
        Returns:
            list: List of dicts [{'box': [x1,y1,x2,y2], 'conf': float, 'class_id': int, 'class_name': str}]
        """
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls = int(box.cls[0].item())
                name = self.names[cls]
                
                detections.append({
                    'box': [x1, y1, x2, y2],
                    'conf': conf,
                    'class_id': cls,
                    'class_name': name
                })
        return detections
