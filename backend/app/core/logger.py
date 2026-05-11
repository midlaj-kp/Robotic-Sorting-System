import logging
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any
from app.core.events import event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sortmate_backend")

class AppLogger:
    @staticmethod
    async def log(level: str, message: str, details: Optional[Dict[str, Any]] = None):
        """ Used by async methods """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "details": details or {}
        }
        if level == "INFO":
            logger.info(f"{message} - {details if details else ''}")
        elif level == "WARNING":
            logger.warning(f"{message} - {details if details else ''}")
        elif level == "ERROR":
            logger.error(f"{message} - {details if details else ''}")
        
        # Filter out high-frequency raw serial data from the UI log
        if "Serial Send:" in message or "Executing robotic sequence" in message:
            return

        try:
            await event_bus.publish("log_update", log_entry)
        except Exception:
            pass

    @staticmethod
    def log_sync(level: str, message: str, details: Optional[Dict[str, Any]] = None):
        """ Used by synchronous threads (hardware / camera loops) to push events to the main thread's event loop. """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "details": details or {}
        }
        if level == "INFO":
            logger.info(f"{message} - {details if details else ''}")
        elif level == "WARNING":
            logger.warning(f"{message} - {details if details else ''}")
        elif level == "ERROR":
            logger.error(f"{message} - {details if details else ''}")
            
        # Filter out high-frequency raw serial data from the UI log
        if "Serial Send:" in message or "Executing robotic sequence" in message:
            return

        try:
            event_bus.publish_threadsafe("log_update", log_entry)
        except Exception:
            pass
