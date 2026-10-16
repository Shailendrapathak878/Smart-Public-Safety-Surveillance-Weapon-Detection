import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
EVIDENCE_DIR = BASE_DIR / "evidence" / "captures"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure data and evidence directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Model configuration
WEAPON_MODEL_PATH = MODELS_DIR / "best.pt"
HUMAN_MODEL_PATH = MODELS_DIR / "yolo11n.pt"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/surveillance.db")

# AI/Inference Settings
IOW_THRESHOLD = 0.5  # Intersection over Weapon Area threshold for validated threat
CONFIDENCE_THRESHOLD = 0.25  # Base confidence threshold for weapons
PERSON_CONFIDENCE_THRESHOLD = 0.4 # Confidence threshold for person detection

# Threat/Alarm Settings
COOLDOWN_SECONDS = 10
THREAT_DISMISS_FRAMES = 15 # Number of consecutive frames without threat to dismiss the alarm
ALARM_DURATION_SECONDS = 5

# UI Settings
APP_NAME = os.getenv("APP_NAME", "Smart Safety Command Center")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Auth
EVAL_USERNAME = os.getenv("EVAL_USERNAME", "admin")
EVAL_PASSWORD = os.getenv("EVAL_PASSWORD", "admin123")
