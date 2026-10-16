import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.monitoring_service import MonitoringSession
import queue
import json

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/monitoring")
async def monitoring_ws(websocket: WebSocket):
    await websocket.accept()
    session = MonitoringSession(websocket)
    session.out_queue = queue.Queue(maxsize=1)

    # Task to read from backend queue and send to websocket
    async def send_updates():
        while True:
            try:
                # We need to use a non-blocking way or run in executor to not block async loop
                # For simplicity, we just use asyncio.sleep and queue.get_nowait()
                while True:
                    try:
                        message = session.out_queue.get_nowait()
                        await websocket.send_json(message)
                    except queue.Empty:
                        break
                await asyncio.sleep(0.01)
            except WebSocketDisconnect:
                break
            except Exception as e:
                print("Send error:", e)
                break

    sender_task = asyncio.create_task(send_updates())

    try:
        while True:
            message_data = await websocket.receive()
            
            if message_data.get("type") == "websocket.disconnect":
                break
                
            if "text" in message_data:
                try:
                    message = json.loads(message_data["text"])
                    msg_type = message.get("type")
                    
                    if msg_type == "start":
                        source = message.get("source")
                        if source in ["ip_camera", "rtsp", "video"]:
                            url = message.get("url") or message.get("path")
                            session.start_backend_capture(source, url)
                        elif source == "browser_webcam":
                            session.start_browser_session()
                    
                    elif msg_type == "stop":
                        session.stop()
                except json.JSONDecodeError:
                    pass
            elif "bytes" in message_data:
                # Browser webcam frame
                if session.source_type == "browser_webcam":
                    session.process_browser_frame(message_data["bytes"])
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
    finally:
        session.stop()
        sender_task.cancel()
