"""Test DriverClicker initialization and execution.
"""

from __future__ import annotations

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from capture.win32_defs import MonitorInfo
from inference.averager import CoordinateAverager


def test_driver_clicker():
    print("[Test] Verifying DriverClicker...")
    # Import clicker
    from inference.clicker import _driver, release_skill

    print(f"[Test] Interception Driver active: {_driver.ctx is not None}, Mouse dev: {_driver.mouse_dev}")

    averager = CoordinateAverager()
    averager.record_frame([(1, 100, 100, 0.9, (80, 80, 120, 120))])

    mon = MonitorInfo(0, "DISPLAY", 0, 0, 1920, 1080, 1920, 1080, True, "Screen 1")
    ok, msg = release_skill(1, averager, mon)
    print(f"[Test] release_skill output: ok={ok}, msg={msg}")
    assert ok is True
    print("[Test] Driver test passed successfully!")


if __name__ == "__main__":
    test_driver_clicker()
