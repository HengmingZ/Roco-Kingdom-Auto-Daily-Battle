"""SkillNet multi-task classification and state model architecture.
"""

from __future__ import annotations

from typing import Any, Tuple, Optional


class SkillNet:
    """Multi-task neural network for Skill Classification and Usability State Prediction."""

    def __init__(self, num_classes: int = 50, backbone_name: str = "mobilenet_v3_small") -> None:
        self.num_classes = num_classes
        self.backbone_name = backbone_name
        self.torch_module = self._build_model()

    def _build_model(self) -> Any:
        try:
            import torch
            import torch.nn as nn
            from .backbone import build_backbone

            class _PyTorchSkillNet(nn.Module):
                def __init__(self, n_classes: int, b_name: str):
                    super().__init__()
                    self.features = build_backbone(b_name, pretrained=False)
                    self.pool = nn.AdaptiveAvgPool2d((1, 1))
                    feature_dim = 576 if b_name == "mobilenet_v3_small" else 512

                    # Head 1: Skill ID Multi-class classifier
                    self.class_head = nn.Sequential(
                        nn.Linear(feature_dim, 256),
                        nn.ReLU(inplace=True),
                        nn.Dropout(0.2),
                        nn.Linear(256, n_classes),
                    )

                    # Head 2: Usability State (usable, grayed_out, cooling_down)
                    self.state_head = nn.Sequential(
                        nn.Linear(feature_dim, 64),
                        nn.ReLU(inplace=True),
                        nn.Linear(64, 2),  # 0: unusable, 1: usable
                    )

                def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
                    feat = self.features(x)
                    feat = self.pool(feat)
                    feat = torch.flatten(feat, 1)
                    logits_class = self.class_head(feat)
                    logits_state = self.state_head(feat)
                    return logits_class, logits_state

            return _PyTorchSkillNet(self.num_classes, self.backbone_name)
        except ImportError:
            return None
