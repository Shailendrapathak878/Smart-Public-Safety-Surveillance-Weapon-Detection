import pytest
from core.threat_engine import ThreatEngine
from core.detection_types import Detection, BoundingBox

def test_threat_engine_no_overlap():
    engine = ThreatEngine(iow_threshold=0.5)
    
    weapon = Detection(class_id=0, class_name="gun", confidence=0.9, bbox=BoundingBox(0, 0, 10, 10))
    human = Detection(class_id=0, class_name="person", confidence=0.9, bbox=BoundingBox(20, 20, 100, 100))
    
    threats = engine.validate_threats([weapon], [human])
    assert len(threats) == 0

def test_threat_engine_full_overlap():
    engine = ThreatEngine(iow_threshold=0.5)
    
    # Weapon is completely inside human
    weapon = Detection(class_id=0, class_name="gun", confidence=0.9, bbox=BoundingBox(50, 50, 60, 60))
    human = Detection(class_id=0, class_name="person", confidence=0.9, bbox=BoundingBox(20, 20, 100, 100))
    
    threats = engine.validate_threats([weapon], [human])
    assert len(threats) == 1
    assert threats[0].iow == 1.0

def test_threat_engine_partial_overlap_below_threshold():
    engine = ThreatEngine(iow_threshold=0.5)
    
    # Weapon area = 100. Overlap is 40. IoW = 0.4.
    weapon = Detection(class_id=1, class_name="knife", confidence=0.8, bbox=BoundingBox(10, 10, 20, 20))
    human = Detection(class_id=0, class_name="person", confidence=0.9, bbox=BoundingBox(16, 10, 30, 30))
    
    threats = engine.validate_threats([weapon], [human])
    assert len(threats) == 0

def test_threat_engine_multiple_humans():
    engine = ThreatEngine(iow_threshold=0.5)
    
    # Weapon is in human2
    weapon = Detection(class_id=0, class_name="gun", confidence=0.9, bbox=BoundingBox(50, 50, 60, 60))
    human1 = Detection(class_id=0, class_name="person", confidence=0.9, bbox=BoundingBox(0, 0, 10, 10))
    human2 = Detection(class_id=0, class_name="person", confidence=0.9, bbox=BoundingBox(20, 20, 100, 100))
    
    threats = engine.validate_threats([weapon], [human1, human2])
    assert len(threats) == 1
    assert threats[0].human == human2
