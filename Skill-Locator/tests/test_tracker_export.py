"""Automated test for CoordinateAverager JSON export and data pipeline.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from inference.coordinate_tracker_node import CoordinateAverager


def test_export_pipeline():
    print("[Test] Testing CoordinateAverager JSON export pipeline...")
    averager = CoordinateAverager()

    # Simulate 10 frames of 4 skills with slight variations
    for i in range(10):
        frame = [
            (1, 1000 + i % 3, 800 + i % 2, 0.95, (950, 750, 1050, 850)),
            (2, 1150 + i % 2, 800 + i % 3, 0.94, (1100, 750, 1200, 850)),
            (3, 1300 + i % 3, 800 + i % 2, 0.96, (1250, 750, 1350, 850)),
            (4, 1450 + i % 2, 800 + i % 3, 0.93, (1400, 750, 1500, 850)),
        ]
        averager.record_frame(frame)

    assert averager.total_frames == 10

    # Test export
    out_dir = os.path.join(PROJECT_ROOT, "configs")
    out_file = os.path.join(out_dir, "test_calibrated_coords.json")

    averager.export_json(out_file, screen_res=(2560, 1440), monitor_name="\\\\.\\DISPLAY1")

    assert os.path.exists(out_file), "Exported file must exist"

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["target_monitor"] == "\\\\.\\DISPLAY1"
    assert data["screen_resolution"] == [2560, 1440]
    assert data["total_frames_sampled"] == 10
    assert "1" in data["skills"]
    assert data["skills"]["1"]["sample_count"] == 10
    assert data["skills"]["1"]["calibrated_center"][0] in [1000, 1001, 1002]

    # Clean up test artifact
    os.remove(out_file)
    print("[Test] Export verification test passed cleanly!")


if __name__ == "__main__":
    test_export_pipeline()
