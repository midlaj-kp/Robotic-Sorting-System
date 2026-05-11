import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.serial_service import serial_service
from app.services.arm_service import arm_service
from app.services.camera_pipeline import camera_pipeline
from typing import List, Optional

router = APIRouter()

@router.get("/ports", response_model=List[str])
async def get_ports():
    return serial_service.list_ports()

@router.post("/connect")
async def connect_serial(port: Optional[str] = None):
    try:
        # Run blocking connect (includes 2s Arduino boot wait) in a thread
        # so it doesn't freeze the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: serial_service.connect(port))
        # Schedule rest pose as a proper async task (we're already on the event loop)
        asyncio.create_task(arm_service._execute_rest_async())
        return {"status": "success", "message": "Connected to serial port"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disconnect")
async def disconnect_serial():
    serial_service.disconnect()
    return {"status": "success", "message": "Disconnected from serial port"}

@router.post("/start")
async def start_pipeline():
    camera_pipeline.start()
    serial_service.send_command("START")
    return {"status": "success", "message": "Pipeline started"}

@router.post("/stop")
async def stop_pipeline():
    from app.services.decision_engine import decision_engine
    # We keep camera_pipeline running so the video feed doesn't break
    serial_service.send_command("STOP")
    decision_engine.reset_auto_start()
    return {"status": "success", "message": "Conveyor stopped, camera remains active"}

@router.get("/status")
async def get_status():
    return {
        "camera_running": camera_pipeline._running,
        "serial_connected": serial_service._running
    }

@router.get("/video_feed")
async def video_feed():
    if not camera_pipeline._running:
        # Try to auto-start if it's not running (resilience)
        try:
            camera_pipeline.start()
        except Exception:
            raise HTTPException(status_code=503, detail="Camera pipeline is not running and failed to auto-start")
            
    if not camera_pipeline._running:
        raise HTTPException(status_code=503, detail="Camera pipeline is not running or failed to initialize")
        
    return StreamingResponse(
        camera_pipeline.get_frame_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )

@router.get("/qr/latest")
async def get_latest_qr():
    """Get the latest detected QR data"""
    qr_data = camera_pipeline.get_latest_qr_data()
    return {
        "qr_data": qr_data,
        "detected": qr_data is not None,
        "timestamp": camera_pipeline.last_qr_timestamp
    }

@router.post("/qr/scan")
async def trigger_qr_scan():
    """Trigger immediate QR scan from current camera frame"""
    qr_data = camera_pipeline.scan_frame_for_qr()
    return {
        "found": qr_data is not None,
        "data": qr_data,
        "category": "A" if qr_data and "A" in qr_data.upper() else "B" if qr_data else None
    }
