"""Screen capture module with multi-monitor support for Skill-Locator.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import struct
from typing import Optional, Tuple, Any, List

# [UPDATE - 2026-09-12]
# Reason: Extract win32 structures to win32_defs.py to keep file under 200 lines.
# Modification: Imported structs from capture.win32_defs.
from capture.win32_defs import (
    RECT, MONITORINFOEX, BITMAPINFOHEADER, MonitorInfo,
    SM_CXSCREEN, SM_CYSCREEN, SRCCOPY, DIB_RGB_COLORS, BI_RGB
)


class ScreenGrabber:
    """Multi-monitor screen capture engine using native Windows GDI."""

    def __init__(self, backend: str = "auto") -> None:
        self._u32 = ctypes.windll.user32
        self._g32 = ctypes.windll.gdi32
        try:
            self._u32.SetProcessDPIAware()
        except Exception:
            pass
        self.cached_monitors: List[MonitorInfo] = []
        self.get_monitors()

    def get_monitors(self) -> List[MonitorInfo]:
        """Enumerate all connected physical/logical monitors."""
        monitors: List[MonitorInfo] = []
        CMPPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)

        def _enum_proc(hmon, hdc, lprc, lparam):
            mi = MONITORINFOEX()
            mi.cbSize = ctypes.sizeof(MONITORINFOEX)
            if self._u32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                dev, l, t, r, b = mi.szDevice, int(mi.rcMonitor.left), int(mi.rcMonitor.top), int(mi.rcMonitor.right), int(mi.rcMonitor.bottom)
                w, h = max(1, r - l), max(1, b - t)
                is_pri = bool(mi.dwFlags & 1)
                idx = len(monitors)
                monitors.append(MonitorInfo(
                    index=idx, device_name=dev, left=l, top=t, right=r, bottom=b,
                    width=w, height=h, is_primary=is_pri,
                    label=f"屏幕 {idx + 1}{' (主屏幕)' if is_pri else ''} - {w}x{h} [{dev}]"
                ))
            return True

        self._u32.EnumDisplayMonitors(0, 0, CMPPROC(_enum_proc), 0)
        if not monitors:
            w, h = int(self._u32.GetSystemMetrics(SM_CXSCREEN)), int(self._u32.GetSystemMetrics(SM_CYSCREEN))
            monitors.append(MonitorInfo(0, "DISPLAY", 0, 0, w, h, w, h, True, f"屏幕 1 (主屏幕) - {w}x{h}"))
        self.cached_monitors = monitors
        return monitors

    # [UPDATE - 2026-09-12]
    # Reason: Restore get_primary_resolution method for backward compatibility.
    # Modification: Added get_primary_resolution returning width and height.
    def get_primary_resolution(self) -> Tuple[int, int]:
        for m in self.cached_monitors:
            if m.is_primary:
                return m.width, m.height
        return (self.cached_monitors[0].width, self.cached_monitors[0].height) if self.cached_monitors else (1920, 1080)

    def capture_screen(self, monitor_index: int = 0) -> Any:
        """Capture the screen of a specific monitor by index."""
        if not self.cached_monitors or monitor_index >= len(self.cached_monitors):
            self.get_monitors()
        mon = self.cached_monitors[monitor_index if monitor_index < len(self.cached_monitors) else 0]
        return self._capture_display_dc(mon.device_name, mon.width, mon.height)

    def capture_primary_screen(self) -> Any:
        for i, m in enumerate(self.cached_monitors):
            if m.is_primary:
                return self.capture_screen(i)
        return self.capture_screen(0)

    def _capture_display_dc(self, dev: str, w: int, h: int) -> Any:
        hdc = self._g32.CreateDCW(dev, None, None, None) or self._u32.GetDC(0)
        hdc_mem = self._g32.CreateCompatibleDC(hdc)
        hbm = self._g32.CreateCompatibleBitmap(hdc, w, h)
        hbm_old = self._g32.SelectObject(hdc_mem, hbm)

        self._g32.BitBlt(hdc_mem, 0, 0, w, h, hdc, 0, 0, SRCCOPY)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth, bmi.biHeight = w, -h
        bmi.biPlanes, bmi.biBitCount, bmi.biCompression = 1, 32, BI_RGB
        bmi.biSizeImage = w * h * 4

        buf = (ctypes.c_char * (w * h * 4))()
        self._g32.GetDIBits(hdc_mem, hbm, 0, h, ctypes.byref(buf), ctypes.cast(ctypes.byref(bmi), ctypes.c_void_p), DIB_RGB_COLORS)

        self._g32.SelectObject(hdc_mem, hbm_old)
        self._g32.DeleteObject(hbm)
        self._g32.DeleteDC(hdc_mem)
        self._g32.DeleteDC(hdc)

        raw_bytes = bytes(buf)
        try:
            import numpy as np
            return np.frombuffer(raw_bytes, dtype=np.uint8).reshape((h, w, 4))[:, :, :3]
        except ImportError:
            return raw_bytes, (w, h)

    def save_screenshot(self, filepath: str, monitor_index: int = 0) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        img = self.capture_screen(monitor_index)
        if hasattr(img, "shape"):
            import cv2
            cv2.imwrite(filepath, img)
            return filepath
        bmp_path = filepath if filepath.lower().endswith(".bmp") else filepath + ".bmp"
        raw = img[0] if isinstance(img, tuple) else bytes(img)
        w, h = (img[1] if isinstance(img, tuple) else (self.cached_monitors[0].width, self.cached_monitors[0].height))
        sz = len(raw)
        with open(bmp_path, "wb") as f:
            f.write(struct.pack("<2sIHHI", b"BM", 54 + sz, 0, 0, 54))
            f.write(struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 32, 0, sz, 2835, 2835, 0, 0))
            f.write(raw)
        return bmp_path
