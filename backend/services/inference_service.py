from core.weapon_detector import WeaponDetector
from core.human_detector import HumanDetector
from core.threat_engine import ThreatEngine
from backend.api.settings import app_settings

class InferenceService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InferenceService, cls).__new__(cls)
            cls._instance.weapon_detector = WeaponDetector()
            cls._instance.human_detector = HumanDetector()
            cls._instance.threat_engine = ThreatEngine(iow_threshold=app_settings.iow_threshold)
        return cls._instance

    def detect_and_validate(self, frame):
        # Update threshold if settings changed
        self.threat_engine.iow_threshold = app_settings.iow_threshold
        
        weapons = self.weapon_detector.detect(frame, conf=app_settings.weapon_confidence)
        humans = self.human_detector.detect(frame)
        threats = self.threat_engine.validate_threats(weapons, humans)
        return weapons, humans, threats

inference_service = InferenceService()
