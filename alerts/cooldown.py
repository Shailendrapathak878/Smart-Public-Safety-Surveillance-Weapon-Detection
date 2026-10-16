import time
from config import settings

class CooldownManager:
    def __init__(self):
        self.last_event_time = 0.0
        self.cooldown_seconds = settings.COOLDOWN_SECONDS

    def can_trigger(self) -> bool:
        current_time = time.time()
        if (current_time - self.last_event_time) > self.cooldown_seconds:
            self.last_event_time = current_time
            return True
        return False
