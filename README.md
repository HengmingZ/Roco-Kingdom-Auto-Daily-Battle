# Roco Kingdom Auto Daily Battle

《洛克王国：世界》自动日常战斗工具：YOLO 技能校准 + 拖拽编排连招 + 驱动级点击执行 + OCR 自动点击"再次挑战"。

## 功能特性

- **技能校准（页签①）**：YOLO 检测技能图标，滑动窗口平均坐标，一键导出/导入校准文件
- **自动连招（页签②）**：拖拽编排最多 10 步技能序列，自定义技能间隔与循环次数，`ESC` 紧急停止
- **驱动级输入**：基于 [Interception](https://github.com/oblitum/Interception) 内核驱动的鼠标/键盘注入，可穿透游戏反作弊对普通注入事件的拦截
- **收尾自动化（每轮连招后）**：滚轮上滚 → 按 `1` → 按 `空格` → (15s) 屏幕中心三连击 → **OCR 识别"再次挑战"按钮并自动点击** → 等待 6s 进入下一轮

## 环境要求

- Windows 10/11，Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- NVIDIA GPU 可选（CUDA 加速检测；CPU 也能跑）

## 安装与运行（源码）

```bash
git clone git@github.com:HengmingZ/Roco-Kingdom-Auto-Daily-Battle.git
cd Roco-Kingdom-Auto-Daily-Battle
uv sync
```

**首次使用必须安装 Interception 驱动**（否则游戏收不到点击）：

```bash
# 右键以管理员身份运行，装完重启电脑
driver_installer/install-interception.exe
```

**模型权重**不在仓库中，从 [Releases](../../releases) 下载 `best.pt` 放入 `Skill-Locator/weights/`（或按 GUI 提示的位置）。

启动（需管理员权限才能向游戏注入点击）：

```bash
cd Skill-Locator
run_main_gui.bat        # 自动请求管理员权限
# 或：uv run gui/main_app.py
```

## 使用流程

1. **技能校准页**：进入战斗界面 → 采样检测 → 导出校准
2. **自动连招页**：从技能库拖技能进序列 → 设置间隔/循环次数 →【开始连招】→ 3 秒倒计时内点击游戏窗口激活
3. 每轮结束后自动执行收尾流程，OCR 找到"再次挑战"即点击，找不到会提示并跳过

## 目录结构

```text
├── Skill-Locator/
│   ├── gui/               # 主程序（main_app.py：校准 + 连招双页签）
│   ├── inference/         # clicker(驱动注入) / predictor(YOLO) / retry_locator(OCR)
│   ├── capture/           # 多显示器 GDI 截图
│   ├── training/          # YOLO 训练管道
│   ├── configs/           # 校准坐标、连招配置、UI ROI
│   └── tests/             # 各功能独立测试脚本
├── driver_installer/      # Interception 驱动安装器 + interception.dll
├── weights/               # (git 排除) YOLO 权重，见 Releases
└── report/                # 排查报告
```

## 常见问题

- **点击无效/光标不动**：确认已安装驱动并重启；确认程序以管理员运行；游戏前台时 `SetCursorPos` 会被反作弊拦截，本工具使用驱动级绝对移动定位，光标应能真实跳转
- **OCR 找不到"再次挑战"**：运行 `uv run tests/test_retry_locator.py` 查看识别结果与标注截图（`tests/output/`）
- **单独验证收尾点击**：`uv run tests/test_ocr_clicker.py`（识别+点击链路）、`uv run tests/test_triple_click.py`（三连击模拟）

## 发布说明（维护者）

- 权重、OCR 相关产物通过 GitHub Releases 附件分发，不进入 git
- exe 打包：PyInstaller（`--uac-admin`，需收集 `rapidocr_onnxruntime` 与 `ultralytics` 数据文件）
