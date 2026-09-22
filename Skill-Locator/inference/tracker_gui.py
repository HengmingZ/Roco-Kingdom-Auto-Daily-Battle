"""GUI application for continuous skill detection, coordinate tracking, and execution.
Screen overlay drawing is completely removed to prevent screen blackout.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple

from capture.screen_grabber import ScreenGrabber, MonitorInfo
from inference.predictor import SkillPredictor
from inference.averager import CoordinateAverager
from inference.overlay import SLOT_PALETTE
from inference.clicker import release_skill


class ScreenTrackerApp:
    """Skill detector, coordinate tracker, and execution GUI (No Screen Overlay)."""

    def __init__(self, root: tk.Tk, project_root: str) -> None:
        self.root, self.project_root = root, project_root
        self.root.title("Skill-Locator 技能平均坐标检测与释放节点")
        self.root.geometry("660x570")
        self.root.configure(bg="#0f172a")

        self.grabber = ScreenGrabber()
        self.monitors: List[MonitorInfo] = self.grabber.get_monitors()
        self.mon_idx = next((i for i, m in enumerate(self.monitors) if m.is_primary), 0)

        self.predictor = SkillPredictor()
        self.averager = CoordinateAverager()

        self._running, self._thread = False, None
        self._build_ui()

    def _build_ui(self) -> None:
        c_bg, t_col = "#1e293b", "#f8fafc"

        # 1. Monitor Selector
        top = tk.Frame(self.root, bg=c_bg, padx=10, pady=6)
        top.pack(fill=tk.X)
        tk.Label(top, text="🎯 目标屏幕:", bg=c_bg, fg=t_col, font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.mon_combo = ttk.Combobox(top, state="readonly", values=[m.label for m in self.monitors], width=36)
        self.mon_combo.pack(side=tk.LEFT, padx=6)
        self.mon_combo.current(self.mon_idx)
        self.mon_combo.bind("<<ComboboxSelected>>", self.on_change_monitor)

        # 2. Control & Detection Bar
        ctrl = tk.LabelFrame(self.root, text=" 检测与释放控制 ", bg=c_bg, fg=t_col, padx=8, pady=6)
        ctrl.pack(fill=tk.X, padx=10, pady=6)

        sub1 = tk.Frame(ctrl, bg=c_bg)
        sub1.pack(fill=tk.X, pady=(0, 4))
        tk.Label(sub1, text="采样间隔(s):", bg=c_bg, fg=t_col).pack(side=tk.LEFT)
        self.var_interval = tk.StringVar(value="0.3")
        tk.Spinbox(sub1, from_=0.05, to=5.0, increment=0.1, textvariable=self.var_interval, width=5).pack(side=tk.LEFT, padx=4)
        tk.Label(sub1, text="置信度阈值:", bg=c_bg, fg=t_col).pack(side=tk.LEFT, padx=(12, 2))
        self.var_conf = tk.DoubleVar(value=0.25)
        tk.Scale(sub1, from_=0.1, to=0.9, resolution=0.05, variable=self.var_conf, orient=tk.HORIZONTAL, length=100, bg=c_bg, fg=t_col).pack(side=tk.LEFT)

        sub2 = tk.Frame(ctrl, bg=c_bg)
        sub2.pack(fill=tk.X, pady=(2, 4))
        self.btn_loop = tk.Button(sub2, text="▶ 循环检测并记录平均坐标", bg="#22c55e", fg="#fff", relief=tk.FLAT, font=("Microsoft YaHei UI", 9, "bold"), command=self.on_toggle_loop)
        self.btn_loop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(sub2, text="🎯 单次采样", bg="#3b82f6", fg="#fff", relief=tk.FLAT, command=self.on_single_sample).pack(side=tk.LEFT, padx=2)
        tk.Button(sub2, text="🔄 重置数据", bg="#475569", fg="#fff", relief=tk.FLAT, command=self.on_reset).pack(side=tk.LEFT, padx=2)
        tk.Button(sub2, text="💾 导出JSON", bg="#f59e0b", fg="#0f172a", relief=tk.FLAT, font=("Microsoft YaHei UI", 9, "bold"), command=self.on_export).pack(side=tk.LEFT, padx=2)

        # 3. Skill Release Section
        sub3 = tk.Frame(ctrl, bg=c_bg)
        sub3.pack(fill=tk.X, pady=(2, 0))
        tk.Label(sub3, text="技能释放:", bg=c_bg, fg="#38bdf8", font=("Microsoft YaHei UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.var_slot = tk.IntVar(value=1)
        for i in range(1, 5):
            tk.Radiobutton(sub3, text=f"技能 {i}", variable=self.var_slot, value=i, bg=c_bg, fg=t_col, selectcolor="#0f172a").pack(side=tk.LEFT, padx=4)
        tk.Button(sub3, text="⚡ 释放所选技能", bg="#dc2626", fg="#fff", font=("Microsoft YaHei UI", 9, "bold"), relief=tk.FLAT, padx=10, command=self.on_release_skill).pack(side=tk.RIGHT)

        # 4. Statistics Table
        tbl = tk.LabelFrame(self.root, text=" 技能中心物理坐标看板 (平均坐标稳定计算) ", bg=c_bg, fg=t_col, padx=6, pady=4)
        tbl.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        cols = ("slot", "count", "current", "avg_coord", "jitter", "conf")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings", height=5)
        for c, t, w in [("slot", "技能", 75), ("count", "采样数", 65), ("current", "当前单帧", 105), ("avg_coord", "累计平均中心(X,Y)", 150), ("jitter", "抖动(±σ)", 95), ("conf", "置信度", 70)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 5. Status Bar
        self.var_status = tk.StringVar(value="就绪。点击【循环检测】记录坐标，或选中技能点击【释放所选技能】。")
        tk.Label(self.root, textvariable=self.var_status, bg=c_bg, fg="#94a3b8", anchor="w", padx=8).pack(fill=tk.X, side=tk.BOTTOM)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._refresh_table()

    def on_change_monitor(self, _=None) -> None:
        self.mon_idx = self.mon_combo.current()
        m = self.monitors[self.mon_idx]
        self.on_reset()
        self.var_status.set(f"已切换至屏幕: {m.label}")

    def on_release_skill(self) -> None:
        """Trigger mouse click at calibrated average coordinate of the chosen skill."""
        ok, msg = release_skill(self.var_slot.get(), self.averager, self.monitors[self.mon_idx])
        self.var_status.set(msg)
        if not ok:
            messagebox.showwarning("无法释放技能", msg)

    def _sample_once(self) -> Tuple[list, float]:
        t0 = time.time()
        frame = self.grabber.capture_screen(self.mon_idx)
        state = self.predictor.predict(frame, conf=self.var_conf.get())
        ms = (time.time() - t0) * 1000
        dets = [(s.slot_id, (s.bbox[0]+s.bbox[2])//2, (s.bbox[1]+s.bbox[3])//2, s.confidence, s.bbox) for s in state.slots]
        self.averager.record_frame(dets)
        return dets, ms

    def _refresh_table(self, dets=None) -> None:
        summary = self.averager.get_summary()
        self.tree.delete(*self.tree.get_children())
        for sid in range(1, 5):
            s = summary[sid]
            name = SLOT_PALETTE.get(sid, {}).get("name", f"S{sid}")
            cur = f"({s['last_x']}, {s['last_y']})" if s["count"] > 0 else "--"
            avg = f"[{s['avg_x_int']}, {s['avg_y_int']}]" if s["count"] > 0 else "--"
            jit = f"±{s['std_x']}, ±{s['std_y']}" if s["count"] > 0 else "--"
            conf = f"{s['avg_conf']:.1%}" if s["count"] > 0 else "--"
            self.tree.insert("", tk.END, values=(name, s["count"], cur, avg, jit, conf))

    def on_single_sample(self) -> None:
        dets, ms = self._sample_once()
        self._refresh_table(dets)
        m = self.monitors[self.mon_idx]
        self.var_status.set(f"单次采样完成 | 耗时: {ms:.1f}ms | 累计: {self.averager.total_frames} 帧")

    def on_toggle_loop(self) -> None:
        if not self._running:
            self._running = True
            self.btn_loop.config(text="⏹ 停止检测", bg="#ef4444")
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        else:
            self._running = False
            self.btn_loop.config(text="▶ 循环检测并记录平均坐标", bg="#22c55e")
            self.var_status.set(f"循环已停止。共采样: {self.averager.total_frames} 帧。")

    def _loop(self) -> None:
        while self._running:
            t0 = time.time()
            try:
                interval = max(0.05, float(self.var_interval.get()))
            except ValueError:
                interval = 0.3
            try:
                dets, ms = self._sample_once()
                if self._running:
                    self.root.after(0, self._on_frame, dets, ms)
            except Exception as e:
                print(f"[Loop Error] {e}")
            time.sleep(max(0.01, interval - (time.time() - t0)))

    def _on_frame(self, dets, ms) -> None:
        self._refresh_table(dets)
        self.var_status.set(f"循环采样中... 已记录 {self.averager.total_frames} 帧 | 耗时: {ms:.1f}ms")

    def on_reset(self) -> None:
        self.averager.reset()
        self._refresh_table()
        self.var_status.set("已重置所有坐标统计。")

    def on_export(self) -> None:
        cfg = os.path.join(self.project_root, "configs", "calibrated_skill_coords.json")
        m = self.monitors[self.mon_idx]
        self.averager.export_json(cfg, (m.width, m.height), m.device_name)
        messagebox.showinfo("导出成功", f"技能校准坐标已保存至:\n{cfg}")

    def on_close(self) -> None:
        self._running = False
        self.root.destroy()
