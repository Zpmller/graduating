import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock deepface before importing modules that depend on it
sys.modules['deepface'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.safety import SafetyEngine

class TestDistanceRules(unittest.TestCase):
    def setUp(self):
        self.patcher_camera = patch('src.logic.safety.Camera')
        self.patcher_dist = patch('src.logic.safety.DistanceEstimator')
        self.patcher_face = patch('src.logic.safety.FaceRecognizer')
        
        self.MockCamera = self.patcher_camera.start()
        self.MockDist = self.patcher_dist.start()
        self.MockFace = self.patcher_face.start()
        
        self.engine = SafetyEngine(db_path='dummy_path')

    def tearDown(self):
        self.patcher_camera.stop()
        self.patcher_dist.stop()
        self.patcher_face.stop()

    def test_cylinder_too_close(self):
        """Test violation when gas cylinders are too close."""
        # Mock distance to be unsafe (2.0m < 5.0m limit)
        self.engine.distance_estimator.calculate_distance.return_value = 2.0
        
        detections = [
            {'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'gas_cylinder'},
            {'box': [100,100,110,110], 'conf': 0.9, 'class_name': 'gas_cylinder'}
        ]
        
        alerts = self.engine.check_rules(detections)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'distance_violation')
        self.assertEqual(alerts[0]['level'], 'DANGER')

    def test_cylinder_safe(self):
        """Test no violation when gas cylinders are at a safe distance."""
        # Mock distance to be safe (6.0m > 5.0m limit)
        self.engine.distance_estimator.calculate_distance.return_value = 6.0
        
        detections = [
            {'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'gas_cylinder'},
            {'box': [100,100,110,110], 'conf': 0.9, 'class_name': 'gas_cylinder'}
        ]
        
        alerts = self.engine.check_rules(detections)
        self.assertEqual(len(alerts), 0)

    def test_cylinder_edge_cases(self):
        """Test single cylinder or calculation failure."""
        # Case 1: Single cylinder
        detections = [{'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'gas_cylinder'}]
        alerts = self.engine.check_rules(detections)
        self.assertEqual(len(alerts), 0)
        
        # Case 2: Distance calculation failure (None)
        detections_2 = [
            {'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'gas_cylinder'},
            {'box': [100,100,110,110], 'conf': 0.9, 'class_name': 'gas_cylinder'}
        ]
        self.engine.distance_estimator.calculate_distance.return_value = None
        
        alerts = self.engine.check_rules(detections_2)
        self.assertEqual(len(alerts), 0)

if __name__ == '__main__':
    unittest.main()
