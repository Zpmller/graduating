import sys
import os
import unittest
import time
from unittest.mock import MagicMock, patch

# Mock deepface before importing modules that depend on it
sys.modules['deepface'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.safety import SafetyEngine

class TestPPERules(unittest.TestCase):
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

    def test_no_helmet_warning(self):
        """Test that detecting a person without a helmet triggers a WARNING alert."""
        detections = [
            {'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'no-helmet'},
            {'box': [100,100,110,110], 'conf': 0.9, 'class_name': 'person'}
        ]
        
        # Simulate consecutive frames
        alerts = []
        for _ in range(self.engine.CONSISTENCY_THRESHOLD):
            alerts = self.engine.check_rules(detections)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'ppe_violation')
        self.assertEqual(alerts[0]['level'], 'WARNING')
        self.assertIn('without Helmet', alerts[0]['message'])

    def test_alert_cooldown(self):
        """Test that PPE alerts do not spam and respect the cooldown period."""
        self.engine.alert_cooldown = 2.0
        detections = [{'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'no-helmet'}]
        
        # Pre-charge consistency
        self.engine.consistency_counter['no-helmet'] = self.engine.CONSISTENCY_THRESHOLD - 1
        
        # 1. Trigger Alert
        alerts = self.engine.check_rules(detections)
        self.assertEqual(len(alerts), 1)
        first_alert_time = alerts[0]['timestamp']
        
        # 2. Immediate next call (within cooldown) -> No Alert
        alerts = self.engine.check_rules(detections)
        self.assertEqual(len(alerts), 0, "Alert should be suppressed by cooldown")
        
        # 3. Advance time -> Alert again
        with patch('time.time', return_value=first_alert_time + 2.1):
            alerts = self.engine.check_rules(detections)
            self.assertEqual(len(alerts), 1, "Alert should trigger after cooldown")

if __name__ == '__main__':
    unittest.main()
