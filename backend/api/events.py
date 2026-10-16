from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database.database import get_db
from database.repository import Repository
from database.models import SecurityEvent
from backend.api.auth import get_current_user, get_authority_user
import pathlib

router = APIRouter(prefix="/api/events", tags=["events"])

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = (PROJECT_ROOT / "evidence" / "captures").resolve()

@router.get("")
def _serialize_event(event):
    ev_dict = {
        "id": event.id,
        "timestamp": event.timestamp,
        "weapon_type": event.weapon_type,
        "weapon_confidence": event.weapon_confidence,
        "iow": event.iow,
        "camera_source": event.camera_source,
        "person_count": event.person_count,
        "status": event.status,
        "alert_state": event.alert_state,
        "alarm_state": event.alarm_state,
        "acknowledged_at": event.acknowledged_at,
        "acknowledged_by": event.acknowledged_by,
        "reviewed_at": event.reviewed_at,
        "reviewed_by": event.reviewed_by,
    }
    if event.evidence_path:
        ev_dict["evidence_url"] = f"/api/events/{event.id}/evidence"
    return ev_dict

@router.get("")
def get_events(limit: int = 50, db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    repo = Repository(db)
    events = repo.get_recent_events(limit=limit)
    result = []
    for ev in events:
        result.append(_serialize_event(ev))
    return result

@router.get("/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _serialize_event(event)

@router.get("/{event_id}/evidence")
def get_evidence(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_authority_user)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    if not event.evidence_path:
        raise HTTPException(status_code=404, detail="Evidence unavailable")
        
    try:
        requested_path = pathlib.Path(event.evidence_path).resolve()
        
        # Verify it exists
        if not requested_path.is_file():
            raise HTTPException(status_code=404, detail="Evidence file not found")
            
        # Prevent path traversal by checking if it's within EVIDENCE_DIR
        if not requested_path.is_relative_to(EVIDENCE_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
            
        return FileResponse(requested_path, media_type="image/jpeg")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=404, detail="Evidence unavailable")

@router.delete("/{event_id}")
def delete_event(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    deleted_file = False
    if event.evidence_path:
        try:
            requested_path = pathlib.Path(event.evidence_path).resolve()
            if requested_path.is_file() and requested_path.is_relative_to(EVIDENCE_DIR):
                requested_path.unlink()
                deleted_file = True
        except Exception:
            pass # ignore missing file error
            
    db.delete(event)
    db.commit()
    
    return {
        "success": True,
        "deleted_event": True,
        "deleted_file": deleted_file
    }

@router.delete("/clear")
def clear_all_evidence(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    events = db.query(SecurityEvent).all()
    deleted_events = 0
    deleted_files = 0
    
    for event in events:
        if event.evidence_path:
            try:
                requested_path = pathlib.Path(event.evidence_path).resolve()
                if requested_path.is_file() and requested_path.is_relative_to(EVIDENCE_DIR):
                    requested_path.unlink()
                    deleted_files += 1
            except Exception as e:
                # Ignore missing file errors, continue deletion
                pass
        
        db.delete(event)
        deleted_events += 1
        
    db.commit()
    
    return {
        "success": True,
        "deleted_events": deleted_events,
        "deleted_files": deleted_files
    }
