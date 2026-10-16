# Smart Public Safety Surveillance & Weapon Detection

🛡️ Command Center Dashboard

## Architecture

This application has been migrated to a modern Single Page Application (SPA) architecture:

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: FastAPI (Python)
- **Live Video**: WebSockets
- **Inference**: YOLO11s (Weapons), YOLO11n (Humans)

## Installation & Dependencies

1. Ensure Python 3.10+ is installed.
2. Install the backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Startup

Start the FastAPI server:

```bash
python -m uvicorn backend.main:app --reload
```

The application will serve the frontend automatically at `http://127.0.0.1:8000`.

## Prototype Credentials

For testing purposes, the following credentials can be used:
- **Username**: `admin`
- **Password**: `admin123`

## Features

### Browser Camera Permission
When using the Laptop Webcam mode, your browser will request permission to access the camera. The video capture is safely handled on the client-side (via `navigator.mediaDevices.getUserMedia`) and frames are securely transmitted over WebSocket to the backend for inference.

### Live Monitoring Sources
- **Laptop Webcam**: Transmits frames directly from the browser's camera.
- **Phone / IP Camera**: Connects the backend directly to the provided network camera URL.
- **RTSP**: Connects the backend directly to CCTV RTSP streams.

### Analysis
- **Image Analysis**: Upload static images (JPG, PNG). The system will analyze the image, detect weapons/persons, and flag active threats. Validated threats trigger an event and a 5-second alarm.
- **Video Analysis**: Upload videos (MP4, AVI) for continuous frame-by-frame analysis via background tasks and WebSocket delivery.

## API Overview

### REST Endpoints
- `POST /api/auth/login` - Authenticate
- `GET /api/auth/me` - Get current user profile
- `GET /api/dashboard/stats` - Fetch overall system statistics
- `POST /api/analysis/image` - Analyze a single image upload
- `POST /api/analysis/video` - Upload and analyze video
- `GET /api/events` - Fetch recent security events
- `GET /api/settings` - Fetch active system settings

### WebSocket Endpoints
- `WS /ws/monitoring` - Real-time continuous processing connection for live streams.

## Testing Instructions

1. **Pytest (Backend)**: 
   ```bash
   python -m pytest tests/
   ```

2. **Playwright (UI)**:
   Ensure you have installed playwright browsers (`playwright install chromium`), then run:
   ```bash
   python test_browser.py
   ```
