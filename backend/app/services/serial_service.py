import serial
import serial.tools.list_ports
import threading
import time
from typing import Optional, List
from app.core.logger import AppLogger
from app.core.config import settings
from app.core.events import event_bus

class SerialService:
    def __init__(self):
        self.port = settings.SERIAL_PORT
        self.baud_rate = settings.BAUD_RATE
        self.connection: Optional[serial.Serial] = None
        self._running = False
        self._read_thread: Optional[threading.Thread] = None

    @staticmethod
    def list_ports() -> List[str]:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, port: Optional[str] = None):
        if self.connection and getattr(self.connection, "is_open", False):
            return
        
        target_port = port or self.port
        if settings.MOCK_HARDWARE:
            AppLogger.log_sync("INFO", f"[MOCK] Connected to {target_port} at {self.baud_rate} baud")
            self.connection = "MOCK" # type: ignore
            self._running = True
            return

        try:
            self.connection = serial.Serial(target_port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to complete hardware reset after serial open
            self.port = target_port
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            AppLogger.log_sync("INFO", f"Connected to Arduino on {target_port} at {self.baud_rate} baud")
        except Exception as e:
            AppLogger.log_sync("ERROR", f"Failed to connect to {target_port}: {e}")
            raise

    def disconnect(self):
        self._running = False
        if self.connection and self.connection != "MOCK":
            if getattr(self.connection, "is_open", False):
                self.connection.close() # type: ignore
        self.connection = None
        AppLogger.log_sync("INFO", "Disconnected from Serial")

    def send_command(self, cmd: str):
        # Fire websocket events for conveyor control so UI stays in sync even without hardware
        if cmd == "START":
            event_bus.publish_threadsafe("conveyor_started", {})
        elif cmd == "STOP":
            event_bus.publish_threadsafe("conveyor_stopped", {})

        if not self.connection:
            AppLogger.log_sync("WARNING", f"Attempted to send command '{cmd}' without serial connection")
            return
        
        AppLogger.log_sync("INFO", f"send data to arduino: {cmd}")

        if self.connection == "MOCK":
            return
            
        try:
            full_cmd = f"{cmd}\n".encode('utf-8')
            self.connection.write(full_cmd) # type: ignore
        except Exception as e:
            AppLogger.log_sync("ERROR", f"Failed to send command {cmd}: {e}")

    def send_servo_command(self, index: int, angle: int):
        """Sends a servo command in the format expected by the custom Arduino firmware: 'index angle'"""
        # Format: "1 90" where 1 is index and 90 is angle
        cmd = f"{index} {angle}"
        self.send_command(cmd)

    def _read_loop(self):
        while self._running and self.connection and self.connection != "MOCK":
            try:
                if getattr(self.connection, "in_waiting", 0) > 0:
                    line = self.connection.readline().decode('utf-8').strip() # type: ignore
                    if line:
                        AppLogger.log_sync("INFO", f"Serial Receive: {line}")
                        # Could emit events for ACKs or trigers here
            except Exception as e:
                AppLogger.log_sync("ERROR", f"Serial Read Error: {e}")
                time.sleep(1)

# Global instance
serial_service = SerialService()
