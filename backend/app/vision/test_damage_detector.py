"""
test_damage_detector.py
-----------------------
Independent test script for the AI Damage Detector component.
"""

import cv2
import numpy as np
import os
import sys

# Add the project root (backend) to path so we can import app
# dirname(__file__) is app/vision, so ../.. is backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.vision.damage_detector import damage_detector

def run_test():
    print("--- AI Damage Detector Standalone Test ---")
    
    # 1. Create a "Clean" frame
    clean_frame = np.zeros((300, 300, 3), dtype=np.uint8)
    clean_frame[:] = (200, 200, 200) # Light gray
    cv2.circle(clean_frame, (150, 150), 100, (100, 100, 100), -1) # Smooth circle
    
    # 2. Create a "Damaged" frame (with irregular lines/cracks)
    damaged_frame = clean_frame.copy()
    # Add some "cracks" (random lines)
    for _ in range(20):
        pt1 = (np.random.randint(50, 250), np.random.randint(50, 250))
        pt2 = (pt1[0] + np.random.randint(-20, 20), pt1[1] + np.random.randint(-20, 20))
        cv2.line(damaged_frame, pt1, pt2, (0, 0, 0), 2)
    
    # 3. Analyze Clean
    result_clean = damage_detector.analyze_surface(clean_frame)
    print(f"Clean Object Result: {result_clean['damaged']} (Conf: {result_clean['confidence']})")
    print(f"  Metadata: {result_clean.get('analysis_metadata')}")
    
    # 4. Analyze Damaged
    result_damaged = damage_detector.analyze_surface(damaged_frame)
    print(f"Damaged Object Result: {result_damaged['damaged']} (Conf: {result_damaged['confidence']})")
    print(f"  Metadata: {result_damaged.get('analysis_metadata')}")
    
    # 5. Verify
    if not result_clean['damaged'] and result_damaged['damaged']:
        print("\nSUCCESS: Damage detector correctly identified the difference!")
    else:
        print("\nFAILURE: Sensitivity might need adjustment.")

if __name__ == "__main__":
    run_test()
