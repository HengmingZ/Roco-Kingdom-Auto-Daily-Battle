"""Locate the '再次挑战' (challenge-again) button on the settlement screen via OCR.

Uses rapidocr-onnxruntime with its bundled Chinese models; the engine is
created lazily on first use so app startup stays fast.
"""

from __future__ import annotations

import re
import threading
from typing import List, Optional, Tuple

from capture.screen_grabber import ScreenGrabber, MonitorInfo

TARGET_TEXT = "再次挑战"
MIN_SCORE = 0.5

OcrHit = Tuple[list, str, float]  # (box points, text, score)


class RetryButtonLocator:
    _engine_instance = None
    _engine_lock = threading.Lock()

    @classmethod
    def _engine(cls):
        with cls._engine_lock:
            if cls._engine_instance is None:
                from rapidocr_onnxruntime import RapidOCR
                cls._engine_instance = RapidOCR()
            return cls._engine_instance

    def __init__(self) -> None:
        self._grabber = ScreenGrabber()

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", "", text)

    def scan_texts(self, mon: MonitorInfo) -> List[OcrHit]:
        """OCR the whole monitor and return all recognized text boxes."""
        img = self._grabber.capture_screen(mon.index)
        if not hasattr(img, "shape"):
            return []
        result, _elapse = self._engine()(img)
        if not result:
            return []
        return [(box, text, score) for box, text, score in result]

    def find(self, mon: MonitorInfo) -> Optional[Tuple[int, int, float, str]]:
        """Return (abs_x, abs_y, score, matched_text) of the retry button, or None."""
        best: Optional[OcrHit] = None
        for box, text, score in self.scan_texts(mon):
            normalized = self._normalize(text)
            if score < MIN_SCORE:
                continue
            # Exact containment first; tolerate OCR splitting/misreading one char.
            if TARGET_TEXT in normalized:
                rank = 2
            elif "挑战" in normalized and len(normalized) <= 6:
                rank = 1
            else:
                continue
            if best is None or rank > best[0] or (rank == best[0] and score > best[1][2]):
                best = (rank, (box, text, score))
        if best is None:
            return None
        box, text, score = best[1]
        cx = sum(p[0] for p in box) / 4
        cy = sum(p[1] for p in box) / 4
        return mon.left + int(cx), mon.top + int(cy), float(score), text
