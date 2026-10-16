from typing import List
from core.detection_types import Detection, BoundingBox, ValidatedThreat
from config import settings

class ThreatEngine:
    """
    Evaluates weapon detections against human detections.
    If a weapon overlaps with a human above the IoW threshold, it's a ValidatedThreat.
    """
    def __init__(self, iow_threshold: float = None):
        self.iow_threshold = iow_threshold if iow_threshold is not None else settings.IOW_THRESHOLD

    def calculate_intersection_area(self, boxA: BoundingBox, boxB: BoundingBox) -> int:
        xA = max(boxA.x1, boxB.x1)
        yA = max(boxA.y1, boxB.y1)
        xB = min(boxA.x2, boxB.x2)
        yB = min(boxA.y2, boxB.y2)

        interArea = max(0, xB - xA) * max(0, yB - yA)
        return interArea

    def validate_threats(self, weapons: List[Detection], humans: List[Detection]) -> List[ValidatedThreat]:
        validated_threats = []

        for weapon in weapons:
            best_human = None
            best_iow = 0.0

            # Find the human with the highest IoW for this weapon
            for human in humans:
                inter_area = self.calculate_intersection_area(weapon.bbox, human.bbox)
                weapon_area = weapon.bbox.area
                
                if weapon_area == 0:
                    continue
                    
                iow = inter_area / float(weapon_area)
                
                if iow > best_iow:
                    best_iow = iow
                    best_human = human
            
            if best_iow >= self.iow_threshold and best_human is not None:
                validated_threats.append(ValidatedThreat(
                    weapon=weapon,
                    human=best_human,
                    iow=best_iow
                ))

        return validated_threats
