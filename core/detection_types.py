from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
    
    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)

@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox

@dataclass
class ValidatedThreat:
    weapon: Detection
    human: Detection
    iow: float # Intersection over Weapon Area
