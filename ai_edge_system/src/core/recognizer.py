import os
import sys

# Set DEEPFACE_HOME before importing DeepFace to control weight download path
# Path: .../ai_edge_system/models
# This ensures weights are downloaded to the project folder, not C:\Users\User\.deepface
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
models_dir = os.path.join(base_dir, 'models')
if not os.path.exists(models_dir):
    os.makedirs(models_dir)
os.environ['DEEPFACE_HOME'] = models_dir

from deepface import DeepFace
import cv2
import numpy as np
import pandas as pd

class FaceRecognizer:
    def __init__(self, db_path=None, model_name='ArcFace'):
        """
        Initialize the Face Recognizer.
        
        Args:
            db_path (str): Path to the folder containing authorized face images.
            model_name (str): Model to use (VGG-Face, Facenet, ArcFace, etc.)
        """
        if db_path is None:
            # Default: ai_edge_system/data/face_db
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, 'data', 'face_db')
            
        self.db_path = db_path
        self.model_name = model_name
        
        # Create db folder if not exists
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            print(f"Created face database directory at {self.db_path}")
            
        print(f"FaceRecognizer initialized with {model_name}. DB: {db_path}")

    def recognize(self, face_img):
        """
        Identify the person in the face image.
        
        Args:
            face_img (numpy.ndarray): Cropped face image (BGR).
            
        Returns:
            dict: {'name': str, 'verified': bool, 'distance': float, 'antispoof': bool}
        """
        if face_img is None or face_img.size == 0:
            return {'name': 'Unknown', 'verified': False, 'distance': 0.0, 'antispoof': False}

        try:
            # 1. Anti-Spoofing Check (Liveness)
            # Simple heuristic: Variance of Laplacian (Blur check) + Colorfulness
            # Real faces usually have more texture/depth (higher variance) than screens/paper.
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Thresholds need tuning based on camera quality. 
            # A low variance indicates a blurry image (often a screen attack or out of focus).
            # Typical threshold ~100-300.
            blur_threshold = 100.0
            
            if variance < blur_threshold:
                # Considered 'spoof' or too blurry to be reliable
                print(f"Liveness Check Failed: Variance {variance:.2f} < {blur_threshold}")
                return {'name': 'Spoof/Blur', 'verified': False, 'distance': 0.0, 'antispoof': False}
                
            is_real = True 
            
            # 2. Face Recognition (Search in DB)
            # Check if DB is empty or doesn't have enough images (DeepFace might crash on empty folders)
            if not os.listdir(self.db_path):
                return {'name': 'Unknown', 'verified': False, 'distance': 0.0, 'antispoof': is_real}

            # DeepFace.find returns a list of DataFrames
            dfs = DeepFace.find(img_path=face_img, 
                                db_path=self.db_path, 
                                model_name=self.model_name, 
                                enforce_detection=False, 
                                silent=True)
            
            if len(dfs) > 0 and not dfs[0].empty:
                # Get the first match (most similar)
                match = dfs[0].iloc[0]
                identity_path = match['identity']
                # Extract name from filename (e.g., "data/face_db/UserA/img1.jpg" -> "UserA")
                # Assuming structure: db_path/PersonName/image.jpg OR db_path/PersonName_1.jpg
                
                filename = os.path.basename(identity_path)
                name = os.path.splitext(filename)[0]
                
                # If using subfolders, get parent folder name
                parent_dir = os.path.basename(os.path.dirname(identity_path))
                if parent_dir != os.path.basename(self.db_path):
                    name = parent_dir
                
                distance = match.get('distance', 0.0) # Varies by model (lower is better for Cosine/Euclidean)
                
                return {
                    'name': name,
                    'verified': True,
                    'distance': distance,
                    'antispoof': is_real
                }
            else:
                return {
                    'name': 'Unknown',
                    'verified': False,
                    'distance': 0.0,
                    'antispoof': is_real
                }

        except Exception as e:
            print(f"Recognition Error: {e}")
            return {'name': 'Error', 'verified': False, 'distance': 0.0, 'antispoof': False}

    def register_face(self, face_img, name):
        """
        Save a face image to the database.
        """
        try:
            user_dir = os.path.join(self.db_path, name)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            
            # Save with timestamp or counter
            count = len(os.listdir(user_dir))
            filename = f"{name}_{count+1}.jpg"
            path = os.path.join(user_dir, filename)
            cv2.imwrite(path, face_img)
            
            # Clear representation cache to update DB
            pkl_path = os.path.join(self.db_path, f"representations_{self.model_name}.pkl")
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
                
            return True, path
        except Exception as e:
            print(f"Registration Error: {e}")
            return False, str(e)
