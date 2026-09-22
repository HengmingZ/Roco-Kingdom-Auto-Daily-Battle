# [UPDATE - 2026-09-12]
# Reason: Standard SendInput fails in DirectInput/anti-cheat games like 《洛克王国：世界》.
# Modification: Ported exact kernel-level mouse injection from RocoKingdom_Clicker using
#               interception.dll with automatic device discovery, absolute coordinate
#               transformation, thread desktop attachment, and 200ms hold time.
# [UPDATE - 2026-09-20]
# Reason: Combo post-round actions need wheel-scroll and key presses.
# Modification: Added kernel-level mouse wheel (INTERCEPTION_MOUSE_WHEEL) and keyboard
#               strokes (scan-code based) with Windows API fallbacks.
# [UPDATE - 2026-11-02]
# Reason: Combo post-round center clicks need a longer button hold (0.3s) than skill taps.
# Modification: Added hold_click_at, a copy of click_at with a longer hold time; also
#               added a GetCursorPos verification after the driver move in click_at.
#               NOTE: the driver maps absolute coords onto the PRIMARY monitor, so
#               screen_to_interception must keep primary-screen normalization (a
#               virtual-screen normalization was tried and shifted every click).
# [UPDATE - 2026-11-02b]
# Reason: The game discarded hold_click_at clicks (post-round triple click had no
#         effect) while accepting the reference pipeline from test_clicker_interception.
# Modification: hold_click_at now matches the reference pipeline exactly: single mouse
#               device via send_stroke_to, interception strokes only -- no mouse_event
#               fallback (its LLMHF_INJECTED flag gets the click discarded) and no
#               driver-level absolute move. click_at is unchanged.

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
import time
from typing import Optional, Tuple

from capture.win32_defs import MonitorInfo
from inference.averager import CoordinateAverager

INTERCEPTION_MOUSE_WHEEL = 0x0400
INTERCEPTION_KEY_DOWN = 0x0000
INTERCEPTION_KEY_UP = 0x0001

SCANCODE_1 = 0x02
SCANCODE_SPACE = 0x39

class InterceptionMouseStroke(ctypes.Structure):
    _fields_ = [
        ("state", ctypes.c_ushort),
        ("flags", ctypes.c_ushort),
        ("rolling", ctypes.c_short),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("information", ctypes.c_uint),
    ]

class InterceptionKeyStroke(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("info", ctypes.c_ushort),
        ("information", ctypes.c_uint),
    ]

class InterceptionEngine:
    """Interception kernel driver wrapper directly ported from RocoKingdom_Clicker."""
    _instance: Optional[InterceptionEngine] = None

    def __init__(self):
        self._lib = None
        self._ctx = None
        self._devices = [11, 12]
        self._keyboards: list[int] = []
        self._load_driver()

    @classmethod
    def get(cls) -> InterceptionEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_driver(self) -> None:
        dll_candidates = [
            os.path.join(os.path.dirname(__file__), "..", "..", "driver_installer", "interception.dll"),
            r"d:\sProject\GameTraining\RocoClicker\RocoKingdom_Clicker\interception.dll",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "RocoClicker", "RocoKingdom_Clicker", "interception.dll"),
            "interception.dll",
        ]
        if getattr(sys, "frozen", False):
            # PyInstaller bundle: prefer the DLL bundled inside the app, then
            # one placed next to the exe.
            dll_candidates.insert(0, os.path.join(sys._MEIPASS, "driver_installer", "interception.dll"))
            dll_candidates.insert(1, os.path.join(os.path.dirname(sys.executable), "driver_installer", "interception.dll"))
        for p in dll_candidates:
            if os.path.exists(p):
                try:
                    self._lib = ctypes.CDLL(p)
                    self._lib.interception_create_context.restype = ctypes.c_void_p
                    self._lib.interception_destroy_context.argtypes = [ctypes.c_void_p]
                    self._lib.interception_send.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
                    self._lib.interception_send.restype = ctypes.c_int
                    self._lib.interception_is_mouse.argtypes = [ctypes.c_int]
                    self._lib.interception_is_mouse.restype = ctypes.c_int
                    self._lib.interception_is_keyboard.argtypes = [ctypes.c_int]
                    self._lib.interception_is_keyboard.restype = ctypes.c_int

                    self._ctx = self._lib.interception_create_context()
                    if self._ctx:
                        self._devices = [d for d in range(11, 21) if self._lib.interception_is_mouse(d)]
                        self._keyboards = [d for d in range(1, 11) if self._lib.interception_is_keyboard(d)]
                        return
                except Exception:
                    pass

    @property
    def is_ready(self) -> bool:
        return bool(self._lib and self._ctx)

    def send_stroke(self, stroke: InterceptionMouseStroke) -> bool:
        if not self.is_ready:
            return False
        ok = False
        for dev in self._devices:
            if self._lib.interception_send(self._ctx, dev, ctypes.byref(stroke), 1) > 0:
                ok = True
        return ok

    def send_stroke_to(self, device: int, stroke: InterceptionMouseStroke) -> bool:
        """Send a stroke to a single mouse device (reference-clicker behavior)."""
        if not self.is_ready:
            return False
        return self._lib.interception_send(self._ctx, device, ctypes.byref(stroke), 1) > 0

    def send_key_stroke(self, stroke: InterceptionKeyStroke) -> bool:
        if not self.is_ready:
            return False
        ok = False
        for dev in self._keyboards:
            if self._lib.interception_send(self._ctx, dev, ctypes.byref(stroke), 1) > 0:
                ok = True
        return ok

def attach_desktop() -> None:
    u32 = ctypes.windll.user32
    hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
    if hd:
        u32.SetThreadDesktop(hd)

def force_foreground(hwnd) -> None:
    """Bring hwnd to the foreground even when this thread lacks foreground rights."""
    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    fg = u32.GetForegroundWindow()
    cur = k32.GetCurrentThreadId()
    tgt = u32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(tgt and tgt != cur and u32.AttachThreadInput(cur, tgt, True))
    try:
        u32.ShowWindow(hwnd, 9)  # SW_RESTORE
        u32.BringWindowToTop(hwnd)
        u32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            u32.AttachThreadInput(cur, tgt, False)

def screen_to_interception(x: int, y: int) -> Tuple[int, int]:
    """Map physical pixel coords to 0-65535 absolute coords.

    The Interception driver maps absolute coordinates onto the PRIMARY monitor
    (same convention as MOUSEEVENTF_ABSOLUTE without VIRTUALDESK), so the
    normalization must use the primary screen size. Normalizing against the
    virtual screen was tried and made every click land offset to the left.
    """
    u32 = ctypes.windll.user32
    w = max(u32.GetSystemMetrics(0) - 1, 1)
    h = max(u32.GetSystemMetrics(1) - 1, 1)
    abs_x = int(max(0, min(x, w)) * 65535 / w)
    abs_y = int(max(0, min(y, h)) * 65535 / h)
    return abs_x, abs_y

def _in_primary(x: int, y: int) -> bool:
    u32 = ctypes.windll.user32
    return 0 <= x < u32.GetSystemMetrics(0) and 0 <= y < u32.GetSystemMetrics(1)

def click_at(x: int, y: int, hold_time: float = 0.05) -> bool:
    """Execute hardware mouse click at physical screen coordinate (x, y).

    hold_time intentionally short: many games treat a long press on a skill
    icon as "hold to show description" instead of a tap to cast.
    """
    u32 = ctypes.windll.user32
    attach_desktop()

    # 1. Activate target window under coordinate
    pt = wintypes.POINT(x, y)
    hwnd = u32.WindowFromPoint(pt)
    if hwnd:
        root_hwnd = u32.GetAncestor(hwnd, 2) or hwnd
        force_foreground(root_hwnd)

    # 2. Move the cursor. SetCursorPos is authoritative and works on any monitor.
    # The driver's absolute move maps onto the PRIMARY monitor only, so send it
    # just for on-primary targets (raw-input games track driver motion); for
    # targets on a secondary monitor it would teleport the cursor off-target.
    eng = InterceptionEngine.get()
    u32.SetCursorPos(x, y)
    if eng.is_ready and _in_primary(x, y):
        abs_x, abs_y = screen_to_interception(x, y)
        move = InterceptionMouseStroke(state=0, flags=1, rolling=0, x=abs_x, y=abs_y, information=0)
        eng.send_stroke(move)
    time.sleep(0.04)

    # The driver move must not leave the cursor short of the target.
    cur = wintypes.POINT()
    if u32.GetCursorPos(ctypes.byref(cur)) and (abs(cur.x - x) > 5 or abs(cur.y - y) > 5):
        u32.SetCursorPos(x, y)
        time.sleep(0.03)

    # 3. Interception Mouse Left Button Down (state=1)
    success = False
    if eng.is_ready:
        down = InterceptionMouseStroke(state=1, flags=0, rolling=0, x=0, y=0, information=0)
        if eng.send_stroke(down):
            success = True

    # Windows API fallback/auxiliary click event
    u32.mouse_event(0x0002, 0, 0, 0, 0)

    time.sleep(hold_time)

    # 4. Interception Mouse Left Button Up (state=2)
    if eng.is_ready:
        up = InterceptionMouseStroke(state=2, flags=0, rolling=0, x=0, y=0, information=0)
        if eng.send_stroke(up):
            success = True

    u32.mouse_event(0x0004, 0, 0, 0, 0)
    return success

def hold_click_at(x: int, y: int, hold_time: float = 0.3) -> bool:
    """Execute a driver-level click at physical screen coordinate (x, y),
    holding the button down for hold_time seconds before releasing.

    Verified-accepted-by-game pipeline: single mouse device (first discovered),
    interception strokes only -- no mouse_event fallback (its LLMHF_INJECTED
    flag makes the game discard the click).

    Cursor positioning uses a driver-level ABSOLUTE move, not SetCursorPos:
    SetCursorPos silently fails after attach_desktop() and produces no raw
    input, so the game's internal cursor never reaches buttons that require
    hover. The driver move maps onto the PRIMARY monitor; for off-primary
    targets we fall back to SetCursorPos (without attach_desktop, which breaks
    it). Requires the driver; returns False without it.
    """
    u32 = ctypes.windll.user32

    eng = InterceptionEngine.get()
    if not eng.is_ready:
        return False

    # 1. Activate target window under coordinate
    pt = wintypes.POINT(x, y)
    hwnd = u32.WindowFromPoint(pt)
    if hwnd:
        root_hwnd = u32.GetAncestor(hwnd, 2) or hwnd
        force_foreground(root_hwnd)

    # 2. Move the cursor, then verify and retry once (anti-cheat occasionally
    # swallows a stroke; SetCursorPos is blocked while the game is foreground).
    dev = eng._devices[0] if eng._devices else 11
    for _attempt in range(2):
        if _in_primary(x, y):
            abs_x, abs_y = screen_to_interception(x, y)
            move = InterceptionMouseStroke(state=0, flags=1, rolling=0, x=abs_x, y=abs_y, information=0)
            eng.send_stroke_to(dev, move)
        else:
            u32.SetCursorPos(x, y)
        time.sleep(0.05)
        cur = wintypes.POINT()
        if u32.GetCursorPos(ctypes.byref(cur)) and abs(cur.x - x) <= 5 and abs(cur.y - y) <= 5:
            break

    # 3. Button down/up on a single device
    down = InterceptionMouseStroke(state=1, flags=0, rolling=0, x=0, y=0, information=0)
    ok_down = eng.send_stroke_to(dev, down)
    time.sleep(hold_time)
    up = InterceptionMouseStroke(state=2, flags=0, rolling=0, x=0, y=0, information=0)
    ok_up = eng.send_stroke_to(dev, up)
    return ok_down and ok_up

def wheel_up(delta: int = 120) -> bool:
    """Scroll the mouse wheel up once (kernel-level stroke + Windows API fallback)."""
    u32 = ctypes.windll.user32
    eng = InterceptionEngine.get()
    success = False
    if eng.is_ready:
        stroke = InterceptionMouseStroke(state=INTERCEPTION_MOUSE_WHEEL, flags=0,
                                         rolling=delta, x=0, y=0, information=0)
        success = eng.send_stroke(stroke)
    # Windows API fallback/auxiliary wheel event (MOUSEEVENTF_WHEEL = 0x0800)
    u32.mouse_event(0x0800, 0, 0, delta, 0)
    return success

def press_key(scan_code: int, hold_time: float = 0.05) -> bool:
    """Press and release a key by scan code (kernel-level stroke + Windows API fallback)."""
    u32 = ctypes.windll.user32
    eng = InterceptionEngine.get()
    success = False
    if eng.is_ready:
        down = InterceptionKeyStroke(code=scan_code, info=INTERCEPTION_KEY_DOWN, information=0)
        success = eng.send_key_stroke(down)
    # Windows API fallback/auxiliary key event (KEYEVENTF_SCANCODE = 0x0008)
    u32.keybd_event(0, scan_code, 0x0008, 0)
    time.sleep(hold_time)
    if eng.is_ready:
        up = InterceptionKeyStroke(code=scan_code, info=INTERCEPTION_KEY_UP, information=0)
        success = eng.send_key_stroke(up) or success
    # KEYEVENTF_KEYUP = 0x0002
    u32.keybd_event(0, scan_code, 0x0008 | 0x0002, 0)
    return success

def release_skill(slot_id: int, averager: CoordinateAverager, mon: MonitorInfo) -> Tuple[bool, str]:
    """Execute click for chosen skill slot based on calibrated average coordinates."""
    if slot_id not in averager.slots:
        return False, f"非法槽位编号: {slot_id}"

    stat = averager.slots[slot_id].to_dict()
    if stat["count"] <= 0:
        return False, f"技能 {slot_id} 尚未采集到坐标，请先执行单次或循环检测！"

    ax, ay = stat["avg_x_int"], stat["avg_y_int"]
    target_x = mon.left + ax
    target_y = mon.top + ay

    ok = click_at(target_x, target_y)
    status_tag = "驱动级成功" if ok else "基础事件发送"
    return True, f"释放技能 {slot_id} [{status_tag}] -> ({target_x}, {target_y}) (采样: {stat['count']}帧)"
