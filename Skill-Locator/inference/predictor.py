"""Main online inference predictor for Skill-Locator.

Predicts skill states from full primary screen captures.
Prefers the ONNX export (onnxruntime, no PyTorch needed at runtime);
falls back to ultralytics/YOLO .pt weights when an ONNX file is absent
(development/training environments).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional, List, Dict, Any, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dataset.preprocessor import Preprocessor
from inference.schema import SkillSlot, BattleSkillsState
from inference.pp_recognizer import PPRecognizer


# [UPDATE - 2026-09-23]
# Reason: Ship a slim exe without the multi-GB PyTorch runtime.
# Modification: Run YOLO inference through onnxruntime on best.onnx
# (letterbox + per-class NMS replicating ultralytics defaults); keep the
# ultralytics .pt path as a dev fallback when no .onnx is present.


class _OnnxYolo:
    """Minimal YOLOv8 detector running on onnxruntime."""

    def __init__(self, onnx_path: str) -> None:
        import onnxruntime as ort

        providers = ort.get_available_providers()
        self.session = ort.InferenceSession(onnx_path, providers=providers)
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        # Model input is (1, 3, H, W)
        self.in_h, self.in_w = int(inp.shape[2]), int(inp.shape[3])

    def predict(self, image: Any, conf: float = 0.25, iou: float = 0.45) -> List[Tuple[int, float, Tuple[int, int, int, int]]]:
        """Return [(class_id, score, (x1, y1, x2, y2)), ...] in original-image pixels."""
        import cv2
        import numpy as np

        h0, w0 = image.shape[:2]
        scale = min(self.in_w / w0, self.in_h / h0)
        nw, nh = int(round(w0 * scale)), int(round(h0 * scale))
        pad_w, pad_h = (self.in_w - nw) / 2.0, (self.in_h - nh) / 2.0

        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((self.in_h, self.in_w, 3), 114, dtype=np.uint8)
        top, left = int(round(pad_h - 0.1)), int(round(pad_w - 0.1))
        canvas[top:top + nh, left:left + nw] = resized
        blob = canvas[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0

        # YOLOv8 output: (1, 4 + num_classes, num_anchors)
        out = self.session.run(None, {self.input_name: blob})[0][0].T
        boxes_cxcywh, class_scores = out[:, :4], out[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(len(out)), class_ids]
        keep = scores >= conf
        boxes_cxcywh, class_ids, scores = boxes_cxcywh[keep], class_ids[keep], scores[keep]
        if len(scores) == 0:
            return []

        # cx,cy,w,h -> x1,y1,w,h in letterboxed coordinates
        x1 = boxes_cxcywh[:, 0] - boxes_cxcywh[:, 2] / 2.0
        y1 = boxes_cxcywh[:, 1] - boxes_cxcywh[:, 3] / 2.0
        xywh = np.stack([x1, y1, boxes_cxcywh[:, 2], boxes_cxcywh[:, 3]], axis=1)

        results: List[Tuple[int, float, Tuple[int, int, int, int]]] = []
        # Per-class NMS (matches torchvision batched_nms used by ultralytics)
        for cid in np.unique(class_ids):
            idxs = np.where(class_ids == cid)[0]
            picked = cv2.dnn.NMSBoxes(
                xywh[idxs].tolist(), scores[idxs].astype(float).tolist(),
                score_threshold=conf, nms_threshold=iou,
            )
            for i in np.array(picked).flatten():
                bx, by, bw, bh = xywh[idxs[i]]
                ox1 = (bx - pad_w) / scale
                oy1 = (by - pad_h) / scale
                ox2 = (bx + bw - pad_w) / scale
                oy2 = (by + bh - pad_h) / scale
                results.append((
                    int(cid),
                    float(scores[idxs[i]]),
                    (
                        int(max(0, min(w0 - 1, round(ox1)))),
                        int(max(0, min(h0 - 1, round(oy1)))),
                        int(max(0, min(w0 - 1, round(ox2)))),
                        int(max(0, min(h0 - 1, round(oy2)))),
                    ),
                ))
        return results


class SkillPredictor:
    """Predicts skill slots and states from full screen images using trained YOLO model."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        if model_path is None:
            if getattr(sys, "frozen", False):
                # PyInstaller bundle: data files live under sys._MEIPASS.
                base = sys._MEIPASS
            else:
                base = PROJECT_ROOT
            onnx_default = os.path.join(base, "weights", "best.onnx")
            pt_default = os.path.join(base, "weights", "best.pt")
            model_path = onnx_default if os.path.exists(onnx_default) else pt_default
        self.model_path = model_path
        self.model = None
        self._backend = None
        self._init_model()

    def _init_model(self) -> None:
        if not os.path.exists(self.model_path):
            return
        try:
            if self.model_path.lower().endswith(".onnx"):
                self.model = _OnnxYolo(self.model_path)
                self._backend = "onnx"
            else:
                from ultralytics import YOLO

                self.model = YOLO(self.model_path)
                self._backend = "ultralytics"
        except Exception as e:
            print(f"[SkillPredictor] Error loading model: {e}")

    def predict(self, screen_image: Any, conf: float = 0.25) -> BattleSkillsState:
        """Process full screen image and return detected skill slots."""
        h, w = screen_image.shape[:2] if hasattr(screen_image, "shape") else (1080, 1920)
        slots_result: List[SkillSlot] = []

        if self.model is not None:
            if self._backend == "onnx":
                detections = self.model.predict(screen_image, conf=conf)
            else:
                detections = []
                results = self.model.predict(screen_image, conf=conf, verbose=False)
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    for i in range(len(boxes)):
                        xyxy = boxes.xyxy[i].cpu().numpy().astype(int)
                        detections.append((
                            int(boxes.cls[i].item()),
                            float(boxes.conf[i].item()),
                            (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                        ))
            for cid, score, xyxy in detections:
                slot = SkillSlot(
                    slot_id=cid + 1,
                    name=f"Skill_{cid + 1}",
                    confidence=round(score, 3),
                    bbox=xyxy,
                )
                slots_result.append(slot)

        # Sort slots by slot_id (1 to 4)
        slots_result.sort(key=lambda s: s.slot_id)

        return BattleSkillsState(
            timestamp=time.time(),
            screen_resolution=(w, h),
            slots=slots_result,
        )
