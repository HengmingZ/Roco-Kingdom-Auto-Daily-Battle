"""Test to verify that SendInput with SetThreadDesktop generates real physical clicks.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
import time
import tkinter as tk

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_verified_click():
    print("[Test] Testing verified SendInput click on real button...")
    u32 = ctypes.windll.user32
    h_desk = u32.OpenDesktopW("default", 0, False, 0x01FF)
    assert h_desk, "Failed to open default desktop"
    ok = u32.SetThreadDesktop(h_desk)
    assert ok, "Failed to attach thread desktop"

    root = tk.Tk()
    root.geometry("250x250+300+300")
    events = []
    btn = tk.Button(root, text="VerifiedTest", command=lambda: events.append("SUCCESS"))
    btn.pack(expand=True, fill="both")
    root.update()

    bx = root.winfo_rootx() + btn.winfo_width() // 2
    by = root.winfo_rooty() + btn.winfo_height() // 2

    # Import click_at from clicker
    from inference.clicker import click_at

    ok_click = click_at(bx, by, hold_time=0.1)
    assert ok_click, "click_at must return True"

    for _ in range(10):
        root.update()
        time.sleep(0.02)

    root.destroy()
    assert events == ["SUCCESS"], f"Expected ['SUCCESS'], got {events}"
    print("[Test] Verified click executed and registered button event successfully!")


if __name__ == "__main__":
    test_verified_click()
