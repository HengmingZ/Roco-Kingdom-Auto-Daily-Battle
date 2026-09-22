"""Test for CoordinateAverager math and aggregation logic.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class SlotCoordinateStats:
    """Statistical aggregator for a single skill slot's center coordinates."""

    def __init__(self, slot_id: int) -> None:
        self.slot_id = slot_id
        self.count = 0
        self.sum_x = 0.0
        self.sum_y = 0.0
        self.sum_x2 = 0.0
        self.sum_y2 = 0.0
        self.sum_conf = 0.0
        self.last_x = 0
        self.last_y = 0
        self.last_conf = 0.0
        self.min_x = 999999
        self.max_x = -999999
        self.min_y = 999999
        self.max_y = -999999

    def add(self, x: int, y: int, conf: float) -> None:
        self.count += 1
        self.sum_x += x
        self.sum_y += y
        self.sum_x2 += x * x
        self.sum_y2 += y * y
        self.sum_conf += conf
        self.last_x = x
        self.last_y = y
        self.last_conf = conf
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)
        self.min_y = min(self.min_y, y)
        self.max_y = max(self.max_y, y)

    @property
    def avg_x(self) -> float:
        return self.sum_x / self.count if self.count > 0 else 0.0

    @property
    def avg_y(self) -> float:
        return self.sum_y / self.count if self.count > 0 else 0.0

    @property
    def std_x(self) -> float:
        if self.count <= 1:
            return 0.0
        variance = (self.sum_x2 / self.count) - (self.avg_x ** 2)
        return math.sqrt(max(0.0, variance))

    @property
    def std_y(self) -> float:
        if self.count <= 1:
            return 0.0
        variance = (self.sum_y2 / self.count) - (self.avg_y ** 2)
        return math.sqrt(max(0.0, variance))

    @property
    def avg_conf(self) -> float:
        return self.sum_conf / self.count if self.count > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "slot_id": self.slot_id,
            "count": self.count,
            "last_x": self.last_x,
            "last_y": self.last_y,
            "avg_x": round(self.avg_x, 2),
            "avg_y": round(self.avg_y, 2),
            "avg_x_int": round(self.avg_x),
            "avg_y_int": round(self.avg_y),
            "std_x": round(self.std_x, 2),
            "std_y": round(self.std_y, 2),
            "min_x": self.min_x if self.count > 0 else 0,
            "max_x": self.max_x if self.count > 0 else 0,
            "min_y": self.min_y if self.count > 0 else 0,
            "max_y": self.max_y if self.count > 0 else 0,
            "avg_conf": round(self.avg_conf, 4),
        }


class CoordinateAverager:
    """Manages coordinate accumulation and running statistics across all 4 slots."""

    def __init__(self) -> None:
        self.slots: Dict[int, SlotCoordinateStats] = {
            i: SlotCoordinateStats(i) for i in range(1, 5)
        }
        self.total_frames = 0

    def update(self, slot_id: int, x: int, y: int, conf: float) -> None:
        if slot_id in self.slots:
            self.slots[slot_id].add(x, y, conf)

    def record_frame(self, detections: List[Tuple[int, int, int, float]]) -> None:
        """Record detections from a single frame: list of (slot_id, x, y, conf)."""
        self.total_frames += 1
        for slot_id, x, y, conf in detections:
            self.update(slot_id, x, y, conf)

    def reset(self) -> None:
        self.slots = {i: SlotCoordinateStats(i) for i in range(1, 5)}
        self.total_frames = 0

    def get_summary(self) -> Dict[int, dict]:
        return {slot_id: stat.to_dict() for slot_id, stat in self.slots.items()}


def test_coordinate_averager():
    print("[Test] Initializing CoordinateAverager...")
    averager = CoordinateAverager()

    # Simulate 3 frames of detections for Slot 1 and Slot 2
    frame1 = [(1, 100, 200, 0.90), (2, 300, 400, 0.85)]
    frame2 = [(1, 102, 202, 0.92), (2, 298, 402, 0.88)]
    frame3 = [(1, 98, 198, 0.88), (2, 302, 398, 0.91)]

    averager.record_frame(frame1)
    averager.record_frame(frame2)
    averager.record_frame(frame3)

    summary = averager.get_summary()

    # Slot 1: (100+102+98)/3 = 100.0, (200+202+198)/3 = 200.0
    s1 = summary[1]
    assert s1["count"] == 3, f"Expected count 3, got {s1['count']}"
    assert s1["avg_x"] == 100.0, f"Expected avg_x 100.0, got {s1['avg_x']}"
    assert s1["avg_y"] == 200.0, f"Expected avg_y 200.0, got {s1['avg_y']}"
    assert s1["avg_x_int"] == 100
    assert s1["avg_y_int"] == 200
    assert s1["min_x"] == 98
    assert s1["max_x"] == 102
    assert s1["std_x"] > 0, "StdDev should be positive"

    # Slot 3 had no detections
    s3 = summary[3]
    assert s3["count"] == 0, f"Expected count 0, got {s3['count']}"
    assert s3["avg_x"] == 0.0

    print("[Test] Slot 1 Summary:", s1)
    print("[Test] Slot 2 Summary:", summary[2])
    print("[Test] Slot 3 (empty) Summary:", s3)
    print("[Test] All assertions passed successfully!")


if __name__ == "__main__":
    test_coordinate_averager()
