from typing import AsyncGenerator
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.api.websockets import manager, websocket_event_listener
from app.core.config import settings
from app.core.events import event_bus
from app.core.logger import AppLogger
from app.db import database
from app.services.camera_pipeline import camera_pipeline
from app.services.serial_service import serial_service

# Create DB tables on import
database.Base.metadata.create_all(bind=database.engine)

# Store the background task to cancel it on shutdown
background_tasks = set()

@asynccontextmanager  # type: ignore
async def lifespan_manager(app: FastAPI):
    # --- Startup Logic ---
    AppLogger.log_sync("INFO", "Application startup...")
    
    # Register the event loop for thread-safe publishing
    loop = asyncio.get_running_loop()
    event_bus.register_loop(loop)
    
    # Start the websocket event listener
    listener_task = asyncio.create_task(websocket_event_listener())
    background_tasks.add(listener_task)
    
    # Start the camera pipeline
    camera_pipeline.start()
    
    AppLogger.log_sync("INFO", "✓ Application startup complete.")
    
    yield
    
    # --- Shutdown Logic ---
    AppLogger.log_sync("INFO", "Application shutdown...")
    
    # Stop services
    camera_pipeline.stop()
    serial_service.disconnect()
    
    # Cancel the background task
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            AppLogger.log_sync("INFO", "WebSocket listener task cancelled successfully.")

    AppLogger.log_sync("INFO", "✓ Application shutdown complete.")


# --- App Initialization ---
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan_manager)  # type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by waiting for data.
            # This can be a simple ping/pong or just waiting.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        AppLogger.log_sync("INFO", f"Client disconnected from WebSocket.")
#uvicorn app.main:app --reload