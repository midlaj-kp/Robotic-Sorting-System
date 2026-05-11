from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.db.database import Base
from datetime import datetime

class ObjectRecord(Base):
    __tablename__ = "object_records"

    id = Column(String, primary_key=True, index=True) # E.g., obj_123
    timestamp = Column(DateTime, default=datetime.utcnow)
    qr_data = Column(String, nullable=True)
    category = Column(String, index=True)
    deformity_status = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    sorting_decision = Column(String)

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String)
    message = Column(String)
    details = Column(String, nullable=True) # Stored as JSON string
