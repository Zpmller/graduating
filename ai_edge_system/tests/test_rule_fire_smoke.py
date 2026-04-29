import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock deepface before importing modules that depend on it
sys.modules['deepface'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.safety import SafetyEngine

class TestFireSmokeRules(unittest.TestCase):
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

    def test_fire_critical(self):
        """Test that fire detection triggers a CRITICAL alert after consistency check."""
        detections = [{'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'fire'}]
        
        # Simulate consecutive frames to trigger consistency check
        alerts = []
        for _ in range(self.engine.CONSISTENCY_THRESHOLD):
            alerts = self.engine.check_rules(detections)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'fire_violation')
        self.assertEqual(alerts[0]['level'], 'CRITICAL')

    def test_smoke_warning(self):
        """Test that smoke detection triggers a WARNING alert after consistency check."""
        detections = [{'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'smoke'}]
        
        # Simulate consecutive frames
        alerts = []
        for _ in range(self.engine.CONSISTENCY_THRESHOLD):
            alerts = self.engine.check_rules(detections)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'smoke_violation')
        self.assertEqual(alerts[0]['level'], 'WARNING')
        self.assertIn('SMOKE', alerts[0]['message'])

    def test_spark_detection(self):
        """Test that spark detection triggers a fire violation (treated as fire hazard)."""
        detections = [{'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'sparks'}]
        
        # Simulate consecutive frames
        alerts = []
        for _ in range(self.engine.CONSISTENCY_THRESHOLD):
            alerts = self.engine.check_rules(detections)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'fire_violation')
        self.assertIn('SPARK', alerts[0]['message']) # Assuming logic keeps 'sparks' distinct or grouped in message if specific
        # Checking implementation: "FIRE/SPARK DETECTED!" is the message
        self.assertIn('FIRE/SPARK', alerts[0]['message'])

if __name__ == '__main__':
    unittest.main()
