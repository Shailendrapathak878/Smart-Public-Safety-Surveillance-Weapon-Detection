import asyncio
import threading
from typing import Any, Dict, Optional, Set

from alerts.alarm import AlarmManager
from backend.services.timing import timing_log


def serialize_event(event) -> Dict[str, Any]:
    return {
        "event_id": event.id,
        "weapon": event.weapon_type,
        "confidence": event.weapon_confidence,
        "iow": event.iow,
        "source": event.camera_source,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "evidence_url": f"/api/events/{event.id}/evidence" if event.evidence_path else None,
        "status": event.status,
        "alert_state": event.alert_state,
        "alarm_state": event.alarm_state,
        "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
        "acknowledged_by": event.acknowledged_by,
        "reviewed_at": event.reviewed_at.isoformat() if event.reviewed_at else None,
        "reviewed_by": event.reviewed_by,
    }


class AlertService:
    def __init__(self):
        self._subscribers: Dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}
        self._seen_events: Set[str] = set()
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._inactive_events: Set[str] = set()
        self._lock = threading.RLock()
        self.alarm = AlarmManager()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        with self._lock:
            self._subscribers[queue] = asyncio.get_running_loop()
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        with self._lock:
            self._subscribers.pop(queue, None)

    def _publish(self, message: Dict[str, Any]):
        with self._lock:
            subscribers = list(self._subscribers.items())
        for subscriber, loop in subscribers:
            loop.call_soon_threadsafe(subscriber.put_nowait, message)

    def restore_active(self, events):
        print("[AUTHORITY] alarm restore decision", flush=True)
        print(f"[ALARM] restore requested events={len(events)}", flush=True)
        with self._lock:
            self._seen_events.update(event.id for event in events)
            if events and all(event.alarm_state == "MUTED" for event in events):
                self.alarm.restore_muted()
        print("[ALARM] restore skipped: dashboard initialization", flush=True)

    def publish_threat(self, event) -> bool:
        with self._lock:
            if event.id in self._seen_events:
                return False
            self._seen_events.add(event.id)
        timing_log("T3", event.id)
        self._publish({"type": "THREAT_DETECTED", **serialize_event(event), "alarm_state": "ACTIVE"})
        threading.Thread(target=self._activate_alarm, args=(event.id,), daemon=True, name="central-alarm").start()
        return True

    def _activate_alarm(self, event_id: str):
        with self._lock:
            if event_id in self._inactive_events:
                return
            timing_log("A0", event_id)
            self.alarm.activate()

    def publish_evidence_ready(self, event):
        self._publish({"type": "EVIDENCE_READY", **serialize_event(event), "alarm_state": self.alarm.state})

    def persist_evidence(self, event_id, frame, threat):
        from database.database import get_db
        from database.models import SecurityEvent
        from database.repository import Repository
        from evidence.capture import EvidenceCapture

        try:
            evidence_path = EvidenceCapture().save_evidence(frame, threat)
            db_session = next(get_db())
            try:
                event = Repository(db_session).update_evidence_path(event_id, evidence_path)
            finally:
                db_session.close()
            if event:
                self.publish_evidence_ready(event)
        except Exception as error:
            print(f"Evidence persistence failed for {event_id}: {error}", flush=True)

    def publish_state_change(self, event):
        if event.status in {"ACKNOWLEDGED", "REVIEWED", "FALSE_POSITIVE"}:
            with self._lock:
                self._inactive_events.add(event.id)
                self.alarm.stop()
            event.alarm_state = "INACTIVE"
        self._publish({"type": "ALERT_STATE_CHANGED", **serialize_event(event), "alarm_state": self.alarm.state})

    def mute_alarm(self, event):
        with self._lock:
            self.alarm.mute()
        event.alarm_state = "MUTED"
        self._publish({"type": "ALERT_STATE_CHANGED", **serialize_event(event), "alarm_state": "MUTED"})

    def current_alarm_state(self) -> str:
        return self.alarm.state

    def command_result(self, command_id: str):
        with self._lock:
            return self._commands.get(command_id)

    def remember_command(self, command_id: str, result: Dict[str, Any]):
        with self._lock:
            self._commands[command_id] = result


alert_service = AlertService()