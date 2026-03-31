"""
Remote player entity — multiplayer Phase N4.

Holds the last-known state of a player on another machine received via
MultiplayerSnapshot. No physics engine; position is updated directly from
network data and optionally smoothed with linear interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Width/height match the local player hitbox (28×56) so collision checks and
# rendering can use the same rect logic.
REMOTE_W = 28
REMOTE_H = 56


@dataclass
class RemotePlayer:
    """State holder for one networked peer player."""

    slot: int
    player_id: str

    # Current authoritative position (world coords, top-left of hitbox)
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0

    health: int = 5
    max_health: int = 5
    facing: int = 1       # 1 = right, -1 = left (matches local player convention)
    is_dead: bool = False

    # Previous position — used for interpolation
    prev_x: float = 0.0
    prev_y: float = 0.0

    # pygame.time.get_ticks() value (ms) when this player was last updated
    last_update_ms: float = 0.0

    # Display name shown above the health bar (e.g. "P2")
    display_name: str = ""

    # AnimationStateMachine — wired up externally after registry is loaded.
    # Use Any to avoid importing pygame at dataclass definition time.
    anim_sm: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = f"P{self.slot + 1}"

    def apply_state(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        health: int,
        facing: int,
        is_dead: bool,
        now_ms: float,
    ) -> None:
        """
        Update from a received PlayerState.
        Saves previous position so the renderer can interpolate.
        """
        self.prev_x = self.x
        self.prev_y = self.y
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.health = health
        self.facing = facing
        self.is_dead = is_dead
        self.last_update_ms = now_ms
        if self.anim_sm is not None:
            self.anim_sm.transition(self._infer_anim_state())

    def _infer_anim_state(self) -> str:
        """
        Derive an animation state name from current physics values.

        Uses the larger of reported vx and the positional delta (prev→current)
        as the speed signal.  This prevents the ghost from snapping to "idle"
        while interpolated_pos() is still sliding it toward the new position —
        keeping animation in sync with the visible movement.
        """
        if self.is_dead:
            return "death"
        if self.vy < -1.0:
            return "jump"
        if self.vy > 1.0:
            return "fall"
        speed = max(abs(self.vx), abs(self.x - self.prev_x))
        if speed > 5.0:
            return "run"
        if speed > 0.5:
            return "walk"
        return "idle"

    def interpolated_pos(self, now_ms: float, tick_ms: float = 16.67) -> tuple[float, float]:
        """
        Return a smoothed position between prev and current using linear
        interpolation based on time elapsed since the last server update.

        *tick_ms* is the expected server tick interval (default 16.67 ms = 60 Hz).
        t is clamped to [0, 1] so we never extrapolate beyond the latest known pos.
        """
        elapsed = now_ms - self.last_update_ms
        t = min(1.0, elapsed / tick_ms) if tick_ms > 0 else 1.0
        ix = self.prev_x + (self.x - self.prev_x) * t
        iy = self.prev_y + (self.y - self.prev_y) * t
        return ix, iy
