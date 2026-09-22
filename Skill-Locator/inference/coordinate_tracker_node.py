"""Skill-Locator Coordinate Tracker Node alias.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# [UPDATE - 2026-09-12]
# Reason: Expose CoordinateAverager for backward compatibility.
# Modification: Imported and re-exported CoordinateAverager and SlotStats.
from inference.averager import CoordinateAverager, SlotStats
from inference.tracker_gui import ScreenTrackerApp


def main() -> None:
    root = tk.Tk()
    app = ScreenTrackerApp(root, PROJECT_ROOT)
    root.mainloop()


if __name__ == "__main__":
    main()
