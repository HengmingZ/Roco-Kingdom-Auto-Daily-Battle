"""Standalone test for OCR-based '再次挑战' button location.

Open the game on the settlement page, then run:
    python tests/test_retry_locator.py [monitor_index]

Prints every recognized text, marks retry-button candidates, and saves an
annotated screenshot to tests/output/retry_locator_debug.png for inspection.
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

COUNTDOWN = 3


def main() -> None:
    grabber = ScreenGrabber()
    monitors = grabber.get_monitors()
    mon_idx = int(sys.argv[1]) if len(sys.argv) > 1 else next(
        (i for i, m in enumerate(monitors) if m.is_primary), 0)
    mon = monitors[mon_idx]
    for i, m in enumerate(monitors):
        mark = " <-- selected" if i == mon_idx else ""
        print(f"[Monitor {i}] {m.label}{mark}")

    for remaining in range(COUNTDOWN, 0, -1):
        print(f"{remaining}s ... switch to the settlement page now!")
        time.sleep(1.0)

    locator = RetryButtonLocator()
    t0 = time.time()
    hits = locator.scan_texts(mon)
    elapsed = time.time() - t0
    print(f"OCR finished in {elapsed:.2f}s, {len(hits)} text boxes:")

    out_dir = os.path.join(CURRENT_DIR, "output")
    os.makedirs(out_dir, exist_ok=True)
    debug_path = os.path.join(out_dir, "retry_locator_debug.png")

    import cv2
    img = grabber.capture_screen(mon.index).copy()
    for i, (box, text, score) in enumerate(hits):
        print(f"  [{i}] score={score:.2f} text={text!r} box={[[round(x), round(y)] for x, y in box]}")
        pts = [(int(px), int(py)) for px, py in box]
        for j in range(4):
            cv2.line(img, pts[j], pts[(j + 1) % 4], (0, 255, 0), 2)
        cv2.putText(img, str(i), pts[0], cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    found = locator.find(mon)
    if found:
        x, y, score, text = found
        print(f"RETRY BUTTON FOUND: text={text!r} score={score:.2f} -> screen ({x}, {y})")
        cv2.circle(img, (x - mon.left, y - mon.top), 12, (0, 0, 255), 3)
    else:
        print("RETRY BUTTON NOT FOUND.")

    cv2.imwrite(debug_path, img)
    print(f"Annotated screenshot saved: {debug_path}")


if __name__ == "__main__":
    main()
