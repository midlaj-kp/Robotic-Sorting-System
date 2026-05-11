import os
from pydantic_settings import BaseSettings

import os

class Settings:
    APP_NAME: str = "Convoyer"
    
    # Hardware flags
    MOCK_HARDWARE: bool = os.getenv("MOCK_HARDWARE", "false").lower() in ("true", "1", "t")
    
    # Camera settings
    CAMERA_INDEX: int = 0
    TARGET_FPS: int = 30
    
    # Serial settings
    SERIAL_PORT: str = "COM3"
    BAUD_RATE: int = 9600
    
    # Simulation settings
    MOCK_ITEM_INTERVAL: float = 2.0 # seconds
    
    # Database
    DATABASE_URL: str = "sqlite:///./convoyer.db"

settings = Settings()
