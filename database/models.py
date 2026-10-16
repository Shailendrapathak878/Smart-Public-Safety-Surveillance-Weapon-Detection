import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey
from database.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="operator")

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    source_url = Column(String)
    is_active = Column(Boolean, default=True)

class SecurityEvent(Base):
    __tablename__ = "security_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    weapon_type = Column(String)
    weapon_confidence = Column(Float)
    camera_source = Column(String)
    person_count = Column(Integer, default=1)
    evidence_path = Column(String)
    iow = Column(Float, nullable=True)
    status = Column(String, default="NEW") # NEW, ACKNOWLEDGED, REVIEWED, FALSE_POSITIVE
    alert_state = Column(String, default="INACTIVE") # ACTIVE, INACTIVE
    alarm_state = Column(String, default="INACTIVE") # ACTIVE, MUTED, INACTIVE
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("security_events.id"))
    provider = Column(String) # Email, Telegram
    status = Column(String, default="PENDING") # PENDING, SENT, FAILED
