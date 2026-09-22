"""Backbone network definitions for Skill-Locator.
"""

from __future__ import annotations

from typing import Any, Tuple


class ConvBlock:
    """Helper descriptor for convolutional block."""
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, stride: int = 1) -> None:
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride


def build_backbone(name: str = "mobilenet_v3_small", pretrained: bool = True) -> Any:
    """Instantiate a lightweight feature extractor backbone."""
    try:
        import torch
        import torchvision.models as models

        if name == "mobilenet_v3_small":
            weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
            model = models.mobilenet_v3_small(weights=weights)
            # Remove classifier, keep feature extractor
            return model.features
        elif name == "resnet18":
            weights = models.ResNet18_Weights.DEFAULT if pretrained else None
            model = models.resnet18(weights=weights)
            # Exclude avgpool and fc
            return torch.nn.Sequential(*list(model.children())[:-2])
        else:
            raise ValueError(f"Unsupported backbone: {name}")
    except ImportError:
        return None
