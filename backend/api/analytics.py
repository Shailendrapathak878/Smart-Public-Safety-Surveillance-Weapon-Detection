from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from database.database import get_db
from database.models import SecurityEvent
from backend.api.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/summary")
def get_analytics_summary(
    time_range: str = Query("7d", alias="range"),
    weapon: Optional[str] = None,
    source: Optional[str] = None,
    min_confidence: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    now = datetime.now(timezone.utc)
    
    # Calculate cutoff time
    if time_range == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "7d":
        cutoff = now - timedelta(days=7)
    elif time_range == "30d":
        cutoff = now - timedelta(days=30)
    else: # all time
        cutoff = None

    # Base query
    query = db.query(SecurityEvent)
    
    if cutoff:
        query = query.filter(SecurityEvent.timestamp >= cutoff)
    if weapon and weapon.lower() != "all":
        query = query.filter(SecurityEvent.weapon_type.ilike(weapon))
    if source and source.lower() != "all":
        query = query.filter(SecurityEvent.camera_source.ilike(source))
    if min_confidence is not None:
        query = query.filter(SecurityEvent.weapon_confidence >= (min_confidence / 100.0))
        
    events = query.order_by(SecurityEvent.timestamp.desc()).all()
    
    if not events:
        return {
            "range": time_range,
            "kpis": {
                "total_threats": 0,
                "evidence_captured": 0,
                "most_detected_weapon": "-",
                "most_active_source": "-",
                "average_confidence": 0
            },
            "timeline": [],
            "weapon_distribution": [],
            "source_distribution": [],
            "hourly_activity": [],
            "heatmap": [],
            "confidence_distribution": [],
            "insights": None,
            "recent_events": []
        }

    # Aggregate KPIs
    total_threats = len(events)
    evidence_captured = sum(1 for e in events if e.evidence_path)
    avg_conf = sum(e.weapon_confidence for e in events) / total_threats if total_threats > 0 else 0
    
    # Distributions
    weapon_counts = {}
    source_counts = {}
    hourly_counts = {str(i).zfill(2): 0 for i in range(24)}
    heatmap_data = {day: {str(i).zfill(2): 0 for i in range(24)} for day in range(7)}
    conf_ranges = {
        "0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0
    }
    
    # Timeline
    timeline_dict = {}

    for e in events:
        # Weapons
        wt = e.weapon_type or "Unknown"
        weapon_counts[wt] = weapon_counts.get(wt, 0) + 1
        
        # Sources
        cs = e.camera_source or "Unknown"
        source_counts[cs] = source_counts.get(cs, 0) + 1
        
        # Time processing
        hour_str = e.timestamp.strftime("%H")
        hourly_counts[hour_str] += 1
        
        day_of_week = e.timestamp.weekday() # 0 = Monday, 6 = Sunday
        heatmap_data[day_of_week][hour_str] += 1
        
        # Timeline aggregation
        if time_range == "today":
            time_key = e.timestamp.strftime("%Y-%m-%d %H:00")
        else:
            time_key = e.timestamp.strftime("%Y-%m-%d")
        timeline_dict[time_key] = timeline_dict.get(time_key, 0) + 1
        
        # Confidence
        conf = e.weapon_confidence * 100
        if conf <= 20: conf_ranges["0-20%"] += 1
        elif conf <= 40: conf_ranges["20-40%"] += 1
        elif conf <= 60: conf_ranges["40-60%"] += 1
        elif conf <= 80: conf_ranges["60-80%"] += 1
        else: conf_ranges["80-100%"] += 1

    most_detected_weapon = max(weapon_counts.items(), key=lambda x: x[1])[0] if weapon_counts else "-"
    most_active_source = max(source_counts.items(), key=lambda x: x[1])[0] if source_counts else "-"
    
    # Formatting for frontend
    timeline = [{"time": k, "count": v} for k, v in sorted(timeline_dict.items())]
    weapon_distribution = [{"name": k, "count": v} for k, v in sorted(weapon_counts.items(), key=lambda x: x[1], reverse=True)]
    source_distribution = [{"name": k, "count": v} for k, v in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)]
    hourly_activity = [{"hour": k, "count": v} for k, v in sorted(hourly_counts.items())]
    
    heatmap = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day_idx in range(7):
        for h in range(24):
            count = heatmap_data[day_idx][str(h).zfill(2)]
            heatmap.append({
                "day": days[day_idx],
                "hour": str(h).zfill(2),
                "count": count
            })
            
    confidence_distribution = [{"range": k, "count": v} for k, v in conf_ranges.items()]

    # Insights
    peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
    insights = {
        "most_detected": f"{most_detected_weapon} — {round((weapon_counts.get(most_detected_weapon, 0) / total_threats) * 100)}%" if weapon_counts else "-",
        "most_active_source": f"{most_active_source} — {round((source_counts.get(most_active_source, 0) / total_threats) * 100)}%" if source_counts else "-",
        "average_confidence": f"{round(avg_conf * 100, 1)}%",
        "peak_activity": f"{peak_hour[0]}:00–{str(int(peak_hour[0])+1).zfill(2)}:00" if peak_hour[1] > 0 else "-"
    }

    recent = []
    for ev in events[:5]:
        ev_dict = {
            "id": ev.id,
            "timestamp": ev.timestamp.isoformat(),
            "weapon_type": ev.weapon_type,
            "weapon_confidence": ev.weapon_confidence,
            "camera_source": ev.camera_source,
            "evidence_url": f"/api/events/{ev.id}/evidence" if ev.evidence_path else None
        }
        recent.append(ev_dict)

    return {
        "range": time_range,
        "kpis": {
            "total_threats": total_threats,
            "evidence_captured": evidence_captured,
            "most_detected_weapon": most_detected_weapon,
            "most_active_source": most_active_source,
            "average_confidence": round(avg_conf * 100, 1)
        },
        "timeline": timeline,
        "weapon_distribution": weapon_distribution,
        "source_distribution": source_distribution,
        "hourly_activity": hourly_activity,
        "heatmap": heatmap,
        "confidence_distribution": confidence_distribution,
        "insights": insights,
        "recent_events": recent
    }
