"""
Snapshot representation and deterministic serialization helpers.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Snapshot:
    frame: int
    seed: int
    player_pos: tuple[float, float]
    player_vel: tuple[float, float]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        ordered_keys = ["frame", "seed", "player_pos", "player_vel", "metadata"]
        return {k: data[k] for k in ordered_keys}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            frame=int(data["frame"]),
            seed=int(data["seed"]),
            player_pos=tuple(data["player_pos"]),
            player_vel=tuple(data["player_vel"]),
            metadata=dict(data.get("metadata", {})),
        )
