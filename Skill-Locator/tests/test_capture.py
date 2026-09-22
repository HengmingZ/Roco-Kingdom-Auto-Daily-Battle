"""Unit test for primary screen capture.
"""

from __future__ import annotations

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capture.screen_grabber import ScreenGrabber


def test_primary_screen_capture() -> None:
    print("[Test] Initializing ScreenGrabber...")
    grabber = ScreenGrabber()
    width, height = grabber.get_primary_resolution()
    print(f"[Test] Detected Primary Screen Resolution: {width}x{height}")
    assert width > 0 and height > 0, "Invalid screen resolution"

    test_output = os.path.join(CURRENT_DIR, "test_primary_screen.bmp")
    print(f"[Test] Capturing and saving primary screen to: {test_output}")
    saved_path = grabber.save_screenshot(test_output)
    assert os.path.exists(saved_path), f"Saved screenshot does not exist: {saved_path}"
    file_size = os.path.getsize(saved_path)
    print(f"[Test] Screenshot successfully verified! File size: {file_size} bytes")

    # Clean up test artifact
    if os.path.exists(saved_path):
        os.remove(saved_path)
        print("[Test] Cleaned up temporary test screenshot.")


if __name__ == "__main__":
    test_primary_screen_capture()
