"""Calibration tab: YOLO detection loop, sliding-window coordinate averaging,
and import/export of calibrated skill centers. Adapted from the legacy
ScreenTrackerApp loop, sharing grabber/predictor/averager from MainApp.
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple

from inference.overlay import SLOT_PALETTE


class CalibrationTab(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, bg="#1e293b")
        self.app = app
        self._running = False
        self._thread = None
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        c_bg, t_col = "#1e293b", "#f8fafc"

        ctrl = tk.LabelFrame(self, text=" 检测与采样控制 ", bg=c_bg, fg=t_col, padx=8, pady=6)
        ctrl.pack(fill=tk.X, padx=8, pady=6)

        sub1 = tk.Frame(ctrl, bg=c_bg)
        sub1.pack(fill=tk.X, pady=(0, 4))
        tk.Label(sub1, text="采样间隔(s):", bg=c_bg, fg=t_col).pack(side=tk.LEFT)
        self.var_interval = tk.StringVar(value="0.3")
        tk.Spinbox(sub1, from_=0.05, to=5.0, increment=0.1, textvariable=self.var_interval,
                   width=5).pack(side=tk.LEFT, padx=4)
        tk.Label(sub1, text="置信度阈值:", bg=c_bg, fg=t_col).pack(side=tk.LEFT, padx=(12, 2))
        self.var_conf = tk.DoubleVar(value=0.25)
        tk.Scale(sub1, from_=0.1, to=0.9, resolution=0.05, variable=self.var_conf,
                 orient=tk.HORIZONTAL, length=100, bg=c_bg, fg=t_col).pack(side=tk.LEFT)

        sub2 = tk.Frame(ctrl, bg=c_bg)
        sub2.pack(fill=tk.X, pady=(2, 0))
        self.btn_loop = tk.Button(sub2, text="▶ 循环检测并记录平均坐标", bg="#22c55e", fg="#fff",
                                  relief=tk.FLAT, font=("Microsoft YaHei UI", 9, "bold"),
                                  command=self.on_toggle_loop)
        self.btn_loop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(sub2, text="🎯 单次采样", bg="#3b82f6", fg="#fff", relief=tk.FLAT,
                  command=self.on_single_sample).pack(side=tk.LEFT, padx=2)
        tk.Button(sub2, text="🔄 重置数据", bg="#475569", fg="#fff", relief=tk.FLAT,
                  command=self.on_reset).pack(side=tk.LEFT, padx=2)
        tk.Button(sub2, text="💾 导出校准", bg="#f59e0b", fg="#0f172a", relief=tk.FLAT,
                  font=("Microsoft YaHei UI", 9, "bold"),
                  command=self.on_export).pack(side=tk.LEFT, padx=2)
        tk.Button(sub2, text="📂 导入校准", bg="#8b5cf6", fg="#fff", relief=tk.FLAT,
                  command=self.on_import).pack(side=tk.LEFT, padx=2)

        tbl = tk.LabelFrame(self, text=" 技能中心物理坐标看板 (平均坐标稳定计算) ",
                            bg=c_bg, fg=t_col, padx=6, pady=4)
        tbl.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        cols = ("slot", "count", "current", "avg_coord", "jitter", "conf")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings", height=5)
        for c, t, w in [("slot", "技能", 75), ("count", "采样数", 65), ("current", "当前单帧", 105),
                        ("avg_coord", "累计平均中心(X,Y)", 150), ("jitter", "抖动(±σ)", 95),
                        ("conf", "置信度", 70)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

    # --- sampling -----------------------------------------------------------

    def _sample_once(self) -> Tuple[list, float]:
        app = self.app
        t0 = time.time()
        frame = app.grabber.capture_screen(app.mon_idx)
        state = app.predictor.predict(frame, conf=self.var_conf.get())
        ms = (time.time() - t0) * 1000
        dets = [(s.slot_id, (s.bbox[0] + s.bbox[2]) // 2, (s.bbox[1] + s.bbox[3]) // 2,
                 s.confidence, s.bbox) for s in state.slots]
        app.averager.record_frame(dets)
        return dets, ms

    def _check_model(self) -> bool:
        if self.app.predictor is None:
            messagebox.showerror("模型不可用", "YOLO 模型加载失败，请检查 weights/best.pt 是否存在。")
            return False
        return True

    def on_single_sample(self) -> None:
        if not self._check_model():
            return
        _dets, ms = self._sample_once()
        self.refresh_table()
        self.app.set_status(f"单次采样完成 | 耗时: {ms:.1f}ms | 累计: {self.app.averager.total_frames} 帧")

    def on_toggle_loop(self) -> None:
        if not self._running:
            if not self._check_model():
                return
            self._running = True
            self.btn_loop.config(text="⏹ 停止检测", bg="#ef4444")
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        else:
            self._running = False
            self.btn_loop.config(text="▶ 循环检测并记录平均坐标", bg="#22c55e")
            self.app.set_status(f"循环已停止。共采样: {self.app.averager.total_frames} 帧。")

    def _loop(self) -> None:
        while self._running:
            t0 = time.time()
            try:
                interval = max(0.05, float(self.var_interval.get()))
            except ValueError:
                interval = 0.3
            try:
                _dets, ms = self._sample_once()
                if self._running:
                    self.after(0, self._on_frame, ms)
            except Exception as e:
                print(f"[Loop Error] {e}")
            time.sleep(max(0.01, interval - (time.time() - t0)))

    def _on_frame(self, ms: float) -> None:
        self.refresh_table()
        self.app.set_status(f"循环采样中... 已记录 {self.app.averager.total_frames} 帧 | 耗时: {ms:.1f}ms")

    # --- table / data ---------------------------------------------------------

    def refresh_table(self) -> None:
        summary = self.app.averager.get_summary()
        self.tree.delete(*self.tree.get_children())
        for sid in range(1, 5):
            s = summary[sid]
            name = SLOT_PALETTE.get(sid, {}).get("name", f"S{sid}")
            cur = f"({s['last_x']}, {s['last_y']})" if s["count"] > 0 else "--"
            avg = f"[{s['avg_x_int']}, {s['avg_y_int']}]" if s["count"] > 0 else "--"
            jit = f"±{s['std_x']}, ±{s['std_y']}" if s["count"] > 0 else "--"
            conf = f"{s['avg_conf']:.1%}" if s["count"] > 0 else "--"
            self.tree.insert("", tk.END, values=(name, s["count"], cur, avg, jit, conf))

    def on_reset(self) -> None:
        self.app.averager.reset()
        self.refresh_table()
        self.app.set_status("已重置所有坐标统计。")

    def on_export(self) -> None:
        app = self.app
        cfg = os.path.join(app.project_root, "configs", "calibrated_skill_coords.json")
        m = app.current_monitor
        app.averager.export_json(cfg, (m.width, m.height), m.device_name)
        app.set_status(f"校准坐标已导出: {cfg}")
        if hasattr(app, "combo_tab"):
            app.combo_tab.refresh_calibration_status()
        messagebox.showinfo("导出成功", f"技能校准坐标已保存至:\n{cfg}")

    def on_import(self) -> None:
        if self.app.load_calibration():
            self.refresh_table()
            if hasattr(self.app, "combo_tab"):
                self.app.combo_tab.refresh_calibration_status()
        else:
            messagebox.showwarning("导入失败", "未找到有效的校准文件 configs/calibrated_skill_coords.json。")

    def shutdown(self) -> None:
        self._running = False
