"""
vision_engine.py
----------------
QR-based vision engine for robotic conveyor sorting.
Integrated with Convoyer Backend.
"""

import cv2
import numpy as np
import time
import urllib.request
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from collections import OrderedDict
import threading
from app.core.logger import AppLogger

# Use the existing AppLogger instead of creating a new one
# ─────────────────────────────────────────────────────────────────────────────
SORT_LEFT  = "SORT_LEFT"
SORT_RIGHT = "SORT_RIGHT"
COOLDOWN_S = 1.5          # seconds between valid scans
MAX_TRACKED_OBJECTS = 32  # centroid tracker capacity
TRACKER_DISAPPEARED_LIMIT = 30  # frames before an object is deregistered
ROI_PADDING = 0.20        # 20 % padding around detected bounding box
SCAN_SCALES = [1.0, 1.5, 2.0, 0.75]   # multi-scale factors for ROI
GLOBAL_SCAN_COOLDOWN = 10.0 # seconds to wait after a successful scan

WECHAT_MODEL_URLS: Dict[str, str] = {
    "detect.prototxt":   "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/detect.prototxt",
    "detect.caffemodel": "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/detect.caffemodel",
    "sr.prototxt":       "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/sr.prototxt",
    "sr.caffemodel":     "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/sr.caffemodel",
}

# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TrackedObject:
    object_id: int
    centroid: np.ndarray          # (x, y)
    bbox: Optional[Tuple]         # (x, y, w, h)
    disappeared: int = 0
    scan_attempts: int = 0
    last_qr_data: Optional[str] = None
    last_scan_ts: float = field(default_factory=lambda: 0.0)

@dataclass
class SortDecision:
    object_id: int
    qr_data: str
    action: str          # SORT_LEFT | SORT_RIGHT
    confidence: float
    timestamp: float
    bbox: Optional[Tuple]

# ─────────────────────────────────────────────────────────────────────────────
# Model download helper
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_wechat_models(model_dir: Path) -> bool:
    """Download WeChat QR models if not already cached. Returns True on success."""
    model_dir.mkdir(parents=True, exist_ok=True)
    all_ok = True
    for fname, url in WECHAT_MODEL_URLS.items():
        dest = model_dir / fname
        if dest.exists():
            continue
        AppLogger.log_sync("INFO", f"Downloading WeChat model: {fname} …")
        try:
            urllib.request.urlretrieve(url, dest)
            AppLogger.log_sync("INFO", f"  ✓ {fname}")
        except Exception as exc:
            AppLogger.log_sync("WARNING", f"  ✗ Failed to download {fname}: {exc}")
            all_ok = False
    return all_ok

# ─────────────────────────────────────────────────────────────────────────────
# Detector factory
# ─────────────────────────────────────────────────────────────────────────────
def _build_detector(model_dir: Path):
    """Return (detector, detector_name) tuple."""
    if _ensure_wechat_models(model_dir):
        try:
            # Check for different attribute names based on OpenCV version
            if hasattr(cv2, 'wechat_qrcode') and hasattr(cv2.wechat_qrcode, 'WeChatQRCode'):
                det = cv2.wechat_qrcode.WeChatQRCode(
                    str(model_dir / "detect.prototxt"),
                    str(model_dir / "detect.caffemodel"),
                    str(model_dir / "sr.prototxt"),
                    str(model_dir / "sr.caffemodel"),
                )
                AppLogger.log_sync("INFO", "QR detector → WeChat Engine Initialized")
                return det, "wechat"
        except Exception as exc:
            AppLogger.log_sync("WARNING", f"WeChat Engine init error: {exc}")

    # Fallback
    try:
        det = cv2.QRCodeDetectorAruco()
        AppLogger.log_sync("INFO", "QR detector → Aruco (Fallback)")
        return det, "aruco"
    except AttributeError:
        det = cv2.QRCodeDetector()
        AppLogger.log_sync("INFO", "QR detector → Standard OpenCV (Legacy)")
        return det, "legacy"

# ─────────────────────────────────────────────────────────────────────────────
# Centroid Tracker
# ─────────────────────────────────────────────────────────────────────────────
class CentroidTracker:
    def __init__(self, max_disappeared: int = TRACKER_DISAPPEARED_LIMIT):
        self.next_id = 0
        self.objects: OrderedDict[int, TrackedObject] = OrderedDict()
        self.max_disappeared = max_disappeared

    def _centroid(self, bbox: Tuple) -> np.ndarray:
        x, y, w, h = bbox
        return np.array([x + w / 2, y + h / 2], dtype="float")

    def register(self, bbox: Tuple) -> int:
        oid = self.next_id
        c   = self._centroid(bbox)
        self.objects[oid] = TrackedObject(object_id=oid, centroid=c, bbox=bbox)
        self.next_id += 1
        return oid

    def deregister(self, oid: int):
        del self.objects[oid]

    def update(self, bboxes: List[Tuple]) -> OrderedDict:
        if not bboxes:
            for oid in list(self.objects):
                self.objects[oid].disappeared += 1
                if self.objects[oid].disappeared > self.max_disappeared:
                    self.deregister(oid)
            return self.objects

        input_centroids = np.array([self._centroid(b) for b in bboxes])

        if not self.objects:
            for bb in bboxes:
                self.register(bb)
        else:
            obj_ids      = list(self.objects.keys())
            obj_cents    = np.array([o.centroid for o in self.objects.values()])
            D = np.linalg.norm(obj_cents[:, None] - input_centroids[None, :], axis=2)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            used_rows, used_cols = set(), set()
            for r, c in zip(rows, cols):
                if r in used_rows or c in used_cols:
                    continue
                oid = obj_ids[r]
                self.objects[oid].centroid    = input_centroids[c]
                self.objects[oid].bbox        = bboxes[c]
                self.objects[oid].disappeared = 0
                used_rows.add(r)
                used_cols.add(c)
            unused_rows = set(range(len(obj_ids))) - used_rows
            unused_cols = set(range(len(input_centroids))) - used_cols
            for r in unused_rows:
                oid = obj_ids[r]
                self.objects[oid].disappeared += 1
                if self.objects[oid].disappeared > self.max_disappeared:
                    self.deregister(oid)
            for c in unused_cols:
                self.register(bboxes[c])
        return self.objects

# ─────────────────────────────────────────────────────────────────────────────
# ROI Pipeline
# ─────────────────────────────────────────────────────────────────────────────
class ROIPipeline:
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def extract(self, frame: np.ndarray, bbox: Tuple, padding: float = ROI_PADDING) -> Optional[np.ndarray]:
        h, w = frame.shape[:2]
        x, y, bw, bh = [int(v) for v in bbox]
        pad_x = int(bw * padding)
        pad_y = int(bh * padding)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + bw + pad_x)
        y2 = min(h, y + bh + pad_y)
        roi = frame[y1:y2, x1:x2]
        return roi if roi.size > 0 else None

    def enhance(self, roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
        enhanced = self.clahe.apply(gray)
        return enhanced

    def multi_scale(self, roi: np.ndarray, scales: List[float] = SCAN_SCALES) -> List[np.ndarray]:
        enhanced = self.enhance(roi)
        variants = []
        h, w = enhanced.shape[:2]
        for s in scales:
            new_w, new_h = max(1, int(w * s)), max(1, int(h * s))
            resized = cv2.resize(enhanced, (new_w, new_h),
                                 interpolation=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA)
            variants.append(resized)
        return variants

# ─────────────────────────────────────────────────────────────────────────────
# QR Decode helper
# ─────────────────────────────────────────────────────────────────────────────
def _decode(detector, img: np.ndarray, detector_name: str) -> Tuple[List[str], List[np.ndarray]]:
    try:
        if detector_name == "wechat":
            texts, pts = detector.detectAndDecode(img)
            return list(texts), list(pts) if pts else []
        elif detector_name in ("aruco", "legacy"):
            data, pts, _ = detector.detectAndDecode(img)
            if data:
                return [data], [pts] if pts is not None else []
    except Exception:
        pass
    return [], []

# ─────────────────────────────────────────────────────────────────────────────
# Motion Detection
# ─────────────────────────────────────────────────────────────────────────────
class MotionDetector:
    def __init__(self):
        self.bgsub = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=40, detectShadows=False)
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def detect_bboxes(self, frame: np.ndarray, min_area: int = 2000) -> List[Tuple]:
        mask = self.bgsub.apply(frame)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel, iterations=3)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in cnts:
            if cv2.contourArea(c) >= min_area:
                boxes.append(cv2.boundingRect(c))
        return boxes

# ─────────────────────────────────────────────────────────────────────────────
# Main Vision Engine
# ─────────────────────────────────────────────────────────────────────────────
class QRVisionEngine:
    def __init__(self, decision_engine=None, event_bus=None, model_dir: str = "app/vision/models", min_object_area: int = 2000):
        self.decision_engine = decision_engine
        self.event_bus       = event_bus
        self.model_dir       = Path(model_dir)

        self.detector, self.detector_name = _build_detector(self.model_dir)
        self.roi_pipeline  = ROIPipeline()
        self.motion_det    = MotionDetector()
        self.tracker       = CentroidTracker()

        self._cooldowns: Dict[int, float] = {}
        self._last_success_ts = 0.0
        self._lock   = threading.Lock()
        self.min_object_area = min_object_area

    def process_frame(self, frame: np.ndarray) -> List[SortDecision]:
        # Block scanning if the robotic arm is busy executing a sequence
        if self.decision_engine and self.decision_engine.is_busy:
            return []

        decisions: List[SortDecision] = []
        bboxes = self.motion_det.detect_bboxes(frame, self.min_object_area)

        with self._lock:
            tracked = self.tracker.update(bboxes)

        for oid, obj in list(tracked.items()):
            if obj.bbox is None:
                continue

            now = time.time()
            if now - self._cooldowns.get(oid, 0.0) < COOLDOWN_S:
                continue
                
            # Global cooldown check: only scan if 10s passed since last success
            if now - self._last_success_ts < GLOBAL_SCAN_COOLDOWN:
                continue

            obj.scan_attempts += 1
            qr_data, confidence = self._scan_object(frame, obj)

            if qr_data:
                action = self._resolve_action(qr_data)
                decision = SortDecision(
                    object_id=oid,
                    qr_data=qr_data,
                    action=action,
                    confidence=confidence,
                    timestamp=now,
                    bbox=obj.bbox,
                )
                obj.last_qr_data = qr_data
                obj.last_scan_ts = now
                self._cooldowns[oid] = now
                self._last_success_ts = now  # Trigger global cooldown

                decisions.append(decision)
                self._dispatch(decision)

        return decisions

    def _scan_object(self, frame: np.ndarray, obj: TrackedObject) -> Tuple[Optional[str], float]:
        roi = self.roi_pipeline.extract(frame, obj.bbox)
        if roi is None:
            return None, 0.0

        variants = self.roi_pipeline.multi_scale(roi)
        for idx, variant in enumerate(variants):
            img3 = cv2.cvtColor(variant, cv2.COLOR_GRAY2BGR) if variant.ndim == 2 else variant
            texts, pts = _decode(self.detector, img3, self.detector_name)
            for text in texts:
                if text and text.strip():
                    conf = 1.0 - (idx * 0.1)
                    return text.strip(), round(conf, 2)
        return None, 0.0

    @staticmethod
    def _resolve_action(qr_data: str) -> str:
        return SORT_LEFT if "A" in qr_data.upper() else SORT_RIGHT

    def _dispatch(self, decision: SortDecision):
        payload: Dict[str, Any] = {
            "object_id": f"obj_{decision.object_id}",
            "qr_data":   decision.qr_data,
            "action":    decision.action,
            "confidence": decision.confidence,
            "timestamp": decision.timestamp,
            "bbox":      decision.bbox,
        }
        if self.decision_engine is not None:
            self.decision_engine.process_object(payload)
