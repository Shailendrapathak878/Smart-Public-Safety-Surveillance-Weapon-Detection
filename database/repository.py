from sqlalchemy.orm import Session
from database import models
from core.detection_types import ValidatedThreat
from datetime import datetime, timezone
import uuid
from backend.services.timing import timing_log

class Repository:
    def __init__(self, db: Session):
        self.db = db

    def initialize_db(self, engine):
        models.Base.metadata.create_all(bind=engine)

    def create_security_event(
        self, 
        threat: ValidatedThreat, 
        camera_source: str, 
        evidence_path: str = None,
        event_id: str = None
    ) -> models.SecurityEvent:
        event = models.SecurityEvent(
            id=event_id or str(uuid.uuid4()),
            weapon_type=threat.weapon.class_name,
            weapon_confidence=threat.weapon.confidence,
            camera_source=camera_source,
            person_count=1,
            evidence_path=evidence_path,
            iow=threat.iow,
            status="NEW",
            alert_state="ACTIVE",
            alarm_state="ACTIVE"
        )
        self.db.add(event)
        timing_log("T1", event.id)
        self.db.commit()
        timing_log("T2", event.id)
        self.db.refresh(event)
        return event

    def update_evidence_path(self, event_id: str, evidence_path: str):
        event = self.db.query(models.SecurityEvent).filter(models.SecurityEvent.id == event_id).first()
        if event:
            event.evidence_path = evidence_path
            self.db.commit()
            self.db.refresh(event)
        return event

    def get_recent_events(self, limit: int = 10):
        return self.db.query(models.SecurityEvent)\
            .order_by(models.SecurityEvent.timestamp.desc())\
            .limit(limit)\
            .all()

    def get_active_events(self):
        return self.db.query(models.SecurityEvent)\
            .filter(models.SecurityEvent.alert_state == "ACTIVE")\
            .order_by(models.SecurityEvent.timestamp.desc())\
            .all()

    def acknowledge_event(self, event: models.SecurityEvent, username: str):
        if event.status == "NEW":
            event.status = "ACKNOWLEDGED"
            event.alert_state = "INACTIVE"
            event.alarm_state = "INACTIVE"
            event.acknowledged_at = datetime.now(timezone.utc)
            event.acknowledged_by = username
            self.db.commit()
            self.db.refresh(event)
        return event

    def review_event(self, event: models.SecurityEvent, username: str, classification: str = "REVIEWED"):
        if classification not in {"REVIEWED", "FALSE_POSITIVE"}:
            raise ValueError("Invalid review classification")
        event.status = classification
        event.alert_state = "INACTIVE"
        event.alarm_state = "INACTIVE"
        event.reviewed_at = datetime.now(timezone.utc)
        event.reviewed_by = username
        self.db.commit()
        self.db.refresh(event)
        return event

    def mute_alarm(self, event: models.SecurityEvent):
        if event.alert_state != "ACTIVE":
            raise ValueError("Only an active alert can be muted")
        event.alarm_state = "MUTED"
        self.db.commit()
        self.db.refresh(event)
        return event
