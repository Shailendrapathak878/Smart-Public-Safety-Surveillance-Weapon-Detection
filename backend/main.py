import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.api import auth, monitoring, analysis, events, settings, analytics, alerts
from backend.websocket import monitoring_ws
from backend.websocket import alerts_ws

app = FastAPI(title="Smart Safety Command Center", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router)
app.include_router(monitoring.router)
app.include_router(analysis.router)
app.include_router(events.router)
app.include_router(settings.router)
app.include_router(analytics.router)
app.include_router(alerts.router)

# WebSockets
app.include_router(monitoring_ws.router)
app.include_router(alerts_ws.router)

# Mount Frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")
    
    # We might have assets folder at root
    assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/authority")
    async def serve_authority():
        authority_path = os.path.join(frontend_path, "authority.html")
        if os.path.exists(authority_path):
            return FileResponse(authority_path)
        return {"detail": "Authority dashboard not found"}

    # Serve index.html for all other non-API routes (SPA support)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Exclude API routes just in case
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return {"detail": "Not Found"}
            
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Frontend not found"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
