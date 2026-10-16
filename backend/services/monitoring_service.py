import threading
import queue
import time
import cv2
import numpy as np
import base64
import json
from fastapi import WebSocket

from backend.services.inference_service import inference_service
from alerts.cooldown import CooldownManager
from alerts.dispatcher import NotificationDispatcher
from evidence.capture import EvidenceCapture
from core.visualizer import draw_detections
from database.database import get_db
from database.repository import Repository
from backend.services.alert_service import alert_service
import os
import uuid
from backend.services.timing import timing_log

class MonitoringSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.source_type = None
        self.source_value = None
        self.capture_generation = 0
        self.active_stop_event = None
        self.thread_lock = threading.RLock()
        
        self.cooldown = CooldownManager()
        self.dispatcher = NotificationDispatcher()
        self.evidence = EvidenceCapture()
        
        # Database session is created on demand for events
        self.db_gen = get_db()
        
    def start_backend_capture(self, source_type: str, source_value: str):
        with self.thread_lock:
            # Normalize IP camera URL
            if source_type == "ip_camera" and isinstance(source_value, str):
                if not source_value.endswith("/video"):
                    source_value = source_value.rstrip("/") + "/video"
                    
            if self.source_type == source_type and self.source_value == source_value and self.active_stop_event and not self.active_stop_event.is_set():
                return True
                
            self.stop()
            
            self.source_type = source_type
            self.source_value = source_value
            self.capture_generation += 1
            self.active_stop_event = threading.Event()
            self.latest_frame = None
            
            if hasattr(self, 'out_queue'):
                while not self.out_queue.empty():
                    try:
                        self.out_queue.get_nowait()
                    except queue.Empty:
                        break
            
            threading.Thread(target=self._capture_loop, args=(self.active_stop_event, self.source_value, self.source_type, self.capture_generation), daemon=True).start()
            threading.Thread(target=self._inference_loop, args=(self.active_stop_event, self.capture_generation), daemon=True).start()
            return True
        
    def _capture_loop(self, stop_event, source_value, source_type, generation_id):
        cap = None
        try:
            if source_type in ["ip_camera", "rtsp", "video"]:
                cap = cv2.VideoCapture(source_value)
                if source_type != "video":
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap or not cap.isOpened():
                return
                
            fps_delay = 0
            if source_type == "video":
                vid_fps = cap.get(cv2.CAP_PROP_FPS)
                if vid_fps > 0:
                    fps_delay = 1.0 / vid_fps

            while not stop_event.is_set() and cap.isOpened():
                loop_start = time.time()
                try:
                    ret, frame = cap.read()
                except Exception as e:
                    print(f"Capture read error: {e}")
                    break
                    
                if not ret or stop_event.is_set():
                    break
                
                if generation_id != self.capture_generation:
                    break
                    
                self.latest_frame = frame
                
                if source_type == "video" and fps_delay > 0:
                    elapsed = time.time() - loop_start
                    if elapsed < fps_delay:
                        time.sleep(fps_delay - elapsed)
                
            if source_type == "video" and not stop_event.is_set() and generation_id == self.capture_generation:
                # Wait briefly to let inference process the last frame before tearing down
                time.sleep(0.5)
        finally:
            if cap:
                cap.release()
        
    def _inference_loop(self, stop_event, generation_id):
        last_time = time.time()

        while not stop_event.is_set():
            if generation_id != self.capture_generation:
                break
                
            frame_to_process = self.latest_frame
            self.latest_frame = None # Consume it
            
            if frame_to_process is not None:
                # Resize if resolution is too high to reduce inference latency
                if self.source_type != "video":
                    h, w = frame_to_process.shape[:2]
                    if w > 1280:
                        scale = 1280 / w
                        frame_to_process = cv2.resize(frame_to_process, (int(w * scale), int(h * scale)))
                        
                self._process_and_send_frame(frame_to_process, last_time)
                last_time = time.time()
            else:
                # For live feeds and video, yield to prevent tight loop if no frame is ready
                time.sleep(0.01)
                    
    def start_browser_session(self):
        with self.thread_lock:
            if self.source_type == "browser_webcam" and self.active_stop_event and not self.active_stop_event.is_set():
                return
                
            self.stop()
            self.source_type = "browser_webcam"
            self.capture_generation += 1
            self.active_stop_event = threading.Event()
            self.latest_frame = None
            
            if hasattr(self, 'out_queue'):
                while not self.out_queue.empty():
                    try:
                        self.out_queue.get_nowait()
                    except queue.Empty:
                        break
                        
            threading.Thread(target=self._inference_loop, args=(self.active_stop_event, self.capture_generation), daemon=True).start()

    def process_browser_frame(self, frame_bytes: bytes):
        if self.source_type != "browser_webcam" or not self.active_stop_event or self.active_stop_event.is_set():
            self.start_browser_session()
            
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is not None:
            # We only maintain the newest unprocessed frame to prevent latency buildup
            self.latest_frame = frame

    def _process_and_send_frame(self, frame, last_time):
        weapons, humans, threats = inference_service.detect_and_validate(frame)
        has_threat = len(threats) > 0
        alert_service.alarm.update(has_threat)
        # Draw boxes
        display_frame = draw_detections(frame, weapons, humans)

        event_data = None
        if has_threat and self.cooldown.can_trigger():
            db_session = next(get_db())
            try:
                repo = Repository(db_session)
                for threat in threats:
                    event_id = str(uuid.uuid4())
                    timing_log("T0", event_id)
                    event = repo.create_security_event(threat, self.source_type, event_id=event_id)
                    alert_service.publish_threat(event)
                    threading.Thread(
                        target=alert_service.persist_evidence,
                        args=(event.id, display_frame, threat),
                        daemon=True,
                        name="evidence-save"
                    ).start()
                    self.dispatcher.dispatch(event)
                    event_data = {"id": event.id, "weapon": event.weapon_type, "confidence": event.weapon_confidence}
            finally:
                db_session.close()

        curr_time = time.time()
        fps = int(1 / (curr_time - last_time)) if curr_time - last_time > 0 else 0

        _, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        b64_image = base64.b64encode(buffer).decode('utf-8')
        
        message = {
            "type": "frame",
            "fps": fps,
            "persons": len(humans),
            "weapons": len(weapons),
            "threat_status": has_threat,
            "image": b64_image,
            "event": event_data
        }
        
        # In a real async environment, we should use asyncio event loop to send.
        # Since this might be called from a synchronous thread, we need a way to schedule it.
        # But we can just use an asyncio run_coroutine_threadsafe if needed, or queue it.
        # However, FastAPI websockets provide standard async methods.
        # We will expose a queue here and the async endpoint will read from it.
        if not hasattr(self, 'out_queue'):
            self.out_queue = queue.Queue(maxsize=1)
            
        try:
            self.out_queue.put_nowait(message)
        except queue.Full:
            self.out_queue.get()
            self.out_queue.put_nowait(message)

    def stop(self):
        with self.thread_lock:
            if self.active_stop_event:
                self.active_stop_event.set()
                
            self.capture_generation += 1
            # Clean up temp file if it was a video
            if self.source_type == "video" and self.source_value and os.path.exists(self.source_value):
                try:
                    os.remove(self.source_value)
                except Exception:
                    pass
                    
            self.source_type = None
            self.source_value = None
            self.active_stop_event = None
