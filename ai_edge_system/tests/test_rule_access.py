import sys
import os
import unittest
import time
import numpy as np
from unittest.mock import MagicMock, patch

# Mock deepface before importing modules that depend on it
sys.modules['deepface'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.safety import SafetyEngine

class TestAccessRules(unittest.TestCase):
    def setUp(self):
        self.patcher_camera = patch('src.logic.safety.Camera')
        self.patcher_dist = patch('src.logic.safety.DistanceEstimator')
        self.patcher_face = patch('src.logic.safety.FaceRecognizer')
        
        self.patcher_camera.start()
        self.patcher_dist.start()
        self.patcher_face.start()
        
        self.engine = SafetyEngine(db_path='dummy_path')

    def tearDown(self):
        self.patcher_camera.stop()
        self.patcher_dist.stop()
        self.patcher_face.stop()

    def test_face_auth_and_throttling(self):
        """Test face recognition throttling and unauthorized detection."""
        self.engine.face_check_interval = 1.0
        face_det = [{'box': [0,0,50,50], 'conf': 0.9, 'class_name': 'face'}]
        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Mock Unauthorized
        self.engine.face_recognizer.recognize.return_value = {'verified': False}
        
        start_time = time.time()
        with patch('time.time', return_value=start_time):
            # 1. Should check and alert
            alerts = self.engine.check_rules(face_det, frame_img=dummy_frame)
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]['type'], 'access_control')
            self.engine.face_recognizer.recognize.assert_called_once()
        
        self.engine.face_recognizer.recognize.reset_mock()
        
        with patch('time.time', return_value=start_time + 0.5):
            # 2. Within interval -> Skip check
            alerts = self.engine.check_rules(face_det, frame_img=dummy_frame)
            self.assertEqual(len(alerts), 0)
            self.engine.face_recognizer.recognize.assert_not_called()
            
        with patch('time.time', return_value=start_time + 1.1):
            # 3. After interval -> Check again
            alerts = self.engine.check_rules(face_det, frame_img=dummy_frame)
            self.assertEqual(len(alerts), 1)
            self.engine.face_recognizer.recognize.assert_called_once()

    def test_face_boundary_safe(self):
        """Test that face coordinates outside image boundaries are handled safely."""
        face_det = [{'box': [-10, -10, 110, 110], 'conf': 0.9, 'class_name': 'face'}]
        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        self.engine.face_recognizer.recognize.return_value = {'verified': True}
        
        try:
            self.engine.check_rules(face_det, frame_img=dummy_frame)
        except Exception as e:
            self.fail(f"check_rules crashed on boundary clipping: {e}")
            
        # Verify valid crop passed to recognizer
        args, _ = self.engine.face_recognizer.recognize.call_args
        crop = args[0]
        self.assertEqual(crop.shape, (100, 100, 3))

if __name__ == '__main__':
    unittest.main()
