"""
Snapshot representation and deterministic serialization helpers.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple


@dataclass
class Snapshot:
    frame: int
    seed: int
    player_pos: Tuple[float, float]
    player_vel: Tuple[float, float]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        ordered_keys = ["frame", "seed", "player_pos", "player_vel", "metadata"]
        return {k: data[k] for k in ordered_keys}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        return cls(
            frame=int(data["frame"]),
            seed=int(data["seed"]),
            player_pos=tuple(data["player_pos"]),
            player_vel=tuple(data["player_vel"]),
            metadata=dict(data.get("metadata", {})),
        )
