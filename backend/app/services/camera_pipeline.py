import cv2
import threading
import time
import numpy as np
import platform
import asyncio
from app.core.config import settings
from app.core.logger import AppLogger
from app.services.decision_engine import decision_engine
from app.vision.vision_engine import QRVisionEngine
from app.core.events import event_bus
import asyncio

class CameraPipeline:
    def __init__(self):
        self.camera_index = settings.CAMERA_INDEX
        self.target_fps = settings.TARGET_FPS
        self.cap = None
        self._running = False
        self._capture_thread = None
        self._process_thread = None
        self.latest_frame_bytes = None
        self.latest_raw_frame = None
        self._use_mock_mode = settings.MOCK_HARDWARE
        
        # New Vision Engine
        self.engine = QRVisionEngine(
            decision_engine=decision_engine,
            event_bus=event_bus
        )

    def start(self):
        if self._running:
            return
            
        self._use_mock_mode = settings.MOCK_HARDWARE
        self._running = True
        
        if not self._use_mock_mode:
            # Try to open camera with auto-detection fallback
            self.cap = self._open_camera()
            if self.cap is None:
                AppLogger.log_sync("ERROR", "Failed to open camera.")
            
            # Configure camera settings
            if self.cap is not None:
                try:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap.set(cv2.CAP_PROP_FPS, 20) # Lower FPS for background processing
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                except Exception as e:
                    AppLogger.log_sync("WARNING", f"Could not set camera properties: {e}")

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._capture_thread.start()
        self._process_thread.start()
        AppLogger.log_sync("INFO", "✓ Camera and Vision engines started")

    def _open_camera(self):
        """Try to open camera with auto-fallback"""
        # Deduplicate while preserving priority order
        seen = set()
        indices_to_try = []
        for i in [self.camera_index] + list(range(5)):
            if i not in seen:
                seen.add(i)
                indices_to_try.append(i)
        
        backends = [(-1, "Default")]
        if platform.system() == "Windows":
            backends = [(cv2.CAP_DSHOW, "DirectShow"), (cv2.CAP_MSMF, "MSMF")] + backends
        
        for backend_id, backend_name in backends:
            for idx in indices_to_try:
                try:
                    cap = cv2.VideoCapture(idx, backend_id) if backend_id != -1 else cv2.VideoCapture(idx)
                    if not cap.isOpened():
                        cap.release()
                        continue
                    # Some cameras need a few warmup frames before returning valid data
                    for _ in range(5):
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            AppLogger.log_sync("INFO", f"✓ Camera opened: Index {idx} ({backend_name})")
                            return cap
                        time.sleep(0.05)
                    AppLogger.log_sync("WARNING", f"Camera index {idx} ({backend_name}) opened but returned no frames, skipping.")
                    cap.release()
                except Exception as e:
                    AppLogger.log_sync("WARNING", f"Camera index {idx} ({backend_name}) error: {e}")
        AppLogger.log_sync("ERROR", "All camera indices exhausted — no usable camera found.")
        return None

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        AppLogger.log_sync("INFO", "Camera feedback stopped")

    def get_frame_stream(self):
        """MJPEG generator for video feed. Runs in threadpool via StreamingResponse."""
        last_bytes = None
        yield b"--frame\r\n"
        while self._running:
            frame = self.latest_frame_bytes
            if frame is not None and frame is not last_bytes:
                last_bytes = frame
                yield (b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n')
            else:
                time.sleep(0.01)

    def _capture_loop(self):
        """Dedicated loop to pull frames without lag."""
        consecutive_failures = 0
        while self._running:
            if self.cap and self.cap.isOpened() and not self._use_mock_mode:
                try:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        consecutive_failures = 0
                        self.latest_raw_frame = frame.copy()
                        ret, encoded_img = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                        if ret:
                            self.latest_frame_bytes = encoded_img.tobytes()
                    else:
                        consecutive_failures += 1
                        self._set_error_frame("Camera Stream Lost")
                        time.sleep(0.05)
                        # After 20 consecutive failures (~1s), try to reopen the camera
                        if consecutive_failures >= 20:
                            AppLogger.log_sync("WARNING", "Camera stream lost — attempting to reopen...")
                            self.cap.release()
                            self.cap = self._open_camera()
                            consecutive_failures = 0
                except Exception as e:
                    self._set_error_frame(f"Camera Error: {str(e)[:20]}")
                    time.sleep(0.1)
            elif self._use_mock_mode:
                # Generate a mock frame
                mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                mock_frame[:] = (30, 30, 30)
                cv2.putText(mock_frame, "MOCK CAMERA ACTIVE", (150, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2, cv2.LINE_AA)
                ret, encoded_img = cv2.imencode('.jpg', mock_frame)
                if ret:
                    self.latest_frame_bytes = encoded_img.tobytes()
                time.sleep(0.1)
            else:
                # Not mock mode and camera failed to open — retry periodically
                self._set_error_frame("No Camera Detected")
                time.sleep(2.0)
                AppLogger.log_sync("INFO", "Retrying camera open...")
                self.cap = self._open_camera()

    def _process_loop(self):
        """Processes frames using the new QRVisionEngine"""
        target_fps = 10
        frame_time = 1.0 / target_fps
        
        while self._running:
            start_time = time.time()
            frame = self.latest_raw_frame
            
            if frame is not None and not self._use_mock_mode:
                try:
                    # Offload all logic to the new engine
                    self.engine.process_frame(frame)
                except Exception as e:
                    AppLogger.log_sync("ERROR", f"Vision Engine error: {e}")

            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)

    def _set_error_frame(self, message: str):
        """Generates a black frame with an error message."""
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, message, (180, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        ret, encoded_img = cv2.imencode('.jpg', error_frame)
        if ret:
            self.latest_frame_bytes = encoded_img.tobytes()

camera_pipeline = CameraPipeline()
