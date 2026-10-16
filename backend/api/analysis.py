from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import cv2
import numpy as np
import base64
import threading
import time
import uuid
import os
import tempfile
import uuid

from database.database import get_db
from database.repository import Repository
from backend.services.inference_service import inference_service
from alerts.cooldown import CooldownManager
from alerts.dispatcher import NotificationDispatcher
from evidence.capture import EvidenceCapture
from core.visualizer import draw_detections
from backend.services.alert_service import alert_service
from backend.services.timing import timing_log

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

cooldown_manager = CooldownManager()
dispatcher = NotificationDispatcher()
evidence_capture = EvidenceCapture()

@router.post("/image")
async def analyze_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image file")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    weapons, humans, threats = inference_service.detect_and_validate(frame)
    has_threat = len(threats) > 0

    repo = Repository(db)

    # Annotate frame
    display_frame = draw_detections(frame, weapons, humans)

    event_data = None
    if has_threat and cooldown_manager.can_trigger():
        for threat in threats:
            event_id = str(uuid.uuid4())
            timing_log("T0", event_id)
            event = repo.create_security_event(threat, "Image Upload", event_id=event_id)
            alert_service.publish_threat(event)
            threading.Thread(
                target=alert_service.persist_evidence,
                args=(event.id, display_frame, threat),
                daemon=True,
                name="evidence-save"
            ).start()
            dispatcher.dispatch(event)
            event_data = {"id": event.id, "weapon": event.weapon_type, "confidence": event.weapon_confidence}
        
    # Encode to base64
    _, buffer = cv2.imencode('.jpg', display_frame)
    b64_image = base64.b64encode(buffer).decode('utf-8')

    return {
        "persons": len(humans),
        "weapons": len(weapons),
        "threat_status": has_threat,
        "image": b64_image,
        "event": event_data
    }

# We will handle Video Upload logic in the monitoring_service to reuse WebSocket delivery.
# This endpoint just accepts the file and saves it, returning a path/id.
@router.post("/video")
async def upload_video(file: UploadFile = File(...)):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid video file")

    temp_dir = tempfile.gettempdir()
    session_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(temp_dir, f"video_{session_id}{ext}")
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    return {"session_id": session_id, "path": temp_path}
