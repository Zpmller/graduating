import numpy as np
import cv2
import os
import yaml

class Camera:
    def __init__(self, calibration_file=None):
        """
        Initialize Camera object.
        Args:
            calibration_file (str): Path to .npz or .yaml file containing camera intrinsics.
        """
        self.camera_matrix = None
        self.dist_coeffs = None
        self.focal_length_x = None
        self.focal_length_y = None
        self.cx = None
        self.cy = None
        
        if calibration_file and os.path.exists(calibration_file):
            self.load_calibration(calibration_file)
        else:
            self.set_default_intrinsics()

    def set_default_intrinsics(self, width=1920, height=1080):
        """
        Set default intrinsics approximating a standard webcam.
        """
        # Approx FOV ~ 60 degrees
        # f = w / (2 * tan(fov/2))
        f = width # Rough approximation often width is close to focal length in pixels for 50-60 deg lens
        self.focal_length_x = f
        self.focal_length_y = f
        self.cx = width / 2
        self.cy = height / 2
        
        self.camera_matrix = np.array([
            [f, 0, self.cx],
            [0, f, self.cy],
            [0, 0, 1]
        ], dtype=np.float32)
        self.dist_coeffs = np.zeros(5)
        print(f"Camera initialized with default intrinsics (F={f})")

    def load_calibration(self, path):
        try:
            if path.lower().endswith(('.yaml', '.yml')):
                self._load_yaml(path)
            else:
                self._load_npz(path)

            # Update intrinsic parameters from loaded matrix
            self.focal_length_x = self.camera_matrix[0, 0]
            self.focal_length_y = self.camera_matrix[1, 1]
            self.cx = self.camera_matrix[0, 2]
            self.cy = self.camera_matrix[1, 2]
            
            print(f"Camera calibration loaded from {path}")
        except Exception as e:
            print(f"Error loading calibration: {e}")
            self.set_default_intrinsics()

    def _load_npz(self, path):
        with np.load(path) as data:
            self.camera_matrix = data['mtx']
            self.dist_coeffs = data['dist']

    def _load_yaml(self, path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
            # Expecting 'camera_matrix' and 'dist_coeffs' keys
            self.camera_matrix = np.array(data['camera_matrix'], dtype=np.float32)
            self.dist_coeffs = np.array(data['dist_coeffs'], dtype=np.float32)

    def get_calibration_data(self):
        return self.camera_matrix, self.dist_coeffs
