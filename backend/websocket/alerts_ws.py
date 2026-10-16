import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.auth import MOCK_TOKEN
from backend.services.alert_service import alert_service
from backend.services.timing import timing_log

router = APIRouter(tags=["alerts-websocket"])

@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if token != MOCK_TOKEN:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    subscriber = alert_service.subscribe()
    try:
        await websocket.send_json({
            "type": "CONNECTION_STATE",
            "state": "CONNECTED",
            "alarm_state": alert_service.current_alarm_state(),
        })
        while True:
            message = await subscriber.get()
            await websocket.send_json(message)
            if message.get("event_id"):
                timing_log("T4", message["event_id"])
    except WebSocketDisconnect:
        pass
    finally:
        alert_service.unsubscribe(subscriber)