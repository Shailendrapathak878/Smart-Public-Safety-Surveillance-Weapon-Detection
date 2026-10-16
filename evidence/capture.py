import cv2
import numpy as np
import os
import uuid
from datetime import datetime
from config import settings
from core.detection_types import ValidatedThreat

class EvidenceCapture:
    def __init__(self):
        self.base_dir = settings.EVIDENCE_DIR

    def _get_daily_dir(self) -> str:
        now = datetime.now()
        path = self.base_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def save_evidence(self, frame: np.ndarray, threat: ValidatedThreat) -> str:
        # Create a copy so we don't draw on the live feed incorrectly if it's referenced elsewhere
        capture_img = frame.copy()
        
        # Draw Weapon Box (Red)
        wx1, wy1, wx2, wy2 = threat.weapon.bbox.x1, threat.weapon.bbox.y1, threat.weapon.bbox.x2, threat.weapon.bbox.y2
        cv2.rectangle(capture_img, (wx1, wy1), (wx2, wy2), (0, 0, 255), 2)
        cv2.putText(capture_img, f"{threat.weapon.class_name} {threat.weapon.confidence:.2f}", 
                    (wx1, wy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Draw Human Box (Yellow)
        hx1, hy1, hx2, hy2 = threat.human.bbox.x1, threat.human.bbox.y1, threat.human.bbox.x2, threat.human.bbox.y2
        cv2.rectangle(capture_img, (hx1, hy1), (hx2, hy2), (0, 255, 255), 2)
        cv2.putText(capture_img, f"Person {threat.iow:.2f} IoW", 
                    (hx1, hy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Generate filename
        event_uuid = str(uuid.uuid4())
        filename = f"event_{event_uuid}.jpg"
        filepath = os.path.join(self._get_daily_dir(), filename)

        # Save Image
        cv2.imwrite(filepath, cv2.cvtColor(capture_img, cv2.COLOR_RGB2BGR))
        
        return filepath
