"""YOLOv8 Training pipeline for Skill-Locator.

Trains YOLOv8n on annotated skill dataset using CUDA,
and exports best weights to .pt and .onnx.
"""

from __future__ import annotations

import os
import shutil
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ultralytics import YOLO
import torch

# [UPDATE - 2026-09-12]
# Reason: Train lightweight YOLO model on annotated skill dataset and export ONNX.
# Modification: Implemented training loop, device auto-detection (CUDA RTX 5060 Ti), and ONNX export.


def train_skill_detector(
    epochs: int = 60,
    imgsz: int = 640,
    batch_size: int = 8,
) -> None:
    weights_dir = os.path.join(PROJECT_ROOT, "weights")
    base_weights = os.path.join(weights_dir, "yolov8n.pt")
    config_yaml = os.path.join(PROJECT_ROOT, "configs", "yolo_dataset.yaml")
    runs_dir = os.path.join(weights_dir, "yolo_runs")

    device = "0" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"

    print("=" * 60)
    print("       Skill-Locator YOLOv8 模型训练")
    print("=" * 60)
    print(f"基础预训练权重: {base_weights}")
    print(f"数据集配置: {config_yaml}")
    print(f"计算硬件: CUDA [{device_name}]")
    print(f"训练参数: Epochs={epochs}, ImgSize={imgsz}, BatchSize={batch_size}")
    print("=" * 60)

    model = YOLO(base_weights)

    results = model.train(
        data=config_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        device=device,
        project=runs_dir,
        name="skill_detector",
        exist_ok=True,
        save=True,
        plots=True,
        workers=2,
    )

    print("\n[Training] 训练完成！正在整理模型权重...")

    # Copy best.pt to weights/best.pt
    best_train_pt = os.path.join(runs_dir, "skill_detector", "weights", "best.pt")
    target_best_pt = os.path.join(weights_dir, "best.pt")
    if os.path.exists(best_train_pt):
        shutil.copy2(best_train_pt, target_best_pt)
        print(f"[Training] 已导出最佳 PyTorch 权重: {target_best_pt}")

    # Export to ONNX
    print("[Training] 正在导出为 ONNX 格式...")
    try:
        best_model = YOLO(target_best_pt)
        exported_onnx = best_model.export(format="onnx", imgsz=imgsz, simplify=True)
        target_onnx = os.path.join(weights_dir, "skill_locator.onnx")
        if os.path.exists(exported_onnx):
            shutil.copy2(exported_onnx, target_onnx)
            print(f"[Training] 已导出生产环境 ONNX 权重: {target_onnx}")
    except Exception as e:
        print(f"[Training] ONNX 导出跳过或出错: {e}")

    print("=" * 60)
    print("       Skill-Locator 训练与导出流程顺利结束")
    print("=" * 60)


if __name__ == "__main__":
    train_skill_detector()
