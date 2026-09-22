"""Model evaluation and metrics calculation for Skill-Locator.
"""

from __future__ import annotations

import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def evaluate_model(weights_path: str, data_dir: str) -> None:
    print(f"[Evaluate] Loading weights from {weights_path}")
    print(f"[Evaluate] Evaluating on test set from {data_dir}")
    print("[Evaluate] Metrics: Top-1 Accuracy: N/A (Awaiting dataset)")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Skill-Locator model.")
    parser.add_argument(
        "--weights",
        "-w",
        default=os.path.join(PROJECT_ROOT, "weights", "best.pt"),
        help="Path to trained weights",
    )
    parser.add_argument(
        "--data",
        "-d",
        default=os.path.join(PROJECT_ROOT, "data", "cropped"),
        help="Path to evaluation dataset",
    )
    args = parser.parse_args()
    evaluate_model(args.weights, args.data)


if __name__ == "__main__":
    main()
