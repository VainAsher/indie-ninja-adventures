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
    facing: int = 1  # 1 = right, -1 = left (matches local player convention)
    is_dead: bool = False

    # Previous position — used for interpolation
    prev_x: float = 0.0
    prev_y: float = 0.0

    # pygame.time.get_ticks() value (ms) when this player was last updated
    last_update_ms: float = 0.0

    # Estimated server update interval (ms) for this player. Used to smooth
    # interpolated_pos() so ghosts don't snap then freeze when the server
    # broadcasts at < 60 Hz.
    update_interval_ms: float = 50.0

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
        anim_state: str = "",
    ) -> None:
        """
        Update from a received PlayerState.
        Saves previous position so the renderer can interpolate.

        *anim_state* is the resolved animation state name from the server
        (e.g. "dash", "slash1", "hurt").  When non-empty it is applied
        directly; when empty the local _infer_anim_state() heuristic is
        used as a fallback for older servers.
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

        # Track the real inter-update interval so interpolated_pos() can
        # adapt to the server's broadcast rate (commonly 20 Hz = 50 ms).
        if self.last_update_ms > 0.0:
            interval = now_ms - self.last_update_ms
            if interval > 0.0:
                # Exponential moving average to reduce jitter.
                self.update_interval_ms = 0.85 * self.update_interval_ms + 0.15 * interval
                # Clamp to sane bounds (ms)
                self.update_interval_ms = max(10.0, min(250.0, self.update_interval_ms))

        self.last_update_ms = now_ms
        if self.anim_sm is not None:
            resolved = anim_state if anim_state else self._infer_anim_state()
            # Don't interrupt a non-looping animation (attack, hurt, teleport,
            # throw, ninjutsu) that is still playing — let it finish.
            # Looping states (idle, walk, run, jump, fall, death) always yield.
            _LOOPING = {
                "idle",
                "walk",
                "run",
                "slow_walk",
                "jump",
                "fall",
                "crouch",
                "wall_slide",
                "air_spin",
                "death",
            }
            if self.anim_sm.state in _LOOPING or self.anim_sm.finished:
                self.anim_sm.transition(resolved)

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

    def interpolated_pos(self, now_ms: float, tick_ms: float | None = None) -> tuple[float, float]:
        """
        Return a smoothed position for rendering.

        Behaviour:
        - While elapsed < expected_ms: linearly interpolate prev→current.
        - When elapsed >= expected_ms (packet is late or we've reached the
          target): extrapolate X using the last known horizontal velocity to
          prevent the ghost from freezing mid-stride.  Y is kept at the
          authoritative target to avoid gravity-drift artifacts (the server
          will supply the correct Y in the next update).

        *tick_ms* is the expected server update interval. If None, uses the
        EMA-measured update interval from apply_state().

        Extrapolation is capped at 3 physics frames (~50 ms) so the ghost
        cannot diverge far from truth during a prolonged network gap.
        """
        expected_ms = self.update_interval_ms if tick_ms is None else tick_ms
        if expected_ms <= 0:
            expected_ms = 1.0
        elapsed = now_ms - self.last_update_ms

        if elapsed <= expected_ms:
            # Normal interpolation window — slide smoothly from prev to current.
            t = elapsed / expected_ms
            ix = self.prev_x + (self.x - self.prev_x) * t
            iy = self.prev_y + (self.y - self.prev_y) * t
        else:
            # Past the expected update time — extrapolate X to fill the gap.
            # vx is in px/frame (physics runs at 60 Hz = 16.667 ms/frame).
            extra_ms = elapsed - expected_ms
            extra_frames = min(extra_ms / 16.667, 3.0)  # cap at 3 frames ≈ 50 ms
            ix = self.x + self.vx * extra_frames
            iy = self.y  # keep Y authoritative; avoids floating/sinking artifacts

        return ix, iy
