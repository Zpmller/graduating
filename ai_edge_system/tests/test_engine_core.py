import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock deepface before importing modules that depend on it
sys.modules['deepface'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.safety import SafetyEngine

class TestSafetyEngineCore(unittest.TestCase):
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

    def test_consistency_reset(self):
        """Test that consistency counters reset when the hazard disappears."""
        detections = [{'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'fire'}]
        empty = []
        
        # Frame 1: Fire (1/3)
        self.engine.check_rules(detections)
        self.assertEqual(self.engine.consistency_counter['fire'], 1)
        
        # Frame 2: Fire (2/3)
        self.engine.check_rules(detections)
        self.assertEqual(self.engine.consistency_counter['fire'], 2)
        
        # Frame 3: Empty -> Reset to 0
        self.engine.check_rules(empty)
        self.assertEqual(self.engine.consistency_counter['fire'], 0)
        
        # Frame 4: Fire (1/3)
        self.engine.check_rules(detections)
        self.assertEqual(self.engine.consistency_counter['fire'], 1)

    def test_mixed_violations(self):
        """Test multiple types of violations occurring in the same frame."""
        detections = [
            {'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'fire'},
            {'box': [20,20,30,30], 'conf': 0.9, 'class_name': 'smoke'},
            {'box': [40,40,50,50], 'conf': 0.9, 'class_name': 'no-helmet'}
        ]
        
        # Pre-charge counters
        self.engine.consistency_counter['fire'] = self.engine.CONSISTENCY_THRESHOLD - 1
        self.engine.consistency_counter['smoke'] = self.engine.CONSISTENCY_THRESHOLD - 1
        self.engine.consistency_counter['no-helmet'] = self.engine.CONSISTENCY_THRESHOLD - 1
        
        alerts = self.engine.check_rules(detections)
        
        alert_types = [a['type'] for a in alerts]
        self.assertIn('fire_violation', alert_types)
        self.assertIn('smoke_violation', alert_types)
        self.assertIn('ppe_violation', alert_types)
        self.assertEqual(len(alerts), 3)

    def test_ignored_classes(self):
        """
        Test that classes present in data.yaml but not in safety rules 
        (e.g., 'helmet', 'person') do not trigger false alerts.
        """
        detections = [
            {'box': [0,0,10,10], 'conf': 0.9, 'class_name': 'helmet'},
            {'box': [20,20,30,30], 'conf': 0.9, 'class_name': 'person'}
        ]
        
        # Should not trigger any alerts
        alerts = self.engine.check_rules(detections)
        self.assertEqual(len(alerts), 0)

if __name__ == '__main__':
    unittest.main()
