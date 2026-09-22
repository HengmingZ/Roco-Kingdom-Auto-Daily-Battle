"""Skill-Locator Screen Detection & Average Coordinate Tracking Node.

Main entry point for on-screen skill detection and running average calibration.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

# Set project root in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# [UPDATE - 2026-09-12]
# Reason: Refactor monolithic file to modular components under 200 lines.
# Modification: Delegated GUI logic to ScreenTrackerApp in tracker_gui.py.
from inference.tracker_gui import ScreenTrackerApp


def main() -> None:
    """Launch the main skill tracker application."""
    root = tk.Tk()
    app = ScreenTrackerApp(root, PROJECT_ROOT)
    root.mainloop()


if __name__ == "__main__":
    main()
