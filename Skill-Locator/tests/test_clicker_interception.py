"""Standalone verification test for Interception driver clicking.
Tests Interception driver injection with interactive desktop attachment.
"""

import ctypes
from ctypes import wintypes
import os
import threading
import time
import tkinter as tk

class InterceptionMouseStroke(ctypes.Structure):
    _fields_ = [
        ("state", ctypes.c_ushort),
        ("flags", ctypes.c_ushort),
        ("rolling", ctypes.c_short),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("information", ctypes.c_uint),
    ]


class InterceptionDriverClicker:
    """Interception kernel driver mouse clicker replicating RocoKingdom_Clicker."""

    def __init__(self, dll_path: str):
        self.dll_path = dll_path
        self._lib = None
        self._ctx = None
        self._device = 11  # INTERCEPTION_MOUSE(1)
        self._init_driver()

    def _init_driver(self):
        if not os.path.exists(self.dll_path):
            raise FileNotFoundError(f"DLL not found: {self.dll_path}")
        self._lib = ctypes.CDLL(self.dll_path)
        self._lib.interception_create_context.restype = ctypes.c_void_p
        self._lib.interception_destroy_context.argtypes = [ctypes.c_void_p]
        self._lib.interception_send.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint
        ]
        self._lib.interception_send.restype = ctypes.c_int

        self._ctx = self._lib.interception_create_context()
        if not self._ctx:
            raise RuntimeError("Failed to create Interception context")

    def click_at(self, x: int, y: int, hold_time: float = 0.18) -> bool:
        u32 = ctypes.windll.user32
        h_desk = u32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            u32.SetThreadDesktop(h_desk)

        pt = wintypes.POINT(x, y)
        hwnd = u32.WindowFromPoint(pt)
        if hwnd:
            root_hwnd = u32.GetAncestor(hwnd, 2) or hwnd
            u32.SetForegroundWindow(root_hwnd)

        u32.SetCursorPos(x, y)
        time.sleep(0.04)

        down = InterceptionMouseStroke(state=1, flags=0, rolling=0, x=0, y=0, information=0)
        res_down = self._lib.interception_send(self._ctx, self._device, ctypes.byref(down), 1)

        time.sleep(hold_time)

        up = InterceptionMouseStroke(state=2, flags=0, rolling=0, x=0, y=0, information=0)
        res_up = self._lib.interception_send(self._ctx, self._device, ctypes.byref(up), 1)

        return bool(res_down > 0 and res_up > 0)

    def close(self):
        if self._lib and self._ctx:
            self._lib.interception_destroy_context(self._ctx)
            self._ctx = None


def run_test():
    dll = r"d:\sProject\GameTraining\RocoClicker\RocoKingdom_Clicker\interception.dll"
    clicker = InterceptionDriverClicker(dll)

    results = []

    u32 = ctypes.windll.user32
    h_desk = u32.OpenDesktopW("default", 0, False, 0x01FF)
    u32.SetThreadDesktop(h_desk)

    root = tk.Tk()
    root.title("Interception Click Test")
    root.geometry("300x200+500+300")

    btn = tk.Button(root, text="Target Button", font=("Arial", 16),
                    command=lambda: results.append("CLICK_RECEIVED"))
    btn.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    def trigger():
        hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
        u32.SetThreadDesktop(hd)
        time.sleep(0.5)

        bx = btn.winfo_rootx() + btn.winfo_width() // 2
        by = btn.winfo_rooty() + btn.winfo_height() // 2
        ok = clicker.click_at(bx, by, hold_time=0.18)
        print(f"Triggered click at ({bx}, {by}), ok={ok}")
        time.sleep(0.2)
        root.after(100, root.destroy)

    threading.Thread(target=trigger, daemon=True).start()
    root.mainloop()
    clicker.close()

    print("Test finished. Events caught:", results)
    assert "CLICK_RECEIVED" in results, "Failed: Button did not receive click event!"
    print("VERIFICATION SUCCESS: Interception kernel driver click delivered successfully!")


if __name__ == "__main__":
    run_test()
