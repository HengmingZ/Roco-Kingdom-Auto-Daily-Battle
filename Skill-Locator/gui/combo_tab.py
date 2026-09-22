"""Combo (skill release sequence) automation tab.

Users drag skills from the palette into an ordered sequence (up to 10 steps),
reorder steps by dragging, remove them via right-click or the trash zone,
and execute the combo with kernel-level clicks at calibrated coordinates.
"""

from __future__ import annotations

import json
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

from inference.overlay import SLOT_PALETTE
from inference.clicker import click_at, hold_click_at, wheel_up, press_key, SCANCODE_1, SCANCODE_SPACE

MAX_STEPS = 10


class ComboTab(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, bg="#1e293b")
        self.app = app
        self.sequence: list[int] = []
        self._drag: dict | None = None
        self._running = False
        self._stop = False
        self._thread = None
        self._retry_locator = None
        self._build_ui()
        self._load_combo(silent=True)
        self._redraw()
        self.refresh_calibration_status()
        self.winfo_toplevel().bind("<Escape>", lambda _e: self._emergency_stop())

    # ------------------------------------------------------------------ UI --

    def _build_ui(self) -> None:
        c_bg, t_col = "#1e293b", "#f8fafc"

        # 1. Calibration status
        cal = tk.LabelFrame(self, text=" 校准状态 (坐标来自技能校准页) ", bg=c_bg, fg=t_col,
                            padx=8, pady=4)
        cal.pack(fill=tk.X, padx=8, pady=6)
        self.cal_labels: dict[int, tk.Label] = {}
        for sid in range(1, 5):
            info = SLOT_PALETTE[sid]
            lbl = tk.Label(cal, text=f"{info['name']}: 未校准", bg=c_bg, fg="#f87171",
                           font=("Microsoft YaHei UI", 9))
            lbl.pack(side=tk.LEFT, padx=8)
            self.cal_labels[sid] = lbl
        tk.Button(cal, text="📂 重新加载校准文件", bg="#8b5cf6", fg="#fff", relief=tk.FLAT,
                  command=self.on_reload_calibration).pack(side=tk.RIGHT, padx=4)

        # 2. Skill palette (drag sources)
        pal = tk.LabelFrame(self, text=" 技能库 (拖拽到下方序列框，或双击追加) ",
                            bg=c_bg, fg=t_col, padx=8, pady=6)
        pal.pack(fill=tk.X, padx=8, pady=4)
        for sid in range(1, 5):
            info = SLOT_PALETTE[sid]
            lbl = tk.Label(pal, text=info["name"], bg=info["hex"], fg="#0f172a",
                           font=("Microsoft YaHei UI", 10, "bold"), width=10, height=2,
                           cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=8, pady=2)
            lbl.bind("<ButtonPress-1>", lambda e, s=sid: self._drag_start(e, "palette", s))
            lbl.bind("<B1-Motion>", self._drag_motion)
            lbl.bind("<ButtonRelease-1>", self._drag_release)
            lbl.bind("<Double-Button-1>", lambda _e, s=sid: self._append_skill(s))

        # 3. Sequence boxes
        seqf = tk.LabelFrame(self, text=" 连招序列 (最多 10 步；拖动调整顺序，右键或拖入回收站删除) ",
                             bg=c_bg, fg=t_col, padx=8, pady=6)
        seqf.pack(fill=tk.X, padx=8, pady=4)
        self.seq_container = tk.Frame(seqf, bg=c_bg)
        self.seq_container.pack(side=tk.LEFT, padx=2, pady=4)
        self.seq_boxes: list[tk.Label] = []
        for i in range(MAX_STEPS):
            box = tk.Label(self.seq_container, text=str(i + 1), width=6, height=3,
                           bg="#334155", fg="#64748b", font=("Microsoft YaHei UI", 8, "bold"),
                           highlightthickness=2, highlightbackground=c_bg, cursor="hand2")
            box.grid(row=0, column=i, padx=2, pady=3)
            box.bind("<ButtonPress-1>", lambda e, idx=i: self._on_box_press(e, idx))
            box.bind("<B1-Motion>", self._drag_motion)
            box.bind("<ButtonRelease-1>", self._drag_release)
            box.bind("<Button-3>", lambda _e, idx=i: self._remove_step(idx))
            self.seq_boxes.append(box)
        self.trash = tk.Label(seqf, text="🗑\n回收站", bg="#7f1d1d", fg="#fecaca",
                              font=("Microsoft YaHei UI", 8), width=5, height=3)
        self.trash.pack(side=tk.RIGHT, padx=4, pady=4)

        # 4. Execution controls
        ctrl = tk.LabelFrame(self, text=" 连招执行控制 ", bg=c_bg, fg=t_col, padx=8, pady=6)
        ctrl.pack(fill=tk.X, padx=8, pady=6)

        row1 = tk.Frame(ctrl, bg=c_bg)
        row1.pack(fill=tk.X, pady=(0, 4))
        tk.Label(row1, text="技能间隔(s):", bg=c_bg, fg=t_col).pack(side=tk.LEFT)
        self.var_interval = tk.StringVar(value="10")
        tk.Spinbox(row1, from_=0.1, to=10.0, increment=0.1, textvariable=self.var_interval,
                   width=6).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="循环次数(0=无限):", bg=c_bg, fg=t_col).pack(side=tk.LEFT, padx=(12, 2))
        self.var_repeat = tk.StringVar(value="1")
        tk.Spinbox(row1, from_=0, to=9999, increment=1, textvariable=self.var_repeat,
                   width=6).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="每轮结束自动执行: 滚轮上滚 → 1 → 空格 → (15s)屏幕中心三连击 | 按 ESC 紧急停止", bg=c_bg, fg="#94a3b8",
                 font=("Microsoft YaHei UI", 8)).pack(side=tk.RIGHT)

        row2 = tk.Frame(ctrl, bg=c_bg)
        row2.pack(fill=tk.X, pady=(2, 0))
        self.btn_run = tk.Button(row2, text="⚡ 开始连招", bg="#dc2626", fg="#fff",
                                 relief=tk.FLAT, font=("Microsoft YaHei UI", 10, "bold"),
                                 command=self.on_toggle_run)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(row2, text="💾 保存连招", bg="#f59e0b", fg="#0f172a", relief=tk.FLAT,
                  command=self.on_save_combo).pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="📂 读取连招", bg="#3b82f6", fg="#fff", relief=tk.FLAT,
                  command=lambda: self._load_combo(silent=False)).pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="🧹 清空序列", bg="#475569", fg="#fff", relief=tk.FLAT,
                  command=self.on_clear).pack(side=tk.LEFT, padx=2)

        row3 = tk.Frame(ctrl, bg=c_bg)
        row3.pack(fill=tk.X, pady=(2, 0))
        tk.Label(row3, text="收尾: 屏幕中心三连击 → OCR点击\"再次挑战\"", bg=c_bg, fg=t_col).pack(side=tk.LEFT)

        self.var_progress = tk.StringVar(value="尚未执行。")
        tk.Label(ctrl, textvariable=self.var_progress, bg=c_bg, fg="#38bdf8",
                 anchor="w").pack(fill=tk.X, pady=(4, 0))

    # ------------------------------------------------------------- drag/drop --

    def _drag_start(self, event, source: str, ref: int) -> None:
        if self._running:
            return
        sid = ref if source == "palette" else (self.sequence[ref] if ref < len(self.sequence) else None)
        if sid is None:
            return
        info = SLOT_PALETTE[sid]
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        tk.Label(ghost, text=info["name"], bg=info["hex"], fg="#0f172a",
                 font=("Microsoft YaHei UI", 10, "bold"), padx=10, pady=6).pack()
        ghost.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        self._drag = {"source": source, "ref": ref, "slot": sid, "ghost": ghost}

    def _drag_motion(self, event) -> None:
        if self._drag:
            self._drag["ghost"].geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

    def _drag_release(self, event) -> None:
        d = self._drag
        if not d:
            return
        self._drag = None
        d["ghost"].destroy()
        x, y = event.x_root, event.y_root
        box_idx = self._box_at(x, y)
        in_container = self._inside(self.seq_container, x, y)
        in_trash = self._inside(self.trash, x, y)

        if d["source"] == "palette":
            if box_idx is None and not in_container:
                return
            if len(self.sequence) >= MAX_STEPS:
                self.app.set_status(f"连招最多 {MAX_STEPS} 步，无法继续添加。")
                return
            at = box_idx if box_idx is not None else len(self.sequence)
            self.sequence.insert(min(at, len(self.sequence)), d["slot"])
        else:
            src = d["ref"]
            if src >= len(self.sequence):
                return
            if in_trash:
                self.sequence.pop(src)
            elif box_idx is not None or in_container:
                item = self.sequence.pop(src)
                if box_idx is None:
                    box_idx = len(self.sequence)
                elif box_idx > src:
                    box_idx -= 1
                self.sequence.insert(min(box_idx, len(self.sequence)), item)
        self._redraw()

    def _on_box_press(self, event, idx: int) -> None:
        if idx < len(self.sequence):
            self._drag_start(event, "seq", idx)

    def _box_at(self, x: int, y: int) -> int | None:
        for i, box in enumerate(self.seq_boxes):
            bx, by = box.winfo_rootx(), box.winfo_rooty()
            if bx <= x <= bx + box.winfo_width() and by <= y <= by + box.winfo_height():
                return i
        return None

    @staticmethod
    def _inside(widget, x: int, y: int) -> bool:
        wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
        return wx <= x <= wx + widget.winfo_width() and wy <= y <= wy + widget.winfo_height()

    def _append_skill(self, sid: int) -> None:
        if self._running:
            return
        if len(self.sequence) >= MAX_STEPS:
            self.app.set_status(f"连招最多 {MAX_STEPS} 步，无法继续添加。")
            return
        self.sequence.append(sid)
        self._redraw()

    def _remove_step(self, idx: int) -> None:
        if self._running or idx >= len(self.sequence):
            return
        self.sequence.pop(idx)
        self._redraw()

    def _redraw(self) -> None:
        for i, box in enumerate(self.seq_boxes):
            if i < len(self.sequence):
                sid = self.sequence[i]
                info = SLOT_PALETTE[sid]
                box.config(text=f"{i + 1}. {info['name']}", bg=info["hex"], fg="#0f172a")
            else:
                box.config(text=str(i + 1), bg="#334155", fg="#64748b")
        self.app.set_status(f"当前连招序列 ({len(self.sequence)}/{MAX_STEPS} 步): "
                            + (" -> ".join(f"技能{s}" for s in self.sequence) if self.sequence else "空"))

    # -------------------------------------------------------------- execution --

    def _emergency_stop(self) -> None:
        if self._running:
            self._stop = True
            self.app.set_status("收到停止指令，正在结束连招...")

    def on_toggle_run(self) -> None:
        if self._running:
            self._stop = True
            return
        if not self.sequence:
            messagebox.showwarning("序列为空", "请先从技能库拖拽技能到连招序列。")
            return
        missing = [sid for sid in dict.fromkeys(self.sequence)
                   if self.app.averager.slots[sid].count <= 0]
        if missing:
            messagebox.showwarning("缺少校准",
                                   f"技能 {', '.join(map(str, missing))} 尚未校准，请先在【技能校准】页采样或导入校准文件。")
            return
        try:
            interval = max(0.1, float(self.var_interval.get()))
        except ValueError:
            messagebox.showwarning("间隔无效",
                                   f"技能间隔 \"{self.var_interval.get()}\" 不是有效数字。\n请只输入秒数，例如 10 或 0.5。")
            return
        try:
            repeat = max(0, int(self.var_repeat.get()))
        except ValueError:
            messagebox.showwarning("循环次数无效",
                                   f"循环次数 \"{self.var_repeat.get()}\" 不是有效整数。\n请输入整数，0 表示无限循环。")
            return
        self._running, self._stop = True, False
        self.btn_run.config(text="⏹ 停止连招", bg="#475569")
        self._thread = threading.Thread(target=self._run_loop, args=(interval, repeat), daemon=True)
        self._thread.start()

    def _interruptible_sleep(self, seconds: float) -> None:
        end = time.time() + seconds
        while not self._stop and time.time() < end:
            time.sleep(0.05)

    def _run_loop(self, interval: float, repeat: int) -> None:
        app = self.app
        mon = app.current_monitor
        round_n = 0
        error = None
        fallback_warned = False
        try:
            for remaining in (3, 2, 1):
                if self._stop:
                    break
                self.after(0, self._on_countdown, remaining)
                self._interruptible_sleep(1.0)
            while not self._stop:
                for i, sid in enumerate(list(self.sequence)):
                    if self._stop:
                        break
                    stat = app.averager.slots[sid].to_dict()
                    if stat["count"] <= 0:
                        raise RuntimeError(f"技能 {sid} 校准数据失效，请重新校准后再执行。")
                    tx, ty = mon.left + stat["avg_x_int"], mon.top + stat["avg_y_int"]
                    self.after(0, self._on_step, i, sid, round_n + 1, tx, ty)
                    for click_n in range(3):
                        if self._stop:
                            break
                        if not click_at(tx, ty) and not fallback_warned:
                            fallback_warned = True
                            self.after(0, self._on_driver_fallback)
                        if click_n < 2:
                            self._interruptible_sleep(0.1)
                    self._interruptible_sleep(interval)
                if self._stop:
                    break
                self._post_round_actions(round_n + 1)
                round_n += 1
                if 0 < repeat <= round_n:
                    break
        except Exception as e:
            print(f"[Combo Error] {e}")
            error = e
        finally:
            self.after(0, self._on_run_finished, round_n, error)

    def _set_progress(self, text: str) -> None:
        self.after(0, lambda t=text: self.var_progress.set(t))

    def _get_retry_locator(self):
        if self._retry_locator is None:
            from inference.retry_locator import RetryButtonLocator
            self._retry_locator = RetryButtonLocator()
        return self._retry_locator

    def _post_round_actions(self, round_n: int) -> None:
        """每轮技能组释放完毕后的收尾操作: 滚轮上滚 -> (1s) 按 1 -> (1s) 按空格
        -> (15s) 屏幕中心三连击(每次按住0.3s) -> OCR定位"再次挑战"并点击。"""
        self._set_progress(f"第 {round_n} 轮技能组完成 | 收尾 1/5: 滚轮上滚")
        wheel_up()
        self._interruptible_sleep(1.0)
        if self._stop:
            return

        self._set_progress(f"第 {round_n} 轮 | 收尾 2/5: 按下 1")
        press_key(SCANCODE_1)
        self._interruptible_sleep(1.0)
        if self._stop:
            return

        self._set_progress(f"第 {round_n} 轮 | 收尾 3/5: 按下 空格")
        press_key(SCANCODE_SPACE)

        for remaining in range(15, 0, -1):
            if self._stop:
                return
            self._set_progress(f"第 {round_n} 轮 | 收尾 4/5: 等待屏幕中心三连击 ({remaining}s)")
            self._interruptible_sleep(1.0)
        if self._stop:
            return

        mon = self.app.current_monitor
        cx, cy = mon.left + mon.width // 2, mon.top + mon.height // 2
        for click_n in range(3):
            if self._stop:
                break
            self._set_progress(f"第 {round_n} 轮 | 收尾 4/5: 屏幕中心三连击 第 {click_n + 1}/3 击 (按住0.3s, 间隔0.5s) -> ({cx}, {cy})")
            if not hold_click_at(cx, cy, hold_time=0.3):
                self.after(0, self._on_driver_fallback)
            if click_n < 2:
                self._interruptible_sleep(0.5)
        if self._stop:
            return

        # 收尾 5/5: 三连击后结算页出现"再次挑战"，OCR 定位并点击（最多 3 次，消失即成功）
        locator = self._get_retry_locator()
        deadline = time.time() + 10.0
        clicks = 0
        while not self._stop and time.time() < deadline and clicks < 3:
            self._set_progress(f"第 {round_n} 轮 | 收尾 5/5: OCR 识别\"再次挑战\"...")
            found = locator.find(mon)
            if found is None:
                if clicks > 0:
                    self._set_progress(f"第 {round_n} 轮 | 收尾 5/5: \"再次挑战\"已消失，页面跳转成功 (点击 {clicks} 次)")
                    break
                self._set_progress(
                    f"第 {round_n} 轮 | 收尾 5/5: 等待\"再次挑战\"出现 ({max(0, int(deadline - time.time()))}s)")
                self._interruptible_sleep(1.0)
                continue
            x, y, score, text = found
            clicks += 1
            self._set_progress(f"第 {round_n} 轮 | 收尾 5/5: 点击[{text}] 第 {clicks} 次 (按住0.3s) -> ({x}, {y})")
            if not hold_click_at(x, y, hold_time=0.3):
                self.after(0, self._on_driver_fallback)
            self._interruptible_sleep(1.0)
        if clicks == 0 and not self._stop:
            self._set_progress(f"第 {round_n} 轮 | 收尾 5/5: 未识别到\"再次挑战\"，跳过")
        if clicks > 0:
            for remaining in range(6, 0, -1):
                if self._stop:
                    return
                self._set_progress(f"第 {round_n} 轮收尾完成 | 等待进入下一轮 ({remaining}s)")
                self._interruptible_sleep(1.0)

    def _on_countdown(self, remaining: int) -> None:
        self.var_progress.set(f"{remaining} 秒后开始连招，请点击游戏窗口激活... (ESC 取消)")

    def _on_driver_fallback(self) -> None:
        self.app.set_status(
            "警告: 驱动级点击未生效，当前仅依赖 Windows 基础事件（游戏里可能丢失点击）。"
            "请运行 driver_installer/install-interception.exe 安装驱动（需管理员并重启）。")

    def _on_step(self, idx: int, sid: int, round_n: int, tx: int, ty: int) -> None:
        for i, box in enumerate(self.seq_boxes):
            box.config(highlightbackground="#ffffff" if i == idx else "#1e293b")
        self.var_progress.set(f"第 {round_n} 轮 | 第 {idx + 1}/{len(self.sequence)} 步: "
                              f"{SLOT_PALETTE[sid]['name']} -> ({tx}, {ty})")

    def _on_run_finished(self, rounds: int, error: Exception | None = None) -> None:
        self._running = False
        self.btn_run.config(text="⚡ 开始连招", bg="#dc2626")
        for box in self.seq_boxes:
            box.config(highlightbackground="#1e293b")
        if error is not None:
            self.var_progress.set(f"连招异常中断 (完成 {rounds} 轮): {error}")
            self.app.set_status(f"连招执行出错: {error}")
        else:
            self.var_progress.set(f"连招结束，共完成 {rounds} 轮。")
            self.app.set_status(f"连招执行结束，共完成 {rounds} 轮。")

    # --------------------------------------------------------------- data I/O --

    @property
    def combo_file(self) -> str:
        return os.path.join(self.app.project_root, "configs", "skill_combos.json")

    def on_save_combo(self) -> None:
        data = {
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sequence": list(self.sequence),
            "interval": self.var_interval.get(),
            "repeat": self.var_repeat.get(),
        }
        os.makedirs(os.path.dirname(self.combo_file), exist_ok=True)
        with open(self.combo_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.app.set_status(f"连招已保存: {self.combo_file}")
        messagebox.showinfo("保存成功", f"连招序列已保存至:\n{self.combo_file}")

    def _load_combo(self, silent: bool) -> bool:
        try:
            with open(self.combo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            seq = [int(s) for s in data.get("sequence", []) if int(s) in SLOT_PALETTE]
        except (OSError, json.JSONDecodeError, ValueError):
            if not silent:
                self.app.set_status("未找到有效的连招配置文件。")
            return False
        self.sequence = seq[:MAX_STEPS]
        self.var_interval.set(str(data.get("interval", "10")))
        self.var_repeat.set(str(data.get("repeat", "1")))
        self._redraw()
        if not silent:
            self.app.set_status(f"已读取连招配置 ({len(self.sequence)} 步)。")
        return True

    def on_clear(self) -> None:
        if self._running:
            return
        self.sequence.clear()
        self._redraw()

    def on_reload_calibration(self) -> None:
        if self.app.load_calibration():
            self.refresh_calibration_status()
            if hasattr(self.app, "calibration_tab"):
                self.app.calibration_tab.refresh_table()
        else:
            messagebox.showwarning("加载失败",
                                   "未找到有效的校准文件 configs/calibrated_skill_coords.json。\n请先在【技能校准】页采样并导出。")

    def refresh_calibration_status(self) -> None:
        summary = self.app.averager.get_summary()
        for sid, lbl in self.cal_labels.items():
            s = summary[sid]
            if s["count"] > 0:
                lbl.config(text=f"{SLOT_PALETTE[sid]['name']}: [{s['avg_x_int']}, {s['avg_y_int']}]",
                           fg="#4ade80")
            else:
                lbl.config(text=f"{SLOT_PALETTE[sid]['name']}: 未校准", fg="#f87171")

    def shutdown(self) -> None:
        self._stop = True
