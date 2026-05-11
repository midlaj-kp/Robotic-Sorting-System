from pydantic import BaseModel
from typing import Optional, Dict, Any

class ObjectDetectionResult(BaseModel):
    id: str
    timestamp: str
    qr_data: Optional[str] = None
    category: str = "A" # A, B, ERROR, REJECT
    deformity_status: bool = False
    confidence_score: float = 0.0
    sorting_decision: str = "A" # A, B, REJECT, ERROR

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ActionCommand(BaseModel):
    action: str
    payload: Optional[Dict[str, Any]] = None
