from datetime import datetime
from app.models.schemas import ObjectDetectionResult
from app.services.serial_service import serial_service
from app.services.arm_service import arm_service
from app.core.logger import AppLogger
from app.core.events import event_bus
from app.db.database import SessionLocal
from app.db.models import ObjectRecord
import asyncio

class DecisionEngine:
    def __init__(self):
        self._conveyor_started = False

    @property
    def is_busy(self) -> bool:
        """Proxies to ArmService to check if hardware is busy"""
        return arm_service.is_busy

    def process_object(self, obj_id_or_payload, qr_data=None, is_deformed=False):
        """
        Decision rules:
         - Parses format: {Category, Material, Origin, Extra}
        """
        if isinstance(obj_id_or_payload, dict):
            payload = obj_id_or_payload
            obj_id = payload.get("object_id")
            qr_data = payload.get("qr_data", "")
            confidence = payload.get("confidence", 1.0)
        else:
            obj_id = obj_id_or_payload
            confidence = 1.0

        # Smart Parsing
        clean_qr = qr_data.strip("{} ").upper()
        parts = [p.strip() for p in clean_qr.split(",")]
        
        primary_category = parts[0] if parts else ""
        material = parts[1] if len(parts) > 1 else "Unknown"
        origin = parts[2] if len(parts) > 2 else "Unknown"
        
        if not qr_data:
            decision = "NONE"
            category = "NO_QR"
        elif "FURNITURE" in clean_qr:
            decision = "REJECT"
            category = "DEFORMED" # Using deformed as placeholder for reject category
        elif "A" == primary_category or (len(parts) > 0 and primary_category.startswith("A")):
            decision = "SORT_LEFT"
            category = "A"
        else:
            decision = "SORT_RIGHT"
            category = "B"
                
        result = ObjectDetectionResult(
            id=str(obj_id),
            timestamp=datetime.utcnow().isoformat(),
            qr_data=qr_data,
            category=category,
            deformity_status=is_deformed,
            confidence_score=confidence,
            sorting_decision=decision
        )
        
        result_dict = result.dict()
        result_dict["material"] = material
        result_dict["origin"] = origin
        
        # Physical sorting via ArmService
        if decision == "SORT_LEFT":
            arm_service.run_sort_a()
        elif decision == "SORT_RIGHT":
            arm_service.run_sort_b()
        elif decision == "REJECT":
            arm_service.trigger_reject_cooldown()

        # Auto-start conveyor if it's the first detection
        if not self._conveyor_started:
            self._auto_start_conveyor()
            event_bus.publish_threadsafe("conveyor_started", {"status": "running"})
            
        AppLogger.log_sync("INFO", f"Decision Engine output: {result.json()}")
        event_bus.publish_threadsafe("sorting_triggered", result_dict)
    
    def _auto_start_conveyor(self):
        """Automatically start conveyor when QR is first detected"""
        try:
            self._conveyor_started = True
            serial_service.send_command("START")
            AppLogger.log_sync("INFO", "Auto-started conveyor on QR detection")
        except Exception as e:
            AppLogger.log_sync("WARNING", f"Could not auto-start conveyor: {e}")
    
    def reset_auto_start(self):
        """Reset the auto-start flag when conveyor is stopped"""
        self._conveyor_started = False
        AppLogger.log_sync("INFO", "Reset auto-start flag")
        
    def _emit_and_save(self, result: ObjectDetectionResult):
        # Use thread-safe publish because this can be called from the camera's thread
        event_bus.publish_threadsafe("sorting_triggered", result.dict())
        
        # Also send command to physical device if not in mock mode
        db = None
        try:
            db = SessionLocal()
            record = ObjectRecord(
                id=result.id,
                qr_data=result.qr_data,
                category=result.category,
                deformity_status=result.deformity_status,
                confidence_score=result.confidence_score,
                sorting_decision=result.sorting_decision
            )
            # Use merge instead of add to safely handle primary key conflicts from past sessions
            db.merge(record)
            db.commit()
        except Exception as e:
            AppLogger.log_sync("ERROR", f"Failed to save record to DB: {e}")
        finally:
            if db:
                db.close()

decision_engine = DecisionEngine()
