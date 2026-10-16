from fastapi import APIRouter
from pydantic import BaseModel
from config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    iow_threshold: float
    weapon_confidence: float
    cooldown_seconds: int

# We'll store these in memory for the prototype, normally this goes to DB or config file
class AppSettings:
    def __init__(self):
        self.iow_threshold = settings.IOW_THRESHOLD
        self.weapon_confidence = settings.CONFIDENCE_THRESHOLD
        self.cooldown_seconds = 10 # Default from prompt

app_settings = AppSettings()

@router.get("")
def get_settings():
    return {
        "iow_threshold": app_settings.iow_threshold,
        "weapon_confidence": app_settings.weapon_confidence,
        "cooldown_seconds": app_settings.cooldown_seconds
    }

@router.post("")
def update_settings(new_settings: SettingsUpdate):
    app_settings.iow_threshold = new_settings.iow_threshold
    app_settings.weapon_confidence = new_settings.weapon_confidence
    app_settings.cooldown_seconds = new_settings.cooldown_seconds
    return {"message": "Settings updated successfully"}
