import numpy as np
import math

class DistanceEstimator:
    def __init__(self, camera_obj):
        """
        Initialize Distance Estimator.
        Args:
            camera_obj (Camera): Instance of utils.camera.Camera
        """
        self.camera = camera_obj
        
        # Real-world heights in centimeters
        # Source: Standard 40L cylinder specs
        self.REAL_HEIGHTS = {
            'oxygen': 145.0,     # ~1.45m
            'acetylene': 105.0,  # ~1.05m
            'gas_cylinder': 125.0, # Average fallback
            'person': 170.0,     # ~1.70m
            'helmet': 25.0       # ~25cm
        }

    def estimate_depth(self, bbox, class_name):
        """
        Estimate Z-distance (depth) from camera using Monocular Vision.
        D = (F * Real_H) / Pixel_H
        
        Args:
            bbox: [x1, y1, x2, y2]
            class_name: str
            
        Returns:
            float: Depth in meters, or None if invalid.
        """
        if class_name not in self.REAL_HEIGHTS:
            return None
            
        x1, y1, x2, y2 = bbox
        pixel_height = y2 - y1
        
        if pixel_height <= 0:
            return None
            
        real_height_cm = self.REAL_HEIGHTS[class_name]
        focal_length = self.camera.focal_length_y # Use Y focal length for height
        
        # Z (cm) = (f * H_real) / h_pixel
        depth_cm = (focal_length * real_height_cm) / pixel_height
        return depth_cm / 100.0 # Convert to meters

    def get_3d_coordinates(self, bbox, depth_m):
        """
        Convert pixel coordinates to 3D Camera Coordinates (X, Y, Z).
        
        Args:
            bbox: [x1, y1, x2, y2]
            depth_m: Depth in meters (Z)
            
        Returns:
            tuple: (X, Y, Z) in meters.
        """
        if depth_m is None:
            return None
            
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2 # Or use y2 for ground point? Center is better for general object position
        
        # X = (u - cx) * Z / fx
        X = (center_x - self.camera.cx) * depth_m / self.camera.focal_length_x
        
        # Y = (v - cy) * Z / fy
        Y = (center_y - self.camera.cy) * depth_m / self.camera.focal_length_y
        
        return (X, Y, depth_m)

    def calculate_distance(self, obj1_info, obj2_info):
        """
        Calculate Euclidean distance between two detected objects.
        
        Args:
            obj1_info: dict {'box': [...], 'class_name': ...}
            obj2_info: dict {'box': [...], 'class_name': ...}
            
        Returns:
            float: Distance in meters.
        """
        # 1. Estimate depth for both
        depth1 = self.estimate_depth(obj1_info['box'], obj1_info['class_name'])
        depth2 = self.estimate_depth(obj2_info['box'], obj2_info['class_name'])
        
        if depth1 is None or depth2 is None:
            return None
            
        # 2. Get 3D coords
        p1 = self.get_3d_coordinates(obj1_info['box'], depth1)
        p2 = self.get_3d_coordinates(obj2_info['box'], depth2)
        
        # 3. Euclidean Distance
        dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
        return dist
