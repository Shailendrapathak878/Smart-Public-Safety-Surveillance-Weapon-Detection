import numpy as np
from ultralytics import YOLO
from typing import List
from core.detection_types import Detection, BoundingBox
from config import settings

class WeaponDetector:
    def __init__(self):
        self.model = YOLO(settings.WEAPON_MODEL_PATH)
        self.class_names = self.model.names

    def detect(self, frame: np.ndarray, conf: float = settings.CONFIDENCE_THRESHOLD) -> List[Detection]:
        # Run inference
        results = self.model.predict(frame, conf=conf, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                detections.append(Detection(
                    class_id=cls_id,
                    class_name=self.class_names[cls_id],
                    confidence=conf,
                    bbox=BoundingBox(x1, y1, x2, y2)
                ))
        return detections
