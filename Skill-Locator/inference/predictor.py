"""Main online inference predictor for Skill-Locator.

Loads ONNX model or weights and predicts skill states from full primary screen captures.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional, List, Dict, Any

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dataset.preprocessor import Preprocessor
from inference.schema import SkillSlot, BattleSkillsState
from inference.pp_recognizer import PPRecognizer


# [UPDATE - 2026-09-12]
# Reason: Integrate trained YOLO model for real-time skill detection.
# Modification: Loaded weights/best.pt via YOLO and extracted bounding boxes and confidence.


class SkillPredictor:
    """Predicts skill slots and states from full screen images using trained YOLO model."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        if model_path is None:
            model_path = os.path.join(PROJECT_ROOT, "weights", "best.pt")
        self.model_path = model_path
        self.model = None
        self._init_model()

    def _init_model(self) -> None:
        if os.path.exists(self.model_path):
            try:
                from ultralytics import YOLO

                self.model = YOLO(self.model_path)
            except Exception as e:
                print(f"[SkillPredictor] Error loading model: {e}")

    def predict(self, screen_image: Any, conf: float = 0.25) -> BattleSkillsState:
        """Process full screen image and return detected skill slots."""
        h, w = screen_image.shape[:2] if hasattr(screen_image, "shape") else (1080, 1920)
        slots_result: List[SkillSlot] = []

        if self.model is not None:
            results = self.model.predict(screen_image, conf=conf, verbose=False)
            if results and len(results) > 0:
                boxes = results[0].boxes
                for i in range(len(boxes)):
                    cid = int(boxes.cls[i].item())
                    score = float(boxes.conf[i].item())
                    xyxy = boxes.xyxy[i].cpu().numpy().astype(int)
                    slot = SkillSlot(
                        slot_id=cid + 1,
                        name=f"Skill_{cid + 1}",
                        confidence=round(score, 3),
                        bbox=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                    )
                    slots_result.append(slot)

        # Sort slots by slot_id (1 to 4)
        slots_result.sort(key=lambda s: s.slot_id)

        return BattleSkillsState(
            timestamp=time.time(),
            screen_resolution=(w, h),
            slots=slots_result,
        )
