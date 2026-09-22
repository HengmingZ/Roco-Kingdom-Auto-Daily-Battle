# Skill-Locator

精灵技能识别与定位系统。负责从游戏画面（主屏幕）中自动捕获战斗界面、定位技能槽位、裁剪 ROI，并通过深度学习/特征匹配模型识别技能类别与可用状态（PP 值、冷却与灰态）。

---

## 目录结构

```text
Skill-Locator/
├── configs/                     # 配置管理
│   ├── ui_roi.json              # 4个技能槽位与PP区域归一化坐标配置（0.0 ~ 1.0）
│   └── train_config.yaml        # 模型训练与导出配置
│
├── data/                        # 数据存储
│   ├── raw/                     # 游戏主屏幕原始全屏截图
│   ├── cropped/                 # ROI 裁剪后的技能小图样本
│   └── annotations/             # 标注数据文件（labels.json）
│
├── capture/                     # 画面捕获层（主屏幕）
│   ├── screen_grabber.py        # Windows GDI / mss 主屏幕捕获实现
│   └── __init__.py
│
├── dataset/                     # 数据构建与处理管道
│   ├── collector.py             # 主屏幕批量/定时截图采集工具
│   ├── preprocessor.py          # ROI 切片与图像归一化
│   └── skill_dataset.py         # 数据集加载器
│
├── models/                      # 神经网络架构
│   ├── backbone.py              # 特征提取网络（MobileNetV3 / ResNet）
│   └── skill_net.py             # 技能多任务网络（分类 + 状态判定）
│
├── training/                    # 训练与评估管道
│   ├── train.py                 # 模型训练主入口
│   └── evaluate.py              # 准确率评估脚本
│
├── weights/                     # 检查点与 ONNX 部署模型
│   └── skill_locator.onnx       # 导出的 ONNX 权重
│
├── inference/                   # 在线推理 API 封装
│   ├── predictor.py             # 技能预测主接口
│   ├── pp_recognizer.py         # PP 字符识别
│   └── schema.py                # 结构化输出类型定义
│
├── gui/                         # 统一 GUI（双页签）
│   ├── main_app.py              # 主窗口：共享屏幕/模型/校准数据 + 页签切换
│   ├── calibration_tab.py       # 页签① 技能校准：检测采样、平均坐标、导入/导出
│   └── combo_tab.py             # 页签② 自动连招：拖拽编排 ≤10 步序列并驱动级点击执行
│
└── tests/                       # 单元测试与验证脚本
    ├── test_capture.py          # 测试主屏幕截屏功能与分辨率识别
    └── test_inference.py        # 测试全流程推断管线
```

---

## 快速使用

### 1. 验证主屏幕截图
```bash
uv run tests/test_capture.py
```

### 2. 采集游戏主屏幕样本
```bash
uv run dataset/collector.py --count 10 --interval 1.5
```
截图将自动保存在 `data/raw/` 目录下。

### 3. 测试推断流程
```bash
uv run tests/test_inference.py
```

### 4. 启动统一 GUI（技能校准 + 自动连招）
```bash
run_main_gui.bat        # 自动请求管理员权限（驱动级点击所需）
# 或手动:
uv run gui/main_app.py
```
- **页签① 技能校准**：循环/单次采样 → 滑动窗口平均坐标 → 导出 `configs/calibrated_skill_coords.json`。
- **页签② 自动连招**：从技能库拖拽技能到序列框（最多 10 步），拖动调整顺序，右键或拖入回收站删除；设置技能间隔与循环次数后点击【开始连招】按顺序点击释放，按 `ESC` 紧急停止；连招配置可保存至 `configs/skill_combos.json`。
