import numpy as np
from ultralytics import YOLO
from typing import List
from core.detection_types import Detection, BoundingBox
from config import settings

class HumanDetector:
    def __init__(self):
        self.model = YOLO(settings.HUMAN_MODEL_PATH)
        # Assuming YOLO11n standard COCO classes, person is class 0

    def detect(self, frame: np.ndarray) -> List[Detection]:
        # Run inference, only for class 0 (person)
        results = self.model.predict(
            frame, 
            classes=[0], 
            conf=settings.PERSON_CONFIDENCE_THRESHOLD, 
            verbose=False
        )
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                
                detections.append(Detection(
                    class_id=0,
                    class_name="person",
                    confidence=conf,
                    bbox=BoundingBox(x1, y1, x2, y2)
                ))
        return detections
