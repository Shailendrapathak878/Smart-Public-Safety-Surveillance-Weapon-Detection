from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import SecurityEvent
from datetime import datetime, date

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # Simple stats: total events, today's events, active threats (mocked as 0 for stats overview)
    total_events = db.query(SecurityEvent).count()
    
    today = date.today()
    # Simple query for today's events, assuming timestamp is datetime
    # We might need a better date filter depending on DB, but this works for basic sqlite
    today_events = db.query(SecurityEvent).filter(
        SecurityEvent.timestamp >= datetime(today.year, today.month, today.day)
    ).count()

    return {
        "system_status": "Online",
        "ai_engine": "Active",
        "total_events": total_events,
        "events_today": today_events,
        "active_threats": 0 # This will be updated live by websockets during monitoring
    }
