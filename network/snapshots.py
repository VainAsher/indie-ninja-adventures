"""
Snapshot representation and deterministic serialization helpers.

Snapshot         — single-player replay snapshot (unchanged).
PlayerState      — one player's state in a multiplayer frame.
MultiplayerSnapshot — full frame state for up to N players.
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


# ──────────────────────────────────────────────────────────────────────────────
# Multiplayer snapshots
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class PlayerState:
    """Per-player state broadcast in a multiplayer frame."""

    player_id: str
    slot: int                          # 0 = host, 1 = first client, …
    pos: tuple[float, float]
    vel: tuple[float, float]
    health: int
    facing: int                        # 1 = right, -1 = left
    is_dead: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "slot": self.slot,
            "pos": list(self.pos),
            "vel": list(self.vel),
            "health": self.health,
            "facing": self.facing,
            "is_dead": self.is_dead,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerState":
        return cls(
            player_id=str(data["player_id"]),
            slot=int(data["slot"]),
            pos=(float(data["pos"][0]), float(data["pos"][1])),
            vel=(float(data["vel"][0]), float(data["vel"][1])),
            health=int(data["health"]),
            facing=int(data.get("facing", 1)),
            is_dead=bool(data.get("is_dead", False)),
        )


@dataclass
class MultiplayerSnapshot:
    """Full game-state frame for all connected players."""

    frame: int
    seed: int
    players: list[PlayerState]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "seed": self.seed,
            "players": [p.to_dict() for p in self.players],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MultiplayerSnapshot":
        return cls(
            frame=int(data["frame"]),
            seed=int(data["seed"]),
            players=[PlayerState.from_dict(p) for p in data.get("players", [])],
            metadata=dict(data.get("metadata", {})),
        )
