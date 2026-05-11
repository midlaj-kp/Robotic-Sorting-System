"""
test_standalone.py
------------------
Standalone entry point for testing the QR vision engine.
Based on the provided main.py.
"""

import argparse
import logging
import signal
import sys
import time
from app.vision.vision_engine import QRVisionEngine

# Stub implementations for standalone testing
class StubDecisionEngine:
    def process_object(self, payload):
        logging.info(f"TEST STUB: Decision for {payload.get('object_id')} -> {payload.get('action')} (QR: {payload.get('qr_data')})")

class StubEventBus:
    def publish_threadsafe(self, event, payload):
        logging.info(f"TEST STUB: Event '{event}' emitted.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("standalone_test")

def main():
    parser = argparse.ArgumentParser(description="Standalone QR Vision Test")
    parser.add_argument("--source",    default=0,
                        help="Camera index (int) or video file path")
    parser.add_argument("--model-dir", default="app/vision/models",
                        help="Directory for WeChat QR neural-network models")
    parser.add_argument("--min-area",  type=int, default=2000,
                        help="Minimum contour area (px²) to track as an object")
    args = parser.parse_args()

    # Coerce source to int if it looks like a camera index
    source = args.source
    try:
        source = int(source)
    except (ValueError, TypeError):
        pass

    decision_engine = StubDecisionEngine()
    event_bus       = StubEventBus()

    engine = QRVisionEngine(
        decision_engine = decision_engine,
        event_bus       = event_bus,
        model_dir       = args.model_dir,
        min_object_area = args.min_area,
    )

    def _shutdown(sig, frame):
        logger.info("Shutdown signal received – stopping engine …")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Starting standalone QR test (source=%s)", source)
    engine.start(source=source)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
