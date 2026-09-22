"""Model training pipeline for Skill-Locator.
"""

from __future__ import annotations

import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def train_model(config_path: str) -> None:
    print(f"[Training] Loading configuration from {config_path}")
    print("[Training] Pipeline initialized.")
    # Placeholders for PyTorch training loop once dataset is collected


def main():
    parser = argparse.ArgumentParser(description="Train Skill-Locator model.")
    parser.add_argument(
        "--config",
        "-c",
        default=os.path.join(PROJECT_ROOT, "configs", "train_config.yaml"),
        help="Path to training config YAML",
    )
    args = parser.parse_args()
    train_model(args.config)


if __name__ == "__main__":
    main()
