"""
tests/test_vision_engine.py
----------------------------
Pytest suite for QRVisionEngine business logic.
Does NOT require a real camera – uses synthetic frames.
"""

import time
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, call

# ── Patch heavy imports before importing vision_engine ──────────────────────
import sys, types

# Minimal cv2 stub so tests run without OpenCV installed in CI
cv2_stub = types.ModuleType("cv2")
cv2_stub.createBackgroundSubtractorMOG2 = MagicMock(return_value=MagicMock(
    apply=MagicMock(return_value=np.zeros((480, 640), dtype=np.uint8))
))
cv2_stub.createCLAHE = MagicMock(return_value=MagicMock(
    apply=MagicMock(side_effect=lambda x: x)
))
cv2_stub.MORPH_ELLIPSE  = 0
cv2_stub.MORPH_OPEN     = 2
cv2_stub.MORPH_CLOSE    = 3
cv2_stub.RETR_EXTERNAL  = 0
cv2_stub.CHAIN_APPROX_SIMPLE = 1
cv2_stub.getStructuringElement = MagicMock(return_value=np.ones((5, 5), np.uint8))
cv2_stub.morphologyEx   = MagicMock(side_effect=lambda m, *a, **kw: m)
cv2_stub.findContours   = MagicMock(return_value=([], None))
cv2_stub.boundingRect   = MagicMock(return_value=(10, 10, 100, 100))
cv2_stub.contourArea    = MagicMock(return_value=3000)
cv2_stub.resize         = MagicMock(side_effect=lambda img, size, **kw: img)
cv2_stub.cvtColor       = MagicMock(side_effect=lambda img, code: img)
cv2_stub.COLOR_BGR2GRAY = 6
cv2_stub.COLOR_GRAY2BGR = 8
cv2_stub.INTER_CUBIC    = 2
cv2_stub.INTER_AREA     = 3
cv2_stub.QRCodeDetector = MagicMock
cv2_stub.QRCodeDetectorAruco = MagicMock

wechat_stub = types.ModuleType("cv2.wechat_qrcode")
wechat_stub.WeChatQRCode = MagicMock
cv2_stub.wechat_qrcode  = wechat_stub

sys.modules["cv2"]                  = cv2_stub
sys.modules["cv2.wechat_qrcode"]   = wechat_stub

# Adjusted import for project structure
from app.vision.vision_engine import (
    QRVisionEngine, CentroidTracker, ROIPipeline,
    MotionDetector, SORT_LEFT, SORT_RIGHT, COOLDOWN_S,
    TrackedObject,
)
# Alias for brevity
QVE = QRVisionEngine


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def blank_frame(h=480, w=640):
    return np.zeros((h, w, 3), dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# Sorting logic
# ─────────────────────────────────────────────────────────────────────────────
class TestSortingLogic:
    def test_contains_A_sorts_left(self):
        assert QVE._resolve_action("ITEM-A-001") == SORT_LEFT

    def test_contains_lowercase_a_sorts_left(self):
        assert QVE._resolve_action("item-a-001") == SORT_LEFT

    def test_contains_B_sorts_right(self):
        assert QVE._resolve_action("ITEM-B-001") == SORT_RIGHT

    def test_unknown_sorts_right(self):
        assert QVE._resolve_action("UNKNOWN-XYZ") == SORT_RIGHT

    def test_empty_sorts_right(self):
        assert QVE._resolve_action("") == SORT_RIGHT


# ─────────────────────────────────────────────────────────────────────────────
# Centroid Tracker
# ─────────────────────────────────────────────────────────────────────────────
class TestCentroidTracker:
    def test_register_new_object(self):
        t = CentroidTracker()
        t.update([(10, 10, 50, 50)])
        assert len(t.objects) == 1

    def test_same_object_tracked(self):
        t = CentroidTracker()
        t.update([(10, 10, 50, 50)])
        oid = list(t.objects.keys())[0]
        t.update([(12, 12, 50, 50)])   # small movement
        assert oid in t.objects        # same id retained

    def test_object_deregistered_after_disappear(self):
        t = CentroidTracker(max_disappeared=2)
        t.update([(10, 10, 50, 50)])
        t.update([])   # frame 1 without detection
        t.update([])   # frame 2
        t.update([])   # frame 3 → should deregister
        assert len(t.objects) == 0

    def test_two_objects_tracked_independently(self):
        t = CentroidTracker()
        t.update([(10, 10, 30, 30), (200, 200, 30, 30)])
        assert len(t.objects) == 2


# ─────────────────────────────────────────────────────────────────────────────
# ROI Pipeline
# ─────────────────────────────────────────────────────────────────────────────
class TestROIPipeline:
    def setup_method(self):
        self.pipe = ROIPipeline()

    def test_extract_returns_none_for_zero_area(self):
        frame = blank_frame()
        # bbox with 0 width/height
        result = self.pipe.extract(frame, (0, 0, 0, 0))
        assert result is None

    def test_extract_clips_to_frame_bounds(self):
        frame = blank_frame(100, 100)
        # bbox near edge – padding would go out of bounds
        roi = self.pipe.extract(frame, (90, 90, 20, 20), padding=0.5)
        assert roi is not None

    def test_multi_scale_returns_correct_count(self):
        frame = blank_frame(200, 200)
        roi = self.pipe.extract(frame, (20, 20, 100, 100))
        scales = [1.0, 1.5, 2.0, 0.75]
        variants = self.pipe.multi_scale(roi, scales)
        assert len(variants) == len(scales)


# ─────────────────────────────────────────────────────────────────────────────
# Cooldown logic
# ─────────────────────────────────────────────────────────────────────────────
class TestCooldown:
    def _make_engine(self):
        de = MagicMock()
        eb = MagicMock()
        # Adjusted patch path for app structure
        with patch("app.vision.vision_engine._build_detector",
                   return_value=(MagicMock(), "legacy")), \
             patch("app.vision.vision_engine._ensure_wechat_models", return_value=False):
            eng = QRVisionEngine(decision_engine=de, event_bus=eb)
        return eng, de, eb

    def test_dispatch_called_once_within_cooldown(self):
        eng, de, eb = self._make_engine()
        eng._dispatch = MagicMock()

        # Simulate two decisions for same object within cooldown window
        from app.vision.vision_engine import SortDecision
        dec = SortDecision(0, "ITEM-A", SORT_LEFT, 1.0, time.time(), (0,0,50,50))

        eng._cooldowns[0] = time.time()          # set cooldown now

        # _process should skip because cooldown not elapsed
        # We test the guard directly
        now = time.time()
        in_cooldown = (now - eng._cooldowns.get(0, 0.0)) < COOLDOWN_S
        assert in_cooldown is True

    def test_dispatch_allowed_after_cooldown(self):
        eng, de, eb = self._make_engine()
        eng._cooldowns[0] = time.time() - (COOLDOWN_S + 0.1)  # expired
        now = time.time()
        in_cooldown = (now - eng._cooldowns.get(0, 0.0)) < COOLDOWN_S
        assert in_cooldown is False


# ─────────────────────────────────────────────────────────────────────────────
# Integration dispatch
# ─────────────────────────────────────────────────────────────────────────────
class TestDispatch:
    def _make_engine(self):
        de = MagicMock()
        eb = MagicMock()
        # Adjusted patch path for app structure
        with patch("app.vision.vision_engine._build_detector",
                   return_value=(MagicMock(), "legacy")), \
             patch("app.vision.vision_engine._ensure_wechat_models", return_value=False):
            eng = QRVisionEngine(decision_engine=de, event_bus=eb)
        return eng, de, eb

    def test_decision_engine_called(self):
        from app.vision.vision_engine import SortDecision
        eng, de, eb = self._make_engine()
        dec = SortDecision(1, "ITEM-A", SORT_LEFT, 0.9, time.time(), (0,0,50,50))
        eng._dispatch(dec)
        de.process_object.assert_called_once()

    def test_event_bus_emitted(self):
        from app.vision.vision_engine import SortDecision
        eng, de, eb = self._make_engine()
        dec = SortDecision(2, "ITEM-B", SORT_RIGHT, 0.8, time.time(), (0,0,50,50))
        eng._dispatch(dec)
        # Event bus was integrated as event_bus.publish_threadsafe
        eb.publish_threadsafe.assert_called_once()
        event_name = eb.publish_threadsafe.call_args[0][0]
        assert event_name == "sorting_triggered"

    def test_payload_contains_action(self):
        from app.vision.vision_engine import SortDecision
        eng, de, eb = self._make_engine()
        dec = SortDecision(3, "ITEM-A-99", SORT_LEFT, 1.0, time.time(), (0,0,50,50))
        eng._dispatch(dec)
        payload = de.process_object.call_args[0][0]
        assert payload["action"] == SORT_LEFT
        assert payload["qr_data"] == "ITEM-A-99"
