"""Schema definitions for Skill-Locator recognition outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class SkillSlot:
    """Represents the recognition result of a single skill slot."""
    slot_id: int
    name: str = "Unknown"
    confidence: float = 0.0
    pp_current: Optional[int] = None
    pp_max: Optional[int] = None
    is_usable: bool = True
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass
class BattleSkillsState:
    """Full battle interface skills state snapshot."""
    timestamp: float
    screen_resolution: Tuple[int, int]
    slots: List[SkillSlot] = field(default_factory=list)
