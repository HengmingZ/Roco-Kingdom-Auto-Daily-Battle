"""Unit test for inference pipeline.
"""

from __future__ import annotations

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capture.screen_grabber import ScreenGrabber
from inference.predictor import SkillPredictor


def test_inference_pipeline() -> None:
    print("[Test] Initializing SkillPredictor...")
    predictor = SkillPredictor()
    grabber = ScreenGrabber()
    print("[Test] Capturing primary screen for inference...")
    screen = grabber.capture_primary_screen()
    print("[Test] Running prediction pipeline...")
    state = predictor.predict(screen)
    print(f"[Test] Prediction successful! Detected {len(state.slots)} skill slots.")
    for s in state.slots:
        print(f"       - Slot {s.slot_id}: {s.name} (BBox: {s.bbox}, Usable: {s.is_usable})")


if __name__ == "__main__":
    test_inference_pipeline()
