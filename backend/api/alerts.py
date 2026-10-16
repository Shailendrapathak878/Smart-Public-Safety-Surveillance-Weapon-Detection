from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.auth import get_authority_user
from backend.api.events import _serialize_event
from backend.services.alert_service import alert_service
from database.database import get_db
from database.models import SecurityEvent
from database.repository import Repository

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

class CommandRequest(BaseModel):
    command_id: str

class ReviewRequest(CommandRequest):
    classification: str = "REVIEWED"

class MuteRequest(CommandRequest):
    type: str = "MUTE_ALARM"

@router.get("/active")
def get_active_alerts(db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    print("[AUTHORITY] active alert sync", flush=True)
    events = Repository(db).get_active_events()
    alert_service.restore_active(events)
    return {
        "alerts": [_serialize_event(event) for event in events],
        "alarm_state": alert_service.current_alarm_state(),
    }

@router.post("/events/{event_id}/acknowledge")
def acknowledge_alert(event_id: str, request: CommandRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    previous = alert_service.command_result(request.command_id)
    if previous:
        return previous
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event = Repository(db).acknowledge_event(event, current_user["username"])
    alert_service.publish_state_change(event)
    result = {
        "type": "COMMAND_ACK",
        "command_id": request.command_id,
        "status": "accepted",
        "event_id": event.id,
        "event_status": event.status,
        "alarm_state": alert_service.current_alarm_state(),
    }
    alert_service.remember_command(request.command_id, result)
    return result

@router.post("/events/{event_id}/mute")
def mute_alarm(event_id: str, request: MuteRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    previous = alert_service.command_result(request.command_id)
    if previous:
        return previous
    if request.type != "MUTE_ALARM":
        raise HTTPException(status_code=400, detail="Invalid alarm command")
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        event = Repository(db).mute_alarm(event)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    alert_service.mute_alarm(event)
    result = {
        "type": "COMMAND_ACK",
        "command_id": request.command_id,
        "status": "accepted",
        "event_id": event.id,
        "event_status": event.status,
        "alarm_state": "MUTED",
    }
    alert_service.remember_command(request.command_id, result)
    return result

@router.post("/events/{event_id}/review")
def review_alert(event_id: str, request: ReviewRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    previous = alert_service.command_result(request.command_id)
    if previous:
        return previous
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        event = Repository(db).review_event(event, current_user["username"], request.classification)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    alert_service.publish_state_change(event)
    result = {
        "type": "COMMAND_ACK",
        "command_id": request.command_id,
        "status": "accepted",
        "event_id": event.id,
        "event_status": event.status,
    }
    alert_service.remember_command(request.command_id, result)
    return result