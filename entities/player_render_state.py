"""
Player animation-state resolver.

Derives the canonical animation state name for a Player entity from its
current PhysicsState and PlayerState flags.  Used by:

  - demo_game.py          — local player sprite selection (60 Hz render loop)
  - game/game_simulator.py — server-side anim_state serialised into PlayerState
                             snapshots so remote observers show accurate animations

Keeping this logic in one place ensures the server and client always agree on
which animation state a given set of flags maps to.
"""

from __future__ import annotations


def compute_anim_state(player: object) -> str:
    """
    Return the animation state name for *player* based on its current flags.

    The priority order mirrors the local render loop in demo_game.py so the
    server snapshot and the local display always agree.

    Args:
        player: A Player instance with a `.state` attribute carrying
                `.physics` (PhysicsState) and action-flag fields.

    Returns:
        A string matching a key in PLAYER_ANIM_DEFS, e.g. "idle", "run",
        "dash", "slash1", "hurt", "teleport", etc.
    """
    physics = player.state.physics
    state = player.state

    if state.health_state.current_hp <= 0:
        return "death"
    if state.health_state.invincibility_frames > 0:
        return "hurt"
    if state.is_teleporting_phase or state.is_teleporting_invuln:
        return "teleport"
    if state.ninjutsu_casting:
        return "ninjutsu_summon"
    if state.ninjutsu_active:
        return "ninjutsu_hand"
    if state.is_throwing:
        if not physics.on_ground:
            return "throw_air"
        if state.crouching:
            return "throw_crouch"
        return "throw_ground"
    if state.is_air_attacking or (not physics.on_ground and getattr(state, "attack_stage", 0) > 0):
        return "slash_air"
    if state.attack_stage == 1:
        return "slash1"
    if state.attack_stage == 2:
        return "slash2"
    if state.attack_stage >= 3:
        return "slash3"
    if state.is_dashing:
        return "dash"
    if state.is_wall_hanging:
        return "wall_hang"
    if state.is_ceiling_hanging:
        return "ceiling_hang"
    if not physics.on_ground:
        if physics.on_wall:
            return "wall_slide"
        if state.jumps_left < state.max_jumps:
            return "air_spin"
        if physics.vy < 0:
            return "jump"
        return "fall"
    if state.crouching:
        return "crouch"
    vx_abs = abs(physics.vx)
    # Fast movement (>5 px/frame) always shows "run" regardless of the run modifier
    # key, matching the pre-v0.9.14 _infer_anim_state threshold so observers see a
    # running sprite whenever the player is actually running at speed.
    if vx_abs > 5.0:
        return "run"
    if getattr(state, "is_running", False) and vx_abs > 0.5:
        return "run"
    if vx_abs > 0.5:
        return "slow_walk"
    return "idle"
