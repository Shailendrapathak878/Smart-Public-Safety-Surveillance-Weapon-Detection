from database.models import SecurityEvent

class NotificationDispatcher:
    def __init__(self):
        pass

    def dispatch(self, event: SecurityEvent):
        # Mocked for now. In production, this would send an async HTTP request or MQTT message.
        print(f"[NOTIFICATION] ACTIVE THREAT EVENT DISPATCHED: {event.id}")
        print(f"Weapon: {event.weapon_type} (Conf: {event.weapon_confidence:.2f})")
        print(f"Evidence: {event.evidence_path}")
