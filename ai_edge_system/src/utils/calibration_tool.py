
import sys
import os
import cv2
import numpy as np
import yaml
import argparse
import glob
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QTextEdit, 
                             QSpinBox, QDoubleSpinBox, QGroupBox, QProgressBar, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Add project root to sys.path to allow imports if running standalone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.camera import Camera

def perform_calibration(images, pattern_size, square_size, log_cb=None, progress_cb=None):
    if log_cb: log_cb(f"Starting calibration with {len(images)} images...")
    
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size

    objpoints = [] 
    imgpoints = [] 

    valid_images = 0
    gray = None
    
    total_imgs = len(images)
    
    for i, fname in enumerate(images):
        img = cv2.imread(fname)
        if img is None:
            if log_cb: log_cb(f"Failed to read {fname}")
            continue
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

        if ret:
            objpoints.append(objp)
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), 
                                        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            imgpoints.append(corners2)
            valid_images += 1
            if log_cb: log_cb(f"Found corners in {os.path.basename(fname)}")
        else:
            if log_cb: log_cb(f"Corners NOT found in {os.path.basename(fname)}")
            
        if progress_cb:
            progress_cb(int((i + 1) / total_imgs * 50))

    if valid_images == 0:
        if log_cb: log_cb("No valid images found for calibration.")
        return None, None, None

    if log_cb: log_cb(f"Calibrating with {valid_images} valid images...")
    
    h, w = gray.shape[:2]
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, (w, h), None, None)

    mean_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        mean_error += error
    total_error = mean_error / len(objpoints)
    
    if progress_cb: progress_cb(100)
    
    return mtx, dist, total_error

class CalibrationWorker(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object, object, float) # matrix, dist, error

    def __init__(self, images, pattern_size, square_size):
        super().__init__()
        self.images = images
        self.pattern_size = pattern_size # (rows, cols)
        self.square_size = square_size

    def run(self):
        mtx, dist, error = perform_calibration(
            self.images, self.pattern_size, self.square_size,
            self.log_signal.emit, self.progress_signal.emit
        )
        if mtx is not None:
            self.result_signal.emit(mtx, dist, error)

class CalibrationTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Calibration Tool")
        self.resize(800, 600)
        self.initUI()
        self.camera_matrix = None
        self.dist_coeffs = None

    def initUI(self):
        layout = QVBoxLayout()

        # --- Section 1: Load Existing ---
        group_load = QGroupBox("1. Load Existing Calibration")
        layout_load = QHBoxLayout()
        self.btn_load_yaml = QPushButton("Load YAML File")
        self.btn_load_yaml.clicked.connect(self.load_yaml)
        layout_load.addWidget(self.btn_load_yaml)
        group_load.setLayout(layout_load)
        layout.addWidget(group_load)

        # --- Section 2: Calibrate New ---
        group_calib = QGroupBox("2. Perform New Calibration")
        layout_calib = QVBoxLayout()
        
        # Settings
        layout_settings = QHBoxLayout()
        layout_settings.addWidget(QLabel("Rows (Corners):"))
        self.spin_rows = QSpinBox()
        self.spin_rows.setValue(9)
        layout_settings.addWidget(self.spin_rows)
        
        layout_settings.addWidget(QLabel("Cols (Corners):"))
        self.spin_cols = QSpinBox()
        self.spin_cols.setValue(6)
        layout_settings.addWidget(self.spin_cols)
        
        layout_settings.addWidget(QLabel("Square Size (mm):"))
        self.spin_size = QDoubleSpinBox()
        self.spin_size.setValue(25.0)
        layout_settings.addWidget(self.spin_size)
        layout_calib.addLayout(layout_settings)

        # Buttons
        layout_btns = QHBoxLayout()
        self.btn_select_imgs = QPushButton("Select Images")
        self.btn_select_imgs.clicked.connect(self.select_images)
        self.btn_run_calib = QPushButton("Run Calibration")
        self.btn_run_calib.clicked.connect(self.run_calibration)
        self.btn_run_calib.setEnabled(False)
        
        layout_btns.addWidget(self.btn_select_imgs)
        layout_btns.addWidget(self.btn_run_calib)
        layout_calib.addLayout(layout_btns)
        
        self.lbl_images = QLabel("No images selected")
        layout_calib.addWidget(self.lbl_images)
        
        self.progress = QProgressBar()
        layout_calib.addWidget(self.progress)
        
        group_calib.setLayout(layout_calib)
        layout.addWidget(group_calib)

        # --- Section 3: Results & Save ---
        group_results = QGroupBox("3. Results & Log")
        layout_results = QVBoxLayout()
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        layout_results.addWidget(self.text_log)
        
        self.btn_save = QPushButton("Save Calibration to YAML")
        self.btn_save.clicked.connect(self.save_yaml)
        self.btn_save.setEnabled(False)
        layout_results.addWidget(self.btn_save)
        
        group_results.setLayout(layout_results)
        layout.addWidget(group_results)

        self.setLayout(layout)
        self.image_paths = []

    def log(self, message):
        self.text_log.append(message)

    def load_yaml(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open YAML', '.', "YAML Files (*.yaml *.yml)")
        if fname:
            try:
                cam = Camera(fname)
                self.camera_matrix = cam.camera_matrix
                self.dist_coeffs = cam.dist_coeffs
                self.log(f"Loaded calibration from {fname}")
                self.log(f"Camera Matrix:\n{self.camera_matrix}")
                self.log(f"Dist Coefficients:\n{self.dist_coeffs}")
                self.btn_save.setEnabled(True)
            except Exception as e:
                self.log(f"Error loading YAML: {e}")

    def select_images(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Select Images', '.', "Image Files (*.jpg *.png *.bmp)")
        if fnames:
            self.image_paths = fnames
            self.lbl_images.setText(f"{len(fnames)} images selected")
            self.btn_run_calib.setEnabled(True)
            self.log(f"Selected {len(fnames)} images.")

    def run_calibration(self):
        rows = self.spin_rows.value()
        cols = self.spin_cols.value()
        size = self.spin_size.value()
        
        self.worker = CalibrationWorker(self.image_paths, (rows, cols), size)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.result_signal.connect(self.on_calibration_finished)
        self.worker.start()
        self.btn_run_calib.setEnabled(False)

    def on_calibration_finished(self, mtx, dist, error):
        self.camera_matrix = mtx
        self.dist_coeffs = dist
        self.log(f"\nCalibration Successful!")
        self.log(f"Re-projection Error: {error:.4f}")
        self.log(f"Camera Matrix:\n{mtx}")
        self.log(f"Dist Coefficients:\n{dist}")
        self.btn_save.setEnabled(True)
        self.btn_run_calib.setEnabled(True)

    def save_yaml(self):
        if self.camera_matrix is None:
            return
            
        fname, _ = QFileDialog.getSaveFileName(self, 'Save YAML', 'camera_calibration.yaml', "YAML Files (*.yaml)")
        if fname:
            data = {
                'camera_matrix': self.camera_matrix.tolist(),
                'dist_coeffs': self.dist_coeffs.tolist()
            }
            try:
                with open(fname, 'w') as f:
                    yaml.dump(data, f)
                self.log(f"Saved to {fname}")
            except Exception as e:
                self.log(f"Error saving: {e}")

    def sync_from_cloud(self):
        url = self.input_url.text()
        try:
            device_id = int(self.input_id.text())
        except ValueError:
            self.log("Error: Device ID must be an integer")
            return
        token = self.input_token.text()
        
        self.sync_worker = SyncWorker(url, device_id, token)
        self.sync_worker.log_signal.connect(self.log)
        self.sync_worker.result_signal.connect(self.on_sync_finished)
        self.sync_worker.start()
        self.btn_sync.setEnabled(False)

    def on_sync_finished(self, yaml_content):
        self.btn_sync.setEnabled(True)
        try:
            # Parse YAML to verify it's valid
            data = yaml.safe_load(yaml_content)
            if 'camera_matrix' not in data or 'dist_coeffs' not in data:
                self.log("Error: Invalid calibration format received")
                return
                
            # Convert lists back to numpy arrays
            self.camera_matrix = np.array(data['camera_matrix'])
            self.dist_coeffs = np.array(data['dist_coeffs'])
            
            self.log("Successfully loaded calibration from Cloud.")
            self.log(f"Camera Matrix:\n{self.camera_matrix}")
            self.log(f"Dist Coefficients:\n{self.dist_coeffs}")
            self.btn_save.setEnabled(True)
            
        except Exception as e:
            self.log(f"Error parsing received YAML: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--images_dir', type=str)
    parser.add_argument('--output', type=str)
    parser.add_argument('--rows', type=int, default=9)
    parser.add_argument('--cols', type=int, default=6)
    parser.add_argument('--size', type=float, default=25.0)
    args, _ = parser.parse_known_args()

    if args.images_dir and args.output:
        # Headless mode
        image_files = glob.glob(os.path.join(args.images_dir, '*'))
        image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        
        mtx, dist, error = perform_calibration(
            image_files, (args.rows, args.cols), args.size,
            log_cb=print
        )
        
        if mtx is not None:
            data = {
                'camera_matrix': mtx.tolist(),
                'dist_coeffs': dist.tolist()
            }
            with open(args.output, 'w') as f:
                yaml.dump(data, f)
            print(f"Calibration saved to {args.output}")
            print(f"Re-projection Error: {error:.4f}")
    else:
        app = QApplication(sys.argv)
        ex = CalibrationTool()
        ex.show()
        sys.exit(app.exec_())
