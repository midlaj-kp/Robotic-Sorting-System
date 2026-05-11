import asyncio
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logger import AppLogger
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        AppLogger.log_sync("INFO", f"New client connected. Total: {len(self.active_connections)}")
        
        # Send initial state to newly connected client
        from app.services.camera_pipeline import camera_pipeline
        from app.services.arm_service import arm_service
        
        initial_state = {
            "event": "system_state",
            "data": {
                "conveyor_running": camera_pipeline._running, # Using camera_pipeline running as proxy for conveyor state if needed
                "arm_busy": arm_service.is_busy
            }
        }
        await websocket.send_text(json.dumps(initial_state))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        AppLogger.log_sync("INFO", f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Create a list of connections to send to, to avoid issues with disconnections during iteration
        connections = self.active_connections[:]
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # If sending fails, assume the client has disconnected and remove them.
                self.disconnect(connection)

manager = ConnectionManager()

# This listener is the bridge between backend events and the frontend
async def websocket_event_listener():
    from app.core.events import event_bus
    AppLogger.log_sync("INFO", "WebSocket event listener started.")
    while True:
        try:
            event = await event_bus.get()
            if event:
                await manager.broadcast(event)
        except asyncio.CancelledError:
            AppLogger.log_sync("INFO", "WebSocket event listener is shutting down.")
            break
        except Exception as e:
            AppLogger.log_sync("ERROR", f"Error in WebSocket event listener: {e}")
            await asyncio.sleep(1)
