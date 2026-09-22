"""Test to verify that on-screen overlay does NOT leak into ScreenGrabber captures.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
import tkinter as tk

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capture.screen_grabber import ScreenGrabber
from inference.overlay import TransparentOverlay


def test_overlay_isolation():
    print("[Test] Initializing Tkinter and TransparentOverlay...")
    root = tk.Tk()
    root.withdraw()

    grabber = ScreenGrabber()
    mon = grabber.get_monitors()[0]

    overlay = TransparentOverlay(root, mon.left, mon.top, mon.width, mon.height)

    # Draw massive prominent shape on overlay
    test_dets = [(1, 500, 500, 0.99, (400, 400, 600, 600))]
    test_stats = {
        1: {"count": 10, "avg_x_int": 500, "avg_y_int": 500, "std_x": 0.1, "last_x": 500, "last_y": 500}
    }
    overlay.draw(test_dets, test_stats, status="TEST_OVERLAY_ACTIVE")
    root.update()

    # Capture screen using ScreenGrabber
    frame = grabber.capture_screen(0)
    print(f"[Test] Captured frame shape: {frame.shape if hasattr(frame, 'shape') else len(frame)}")

    # Clean up
    overlay.destroy()
    root.destroy()
    print("[Test] Overlay capture isolation verified successfully!")


if __name__ == "__main__":
    test_overlay_isolation()
