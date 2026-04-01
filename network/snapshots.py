"""
Snapshot representation and deterministic serialization helpers.

Snapshot            — single-player replay snapshot (unchanged).
PlayerState         — one player's state in a multiplayer frame.
MultiplayerSnapshot — Phase 1/2.5 frame state for up to N players.
EnemyState          — one enemy's authoritative state (Phase 3).
PickupState         — one pickup's authoritative state (Phase 3).
PlatformState       — one falling/moving platform's state (Phase 3).
WorldSnapshot       — full authoritative world state (Phase 3).
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
    anim_state: str = ""               # resolved animation state name; "" = use inference

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "slot": self.slot,
            "pos": list(self.pos),
            "vel": list(self.vel),
            "health": self.health,
            "facing": self.facing,
            "is_dead": self.is_dead,
            "anim_state": self.anim_state,
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
            anim_state=str(data.get("anim_state", "")),
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


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3: Authoritative world state
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class EnemyState:
    """Authoritative state of one enemy entity."""

    enemy_id: str
    x: float
    y: float
    vx: float
    vy: float
    hp: int
    ai_state: str          # "idle" | "patrol" | "chase" | "attack" | "dead"
    facing_right: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "enemy_id": self.enemy_id,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "hp": self.hp,
            "ai_state": self.ai_state,
            "facing_right": self.facing_right,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnemyState":
        return cls(
            enemy_id=str(data["enemy_id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            vx=float(data["vx"]),
            vy=float(data["vy"]),
            hp=int(data["hp"]),
            ai_state=str(data["ai_state"]),
            facing_right=bool(data["facing_right"]),
        )


@dataclass
class PickupState:
    """Authoritative state of one pickup entity."""

    pickup_id: str
    x: float
    y: float
    pickup_type: str
    alive: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "pickup_id": self.pickup_id,
            "x": self.x,
            "y": self.y,
            "pickup_type": self.pickup_type,
            "alive": self.alive,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PickupState":
        return cls(
            pickup_id=str(data["pickup_id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            pickup_type=str(data["pickup_type"]),
            alive=bool(data["alive"]),
        )


@dataclass
class PlatformState:
    """Authoritative state of one falling or moving platform."""

    platform_id: str       # "plat_{origin_x}_{origin_y}"
    state: str             # "idle" | "triggered" | "falling" | "respawn"
    pos_y: float
    timer: float
    vy: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "state": self.state,
            "pos_y": self.pos_y,
            "timer": self.timer,
            "vy": self.vy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlatformState":
        return cls(
            platform_id=str(data["platform_id"]),
            state=str(data["state"]),
            pos_y=float(data["pos_y"]),
            timer=float(data["timer"]),
            vy=float(data["vy"]),
        )


@dataclass
class WorldSnapshot:
    """Full authoritative world state broadcast by the server each tick (Phase 3)."""

    frame: int
    seed: int
    players: list[PlayerState]
    enemies: list[EnemyState]
    pickups: list[PickupState]
    platform_states: list[PlatformState]
    metadata: dict[str, Any]
    hub_id: str = ""   # zone this snapshot belongs to; "" = pre-Phase-4 server

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "seed": self.seed,
            "players": [p.to_dict() for p in self.players],
            "enemies": [e.to_dict() for e in self.enemies],
            "pickups": [p.to_dict() for p in self.pickups],
            "platform_states": [ps.to_dict() for ps in self.platform_states],
            "metadata": self.metadata,
            "hub_id": self.hub_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldSnapshot":
        return cls(
            frame=int(data["frame"]),
            seed=int(data["seed"]),
            players=[PlayerState.from_dict(p) for p in data.get("players", [])],
            enemies=[EnemyState.from_dict(e) for e in data.get("enemies", [])],
            pickups=[PickupState.from_dict(p) for p in data.get("pickups", [])],
            platform_states=[PlatformState.from_dict(ps) for ps in data.get("platform_states", [])],
            metadata=dict(data.get("metadata", {})),
            hub_id=str(data.get("hub_id", "")),
        )
