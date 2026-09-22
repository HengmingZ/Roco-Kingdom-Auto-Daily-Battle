"""Dummy transparent overlay placeholder (Drawing disabled).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

SLOT_PALETTE = {
    1: {"name": "技能 1", "hex": "#38bdf8"},
    2: {"name": "技能 2", "hex": "#4ade80"},
    3: {"name": "技能 3", "hex": "#facc15"},
    4: {"name": "技能 4", "hex": "#f87171"},
}


class TransparentOverlay:
    """Disabled overlay placeholder to prevent screen blackout."""

    def __init__(self, master=None, left: int = 0, top: int = 0, width: int = 0, height: int = 0) -> None:
        self.visible = False

    def reposition(self, left: int, top: int, width: int, height: int) -> None:
        pass

    def draw(self, dets: List[Tuple[int, int, int, float, Tuple[int, int, int, int]]], stats: Dict[int, dict], status: str = "") -> None:
        pass

    def clear(self) -> None:
        pass

    def destroy(self) -> None:
        pass
