"""Main GUI application with two tabs: skill calibration and combo automation.

Tab 1 (CalibrationTab): YOLO skill detection -> sliding-window coordinate
averaging -> export/import of calibrated skill centers.
Tab 2 (ComboTab): drag-and-drop skill release sequence (up to 10 steps)
executed via kernel-level clicks.
"""

from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from tkinter import ttk

if getattr(sys, "frozen", False):
    # PyInstaller bundle: resolve runtime files relative to the exe.
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capture.screen_grabber import ScreenGrabber, MonitorInfo
from inference.predictor import SkillPredictor
from inference.averager import CoordinateAverager

from gui.calibration_tab import CalibrationTab
from gui.combo_tab import ComboTab

CALIBRATION_FILE = os.path.join(PROJECT_ROOT, "configs", "calibrated_skill_coords.json")


class MainApp:
    """Shared state (grabber / predictor / averager / monitor) + notebook tabs."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.project_root = PROJECT_ROOT
        self.root.title("Skill-Locator 技能校准与自动连招")
        self.root.geometry("920x680")
        self.root.configure(bg="#0f172a")

        self.grabber = ScreenGrabber()
        self.monitors = self.grabber.get_monitors()
        self.mon_idx = next((i for i, m in enumerate(self.monitors) if m.is_primary), 0)

        model_path = os.path.join(PROJECT_ROOT, "weights", "best.pt")
        try:
            self.predictor = SkillPredictor(model_path=model_path)
        except Exception as e:
            self.predictor = None
            print(f"[WARN] 模型加载失败，检测功能不可用: {e}")

        self.averager = CoordinateAverager()
        self.load_calibration(CALIBRATION_FILE, silent=True)

        self._build_ui()

    @property
    def current_monitor(self) -> MonitorInfo:
        return self.monitors[self.mon_idx]

    def load_calibration(self, path: str = CALIBRATION_FILE, silent: bool = False) -> bool:
        """Import previously exported calibration centers into the averager."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            if not silent:
                self.set_status(f"校准文件不存在或已损坏: {path}")
            return False
        loaded = 0
        for sid_str, sk in data.get("skills", {}).items():
            center = sk.get("calibrated_center")
            if not str(sid_str).isdigit() or not center or sk.get("sample_count", 0) <= 0:
                continue
            sid = int(sid_str)
            if sid not in self.averager.slots:
                continue
            bbox = tuple(sk.get("last_bbox", (0, 0, 0, 0)))
            self.averager.slots[sid].add(int(center[0]), int(center[1]),
                                         sk.get("avg_confidence", 1.0), bbox)
            loaded += 1
        if loaded:
            self.set_status(f"已加载校准文件 ({loaded} 个技能): {path}")
        return loaded > 0

    def _build_ui(self) -> None:
        c_bg, t_col = "#1e293b", "#f8fafc"

        top = tk.Frame(self.root, bg=c_bg, padx=10, pady=6)
        top.pack(fill=tk.X)
        tk.Label(top, text="🎯 目标屏幕:", bg=c_bg, fg=t_col,
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.mon_combo = ttk.Combobox(top, state="readonly",
                                      values=[m.label for m in self.monitors], width=36)
        self.mon_combo.pack(side=tk.LEFT, padx=6)
        self.mon_combo.current(self.mon_idx)
        self.mon_combo.bind("<<ComboboxSelected>>", self.on_change_monitor)

        self.notebook = ttk.Notebook(self.root)
        self.calibration_tab = CalibrationTab(self.notebook, self)
        self.combo_tab = ComboTab(self.notebook, self)
        self.notebook.add(self.calibration_tab, text=" ① 技能校准 ")
        self.notebook.add(self.combo_tab, text=" ② 自动连招 ")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.notebook.bind("<<NotebookTabChanged>>",
                           lambda _e: self.combo_tab.refresh_calibration_status())

        self.var_status = tk.StringVar(value="就绪。先在【技能校准】页采样校准，再到【自动连招】页编排连招。")
        tk.Label(self.root, textvariable=self.var_status, bg=c_bg, fg="#94a3b8",
                 anchor="w", padx=8).pack(fill=tk.X, side=tk.BOTTOM)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_status(self, msg: str) -> None:
        if hasattr(self, "var_status"):
            self.var_status.set(msg)
        else:
            print(msg)

    def on_change_monitor(self, _=None) -> None:
        self.mon_idx = self.mon_combo.current()
        self.averager.reset()
        self.calibration_tab.refresh_table()
        self.combo_tab.refresh_calibration_status()
        self.set_status(f"已切换至屏幕: {self.monitors[self.mon_idx].label} (坐标统计已重置)")

    def on_close(self) -> None:
        self.calibration_tab.shutdown()
        self.combo_tab.shutdown()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
