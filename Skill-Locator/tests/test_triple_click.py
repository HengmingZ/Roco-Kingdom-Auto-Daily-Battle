"""Standalone simulation of the combo post-round center triple-click.

Waits 3s so the user can activate the game window, then performs 3 clicks
at the center of the selected monitor: hold 0.3s, release, 0.5s interval.

Usage:
    python tests/test_triple_click.py [monitor_index] [--hold 0.3] [--here] [--ref]

--here: click at the CURRENT physical cursor position instead of the monitor
        center. Put your mouse exactly where a manual click works in-game to
        isolate "wrong coordinate" from "injection not accepted".
--ref:  use the exact RocoKingdom_Clicker pipeline (single device 11,
        interception strokes only: no mouse_event, no absolute-move stroke).
        Use this when the standard pipeline fails inside the game.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capture.screen_grabber import ScreenGrabber
from inference.clicker import hold_click_at

INTERCEPTION_DLL = r"d:\sProject\GameTraining\RocoClicker\RocoKingdom_Clicker\interception.dll"

CLICK_INTERVAL = 0.5
COUNTDOWN = 3


class InterceptionMouseStroke(ctypes.Structure):
    _fields_ = [
        ("state", ctypes.c_ushort),
        ("flags", ctypes.c_ushort),
        ("rolling", ctypes.c_short),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("information", ctypes.c_uint),
    ]


class ReferenceClicker:
    """Exact pipeline from RocoKingdom_Clicker / test_clicker_interception.py."""

    def __init__(self, dll_path: str = INTERCEPTION_DLL):
        self._lib = ctypes.CDLL(dll_path)
        self._lib.interception_create_context.restype = ctypes.c_void_p
        self._lib.interception_send.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
        self._lib.interception_send.restype = ctypes.c_int
        self._ctx = self._lib.interception_create_context()
        if not self._ctx:
            raise RuntimeError("Failed to create Interception context")

    def click_at(self, x: int, y: int, hold_time: float = 0.18) -> bool:
        u32 = ctypes.windll.user32
        hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
        if hd:
            u32.SetThreadDesktop(hd)
        pt = wintypes.POINT(x, y)
        hwnd = u32.WindowFromPoint(pt)
        if hwnd:
            u32.SetForegroundWindow(u32.GetAncestor(hwnd, 2) or hwnd)
        u32.SetCursorPos(x, y)
        time.sleep(0.04)
        down = InterceptionMouseStroke(state=1, flags=0, rolling=0, x=0, y=0, information=0)
        r1 = self._lib.interception_send(self._ctx, 11, ctypes.byref(down), 1)
        time.sleep(hold_time)
        up = InterceptionMouseStroke(state=2, flags=0, rolling=0, x=0, y=0, information=0)
        r2 = self._lib.interception_send(self._ctx, 11, ctypes.byref(up), 1)
        return r1 > 0 and r2 > 0


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    hold = 0.3
    if "--hold" in sys.argv:
        hold = float(sys.argv[sys.argv.index("--hold") + 1])
    use_cursor_pos = "--here" in sys.argv
    use_ref = "--ref" in sys.argv

    clicker = ReferenceClicker() if use_ref else None
    if use_ref:
        print("Mode: REFERENCE pipeline (device 11 only, no mouse_event)")

    if use_cursor_pos:
        print("Mode: click at current cursor position (--here)")
    else:
        grabber = ScreenGrabber()
        monitors = grabber.get_monitors()
        mon_idx = int(args[0]) if args else next(
            (i for i, m in enumerate(monitors) if m.is_primary), 0)
        for i, m in enumerate(monitors):
            mark = " <-- selected" if i == mon_idx else ""
            print(f"[Monitor {i}] {m.label}{mark}")

    for remaining in range(COUNTDOWN, 0, -1):
        print(f"{remaining}s ... switch to the game window now!")
        time.sleep(1.0)

    if use_cursor_pos:
        u32 = ctypes.windll.user32
        pt = wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(pt))
        cx, cy = pt.x, pt.y
    else:
        mon = monitors[mon_idx]
        cx, cy = mon.left + mon.width // 2, mon.top + mon.height // 2
    print(f"Target: ({cx}, {cy}) | hold {hold}s | interval {CLICK_INTERVAL}s")

    for click_n in range(3):
        if use_ref:
            ok = clicker.click_at(cx, cy, hold_time=hold)
        else:
            ok = hold_click_at(cx, cy, hold_time=hold)
        tag = "driver-level" if ok else "basic-event only (driver not ready)"
        print(f"Click {click_n + 1}/3 at ({cx}, {cy}) [hold {hold}s] [{tag}]")
        if click_n < 2:
            time.sleep(CLICK_INTERVAL)

    print("Done.")


if __name__ == "__main__":
    main()
