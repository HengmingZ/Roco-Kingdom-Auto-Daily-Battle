"""Test the OCR-locate + driver-click chain on the '再次挑战' button.

Open the game on the settlement page (button visible), then run:
    python tests/test_ocr_clicker.py [monitor_index]

Flow: 3s countdown -> OCR locate -> one hold_click_at(0.3s) at the button
center -> wait 1s -> OCR re-scan (read-only) to check whether it disappeared.
No other actions are performed.
"""

from __future__ import annotations

import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from capture.screen_grabber import ScreenGrabber
from inference.retry_locator import RetryButtonLocator
from inference.clicker import hold_click_at

COUNTDOWN = 3
HOLD_TIME = 0.3


def main() -> None:
    grabber = ScreenGrabber()
    monitors = grabber.get_monitors()
    mon_idx = int(sys.argv[1]) if len(sys.argv) > 1 else next(
        (i for i, m in enumerate(monitors) if m.is_primary), 0)
    mon = monitors[mon_idx]
    print(f"Monitor: {mon.label}")

    for remaining in range(COUNTDOWN, 0, -1):
        print(f"{remaining}s ... switch to the settlement page now!")
        time.sleep(1.0)

    locator = RetryButtonLocator()
    found = locator.find(mon)
    if not found:
        print("FAIL: retry button not found by OCR. Nothing clicked.")
        return
    x, y, score, text = found
    print(f"OCR found: text={text!r} score={score:.2f} -> screen ({x}, {y})")

    ok = hold_click_at(x, y, hold_time=HOLD_TIME)
    print(f"Clicked once with hold_click_at(hold={HOLD_TIME}s), driver ok={ok}")

    time.sleep(1.0)
    still = locator.find(mon)
    if still:
        print(f"RESULT: button STILL VISIBLE at ({still[0]}, {still[1]}) - click had no effect.")
    else:
        print("RESULT: button GONE - page jumped, click succeeded.")


if __name__ == "__main__":
    main()
