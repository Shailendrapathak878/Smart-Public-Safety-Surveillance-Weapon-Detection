import pygame
import os
import threading
from config import settings
from backend.services.timing import timing_log

class AlarmManager:
    def __init__(self):
        # We need to initialize pygame mixer safely
        try:
            pygame.mixer.init()
            timing_log("A2", "alarm")
            self.buzzer_path = str(settings.ASSETS_DIR / "buzzer.mp3")
            
            # Create dummy buzzer if it doesn't exist so it doesn't crash
            if not os.path.exists(self.buzzer_path):
                settings.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                with open(self.buzzer_path, 'wb') as f:
                    pass # Just touch the file, pygame will fail to play it but won't crash init if handled
                    
            if os.path.getsize(self.buzzer_path) > 0:
                pygame.mixer.music.load(self.buzzer_path)
                timing_log("A3", "alarm")
                self.is_loaded = True
            else:
                self.is_loaded = False
        except Exception as e:
            print(f"Error initializing Pygame Mixer: {e}")
            self.is_loaded = False
            
        self.no_threat_frames = 0
        self.dismiss_frames = settings.THREAT_DISMISS_FRAMES
        self._lock = threading.Lock()
        self._stop_timer = None
        self.state = "UNAVAILABLE" if not self.is_loaded else "STOPPED"

    def activate(self):
        with self._lock:
            print("[ALARM] activate requested", flush=True)
            timing_log("A1", "alarm")
            if not self.is_loaded:
                self.state = "UNAVAILABLE"
                return
            self.no_threat_frames = 0
            self.state = "ACTIVE"
            if pygame.mixer.music.get_busy():
                return
            try:
                pygame.mixer.music.play(-1)
                timing_log("A4", "alarm")
                if self._stop_timer:
                    self._stop_timer.cancel()
                self._stop_timer = threading.Timer(
                    settings.ALARM_DURATION_SECONDS,
                    self.stop,
                )
                self._stop_timer.daemon = True
                self._stop_timer.start()
                print("[ALARM] activate completed", flush=True)
            except Exception as error:
                print(f"Alarm playback failed: {error}", flush=True)
                self.state = "UNAVAILABLE"

    def stop(self):
        with self._lock:
            print("[ALARM] stop requested", flush=True)
            if self._stop_timer:
                self._stop_timer.cancel()
                self._stop_timer = None
            if self.is_loaded and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.state = "STOPPED" if self.is_loaded else "UNAVAILABLE"
            print("[ALARM] stop completed", flush=True)

    def mute(self):
        with self._lock:
            print("[ALARM] mute requested", flush=True)
            if self._stop_timer:
                self._stop_timer.cancel()
                self._stop_timer = None
            if self.is_loaded and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.state = "MUTED" if self.is_loaded else "UNAVAILABLE"
            print("[ALARM] mute completed", flush=True)

    def restore_muted(self):
        with self._lock:
            self.state = "MUTED" if self.is_loaded else "UNAVAILABLE"

    def update(self, has_threat: bool):
        with self._lock:
            if not self.is_loaded:
                return

            if has_threat:
                self.no_threat_frames = 0
                if self.state == "MUTED":
                    return
                if not pygame.mixer.music.get_busy():
                    try:
                        pygame.mixer.music.play(-1) # Loop indefinitely
                        self.state = "ACTIVE"
                    except:
                        self.state = "UNAVAILABLE"
            else:
                self.no_threat_frames += 1
                if self.no_threat_frames >= self.dismiss_frames:
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                    self.state = "STOPPED"
