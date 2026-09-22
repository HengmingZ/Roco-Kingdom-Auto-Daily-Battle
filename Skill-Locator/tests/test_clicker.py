"""Unit test for clicker module coordinate calculation.
"""

from __future__ import annotations

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capture.win32_defs import MonitorInfo
from inference.averager import CoordinateAverager


def test_click_target_calculation():
    print("[Test] Testing click target coordinate calculation...")
    averager = CoordinateAverager()

    # Simulate detection for slot 2 on a secondary monitor at left=2560, top=0
    mon = MonitorInfo(
        index=1, device_name="\\\\.\\DISPLAY2",
        left=2560, top=100, right=4480, bottom=1180,
        width=1920, height=1080, is_primary=False, label="屏幕 2"
    )

    averager.record_frame([(2, 500, 600, 0.95, (450, 550, 550, 650))])

    stat = averager.slots[2].to_dict()
    assert stat["avg_x_int"] == 500
    assert stat["avg_y_int"] == 600

    target_x = mon.left + stat["avg_x_int"]
    target_y = mon.top + stat["avg_y_int"]

    assert target_x == 3060, f"Expected 3060, got {target_x}"
    assert target_y == 700, f"Expected 700, got {target_y}"

    print(f"[Test] Calculated desktop target: ({target_x}, {target_y}) - Verified!")


if __name__ == "__main__":
    test_click_target_calculation()
