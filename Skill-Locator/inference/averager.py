"""Coordinate statistical averager using fixed-capacity FIFO queue (deque).
Avoids unbounded memory growth and enables adaptive sliding-window calibration.
"""

from __future__ import annotations

from collections import deque
import json
import math
import os
import time
from typing import Dict, List, Tuple


class SlotStats:
    """Statistical accumulator using a fixed-capacity FIFO queue (sliding window)."""

    def __init__(self, slot_id: int, maxlen: int = 100) -> None:
        self.slot_id = slot_id
        self.maxlen = maxlen
        self.queue: deque[Tuple[int, int, float, Tuple[int, int, int, int]]] = deque(maxlen=maxlen)
        self.total_seen = 0

    def add(self, x: int, y: int, conf: float, bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> None:
        self.total_seen += 1
        self.queue.append((x, y, conf, bbox))

    @property
    def count(self) -> int:
        return len(self.queue)

    @property
    def avg_x(self) -> float:
        return sum(p[0] for p in self.queue) / len(self.queue) if self.queue else 0.0

    @property
    def avg_y(self) -> float:
        return sum(p[1] for p in self.queue) / len(self.queue) if self.queue else 0.0

    @property
    def std_x(self) -> float:
        if len(self.queue) <= 1:
            return 0.0
        ax = self.avg_x
        return math.sqrt(sum((p[0] - ax) ** 2 for p in self.queue) / len(self.queue))

    @property
    def std_y(self) -> float:
        if len(self.queue) <= 1:
            return 0.0
        ay = self.avg_y
        return math.sqrt(sum((p[1] - ay) ** 2 for p in self.queue) / len(self.queue))

    @property
    def avg_conf(self) -> float:
        return sum(p[2] for p in self.queue) / len(self.queue) if self.queue else 0.0

    @property
    def last_x(self) -> int:
        return self.queue[-1][0] if self.queue else 0

    @property
    def last_y(self) -> int:
        return self.queue[-1][1] if self.queue else 0

    @property
    def last_bbox(self) -> Tuple[int, int, int, int]:
        return self.queue[-1][3] if self.queue else (0, 0, 0, 0)

    def to_dict(self) -> dict:
        return {
            "slot_id": self.slot_id, "count": self.count, "total_seen": self.total_seen,
            "last_x": self.last_x, "last_y": self.last_y,
            "avg_x": round(self.avg_x, 2), "avg_y": round(self.avg_y, 2),
            "avg_x_int": int(round(self.avg_x)), "avg_y_int": int(round(self.avg_y)),
            "std_x": round(self.std_x, 2), "std_y": round(self.std_y, 2),
            "avg_conf": round(self.avg_conf, 4), "last_bbox": list(self.last_bbox),
        }


class CoordinateAverager:
    """Maintains fixed-capacity FIFO queues across all 4 skill slots."""

    def __init__(self, window_size: int = 100) -> None:
        self.window_size = window_size
        self.slots: Dict[int, SlotStats] = {i: SlotStats(i, maxlen=window_size) for i in range(1, 5)}
        self.total_frames = 0

    def record_frame(self, dets: List[Tuple[int, int, int, float, Tuple[int, int, int, int]]]) -> None:
        self.total_frames += 1
        for sid, cx, cy, conf, bbox in dets:
            if sid in self.slots:
                self.slots[sid].add(cx, cy, conf, bbox)

    def reset(self) -> None:
        self.slots = {i: SlotStats(i, maxlen=self.window_size) for i in range(1, 5)}
        self.total_frames = 0

    def get_summary(self) -> Dict[int, dict]:
        return {sid: s.to_dict() for sid, s in self.slots.items()}

    def export_json(self, path: str, screen_res: Tuple[int, int] = (1920, 1080), monitor: str = "", monitor_name: str = "") -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        mon = monitor or monitor_name or "DISPLAY"
        data = {
            "calibrated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_monitor": mon, "screen_resolution": list(screen_res),
            "window_size": self.window_size, "total_frames_sampled": self.total_frames,
            "skills": {
                str(sid): {
                    "name": f"技能 {sid}", "sample_count": s.count, "total_seen": s.total_seen,
                    "calibrated_center": [s.to_dict()["avg_x_int"], s.to_dict()["avg_y_int"]],
                    "precise_center": [s.to_dict()["avg_x"], s.to_dict()["avg_y"]],
                    "jitter_std_dev": [s.to_dict()["std_x"], s.to_dict()["std_y"]],
                    "avg_confidence": s.to_dict()["avg_conf"], "last_bbox": list(s.last_bbox),
                } for sid, s in self.slots.items()
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
