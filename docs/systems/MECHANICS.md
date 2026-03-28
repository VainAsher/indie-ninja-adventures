# Player Mechanics System

## Design Principle

Every player ability is a self-contained class that extends `BaseMechanic`
(`mechanics/base.py`). Mechanics communicate only through `PlayerState` and
the shared `EventBus`. No mechanic holds a reference to another mechanic or
to the `Player` object itself.

The `Player` class (`entities/player.py`) owns an ordered list `self.mechanics`
and calls each mechanic's `on_tick(state, dt)` in sequence every physics frame
(60 Hz). The processing order is fixed:

1. Crouch (produces movement multipliers used in step 2)
2. Movement
3. Dash
4. Jump
5. Wall slide
6. Shuriken
7. Teleport
8. Ninjutsu

`DamageMechanic` is not appended to `self.mechanics`; it is called explicitly
wherever hazard or enemy collision checks occur.

---

## Ability Gating

The `Player.__init__` receives an optional `feature_flags: dict`. Each entry
maps a flag name to a boolean:

```python
feature_flags = {
    "double_jump": True,
    "wall_jump":   True,
    "dash":        True,
    "crouch":      True,
    "shuriken":    True,
    "teleport":    True,
    "ninjutsu":    True,
}
```

`process_input()` checks the relevant flag before forwarding an input request
to a mechanic. For example:

```python
if self.feature_flags.get("dash", True):
    self.dash.request_dash()
```

`JumpMechanic` is a special case: `double_jump_enabled` and `wall_jump_enabled`
are baked into instance variables at construction time from the flags passed to
`__init__`. Changing `player.feature_flags` at runtime does not automatically
update these variables. The `sync_player_abilities(unlocked_abilities)` helper
in `demo_game.py` handles both the dict update and the manual sync:

```python
player.jump.double_jump_enabled = player.feature_flags.get("double_jump", False)
player.jump.wall_jump_enabled   = player.feature_flags.get("wall_jump", False)
```

Call `sync_player_abilities` whenever a campaign unlocks a new ability.
Crouch is intentionally excluded from gating — it is treated as a basic
navigation tool that is always active.

---

## BaseMechanic Interface

File: `mechanics/base.py`

| Method | Required | Description |
|---|---|---|
| `on_tick(state, dt)` | Yes | Called every 60 Hz tick; modifies PlayerState |
| `can_activate(state)` | Yes | Returns True when preconditions are met |
| `on_collision(state, event)` | No | Responds to CollisionEvent |
| `reset(state)` | No | Resets internal timers; called on respawn |
| `cleanup()` | No | Unsubscribes from EventBus; called on entity destroy |
| `enable() / disable()` | No | Sets `self.enabled`; checked at top of `on_tick` |

---

## Mechanics Reference

### MovementMechanic

File: `mechanics/movement.py`

Purpose: Applies smooth interpolation-based horizontal movement every tick.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `MAX_RUN_SPEED` | 8.0 | Maximum horizontal velocity (units/tick) |
| `MOVEMENT_ACCEL` | 2600.0 | Smooth interpolation constant |

Algorithm:

```
target_vx = direction * MAX_RUN_SPEED * speed_multiplier
smooth_factor = min(1.0, MOVEMENT_ACCEL * accel_multiplier * dt / MAX_RUN_SPEED)
vx += (target_vx - vx) * smooth_factor
```

The same algorithm is used on ground and in air (unified physics). Direction
is set via `set_input(-1 | 0 | 1)`. Movement is skipped entirely when
`movement_locked` is `True`.

Modifiers applied by `Player.on_tick` before calling this mechanic:

- Crouching: `speed_mult = 0.6`, `accel_mult = 0.8`
- Walking (no Alt key): `speed_mult = 0.6`, `accel_mult = 0.8`
- Running (Alt key held): `speed_mult = 1.0`, `accel_mult = 1.0`
- `environment_speed_mult` and `environment_accel_mult` on `PlayerState` are
  applied as additional multipliers for zone-specific effects.

`movement_locked` is set to `True` during an active dash or while
`wall_jump_lock > 0`.

Interactions:

- DashMechanic sets `movement_locked = True` via `Player.on_tick` while
  `state.is_dashing` is True.
- WallSlideMechanic's wall-jump coyote buffer is tracked in `Player.on_tick`,
  not here.
- CrouchMechanic calls `get_movement_modifier()` which is read back in
  `Player.on_tick` to set multipliers before calling `movement.on_tick`.

---

### JumpMechanic

File: `mechanics/jump.py`

Purpose: Unified handler for all jump types. A single `request_jump()` call
routes to whichever jump type is currently legal.

Key parameters (imported from `config/physics_constants.py`):

| Constant | Description |
|---|---|
| `JUMP_POWER` | Upward impulse for ground / coyote jump |
| `DOUBLE_JUMP_POWER` | Upward impulse for air jump |
| `WALL_JUMP_POWER_X` | Horizontal component of wall jump (applied at 0.5x in code) |
| `WALL_JUMP_POWER_Y` | Vertical component of wall jump |
| `JUMP_BUFFER_TIME` | 0.14 s — input buffering window |
| `CROUCH_JUMP_MULT` | 0.7 — jump power modifier when crouching |

Mechanic-level constants:

| Constant | Value | Description |
|---|---|---|
| `MAX_JUMPS` | 2 | Air jumps available after leaving ground |
| `WALL_JUMP_INPUT_LOCK` | 0.12 s | Horizontal input lock after wall jump |

Coyote time (0.12 s ground grace period) is managed in `Player.on_tick`, not
inside JumpMechanic. It sets `state.coyote_time = 0.12` when the player leaves
ground and counts it down each tick.

Jump priority (checked in order):

1. Ground jump or coyote jump — requires `on_ground` or `coyote_time > 0`
2. Wall jump — requires `on_wall` or `wall_coyote_time > 0`; costs 3 stamina;
   locks horizontal input for `WALL_JUMP_INPUT_LOCK` seconds
3. Double jump — requires `jumps_left > 0`; costs 3 stamina

Variable jump height: `Player.on_tick` applies extra gravity (`GRAVITY *
(JUMP_CUT_MULT - 1)`) when the player is rising and the jump key has been
released, producing short tap-for-low / hold-for-high behaviour.

`on_collision` resets `jumps_left` to `MAX_JUMPS` on a ground collision event.

Important: `double_jump_enabled` and `wall_jump_enabled` are instance variables
set at construction time from `feature_flags`. They are not re-read from the
dict on each tick. Use `sync_player_abilities()` to update them at runtime.

---

### DashMechanic

File: `mechanics/dash.py`

Purpose: Grants a brief burst of high-speed horizontal movement with a
fixed cooldown.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `DASH_SPEED` | 16.0 | Velocity override during dash (double normal max) |
| `DASH_DURATION` | 0.16 s | ~10 frames at 60 Hz |
| `DASH_COOLDOWN` | 0.45 s | ~27 frames; starts after dash ends or is cancelled |

State machine:

- Ready: `dash_cooldown == 0` and `is_dashing == False`
- Dashing: `is_dashing == True`, `dash_time` counting down
- Cooldown: `is_dashing == False`, `dash_cooldown > 0`

During a dash, `vx` is overridden to `facing * DASH_SPEED` each tick. Normal
MovementMechanic processing is locked via `movement_locked`.

Dash is cancelled immediately on a wall collision (`wall_left` or `wall_right`
CollisionEvent). Cooldown begins on both natural expiry and wall cancellation.

`can_activate` returns True only when `not is_dashing and dash_cooldown <= 0`.

---

### WallSlideMechanic

File: `mechanics/wall_slide.py`

Purpose: Allows the player to cling to a wall and slow their descent, governed
by a stamina pool.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `WALL_SLIDE_SPEED` | 3.0 | Max fall speed while sliding |
| `WALL_FRICTION_FALL_SPEED` | 6.0 | Fall cap when touching wall but not actively sliding |
| `MAX_STAMINA` | 3.0 s | Maximum cling time |
| `STAMINA_REGEN_TIME` | 2.0 s | Time to fully regenerate from 0 |
| `MIN_STAMINA_TO_CLING` | 0.3 s | Minimum stamina required to begin a new cling |
| `EXHAUST_THRESHOLD` | 0.5 s | Stamina level at which an active slide stops |
| `EXHAUST_PENALTY` | 0.25 s | Extra stamina removed when exhausted off wall |
| `SLIDE_DRAIN_MULT` | 1.6 | Drain multiplier while actively sliding |

Wall coyote buffer: `Player.on_tick` sets `wall_coyote_time = 0.12` each tick
while `on_wall` and resets it otherwise. `JumpMechanic` checks this buffer when
deciding whether a wall jump is valid.

After stamina exhaustion, the mechanic sets `await_ground_after_exhaust = True`
and nudges the player off the wall for 6 frames to break repeated collision
detection. Stamina regeneration resumes only after the player touches the ground
again.

`wall_slide_stamina` is a field on `PlayerState`. The HUD reads it directly for
the stamina bar display.

`can_activate` checks `on_wall`, `not on_ground`, and
`wall_slide_stamina >= MIN_STAMINA_TO_CLING`.

---

### CrouchMechanic

File: `mechanics/crouch.py`

Purpose: Toggles a reduced hitbox height and applies movement penalties. Blocks
the stand-up transition when a ceiling is detected above.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `CROUCH_SPEED_MULT` | 0.6 | Speed multiplier while crouching |
| `CROUCH_ACCEL_MULT` | 0.8 | Acceleration multiplier while crouching |
| `CROUCH_JUMP_MULT` | 0.7 | Jump power multiplier while crouching |
| `CROUCH_HEIGHT_RATIO` | 0.5 | Hitbox height = normal height * 0.5 |

Default player hitbox: 28 x 56 px. Crouched: 28 x 28 px.

Input model: `set_crouch(active: bool)` is called every frame from
`process_input()` with the current state of the hold key. Crouch is hold-based,
not a toggle.

When entering crouch the player's `y` position is shifted down by
`height_diff = normal_height - crouch_height` to keep the bottom of the hitbox
fixed. The reverse shift occurs when standing up.

Stand-up is blocked when `collision_checker.tiles` overlap a test rect placed
at the standing position. If the player is airborne when the crouch key is
released, `_force_exit_crouch` restores height without a ceiling check.

`can_activate` returns `on_ground`.

Movement multipliers are provided via `get_movement_modifier(state)`, which
returns `{"speed_mult": 0.6, "accel_mult": 0.8}` when crouching.

---

### CombatMechanic

File: `mechanics/combat_mechanic.py`

Purpose: Resolves player-enemy contact each frame, classifying each collision
into one of three interaction types.

This class does not extend `BaseMechanic`. It is instantiated separately and
`check_enemy_collisions(state, enemy_manager, dt)` is called from the main game
loop.

Interaction types and their conditions:

| Type | Condition | Effect |
|---|---|---|
| Dash attack | `state.is_dashing` | Deals 1 damage, 300 px/s knockback, 0.5 s stun |
| Jump attack | Player falling, player bottom near enemy top, within 45 degree angle | Deals 2 damage, bounces player upward, restores all air jumps |
| Contact damage | Enemy in `ATTACK_ACTIVE` sub-state | Player takes `enemy.base_damage`, receives knockback |

Contact damage is only applied during the enemy's `ATTACK_ACTIVE` sub-state,
not on any body overlap. This enforces telegraphed attack windows.

Goblins are a special case: they deal damage via a forward hitbox
(`get_attack_hitbox()`) rather than body contact. `_check_goblin_attacks` runs
as a separate pass after the main loop.

Damage constants:

| Constant | Value |
|---|---|
| `DASH_ATTACK_DAMAGE` | 1 |
| `JUMP_ATTACK_DAMAGE` | 2 |
| `JUMP_ATTACK_BOUNCE_VELOCITY` | -400.0 px/s |
| `ENEMY_CONTACT_KNOCKBACK` | 200.0 px/s |

A per-enemy cooldown of 200 ms (`damage_cooldown`) prevents dash attacks from
hitting the same enemy multiple times in one dash.

---

### DamageMechanic

File: `mechanics/damage.py`

Purpose: Applies damage to the player, manages invincibility frames, and
emits death/respawn events.

This class does not extend `BaseMechanic` and is not in `self.mechanics`. It
subscribes to `TickEvent` for i-frame countdown bookkeeping.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `INVINCIBILITY_DURATION` | 1.5 s | I-frames after taking damage |

Invincibility is stored as `health_state.invincibility_frames` (an integer
frame count). `update_invincibility(state, dt)` converts `dt` to frames and
decrements that counter.

`take_damage(state, amount, source, source_pos, force)` returns `True` if the
player died. It:

1. Checks `health_state.is_invincible()` (skips if True unless `force=True`)
2. Delegates to `health_state.take_damage(amount, defense=0)`
3. Emits `PlayerDamageEvent` and, on death, `PlayerDeathEvent`

`respawn(state, spawn_x, spawn_y)` restores full health, resets position and
velocity, and grants 120 frames (2 s at 60 Hz) of spawn invincibility.

`instant_death(state, source)` bypasses invincibility and forces `current_hp`
to 0, then emits `PlayerDeathEvent`.

The HUD invincibility flash (white overlay every 6 frames) is implemented in
the render loop in `demo_game.py`, not inside this mechanic.

---

### ShurikenMechanic

File: `mechanics/shuriken.py`

Purpose: Manages a pool of shuriken projectiles. Each throw consumes one ammo
and starts a cooldown.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `SPEED` | 10.0 px/tick | ~600 px/s at 60 Hz |
| `COOLDOWN` | 0.35 s | Between throws |
| `DAMAGE` | 1 | Damage dealt to enemies |
| `STUN` | 0.4 s | Stun duration applied to hit enemy |

Default ammo: 10 (`shuriken_ammo` on `PlayerState`).

`request_throw(aim_offset_y: int)` records a throw request. `aim_offset_y` of
-1 aims up, +1 aims down, 0 is horizontal. On the next `on_tick` call, if
`throw_cooldown <= 0` and `shuriken_ammo > 0`, a `ShurikenProjectile` is
appended to `self.projectiles`.

Projectile lifecycle:

1. Moves by `(vx, vy)` each tick.
2. On tile collision: sets `stuck = True`, `stuck_timer = 2.0 s`, remains
   visible for 2 seconds then is removed.
3. On enemy collision: applies damage and stun; `stuck_timer = 0.1 s` (quick
   despawn after hit). Slimes absorb the projectile with no damage effect.
4. On TTL expiry: removed from the active list.

`can_activate` returns `shuriken_ammo > 0 and throw_cooldown <= 0`.

Input key: `K` (default).

---

### TeleportMechanic

File: `mechanics/teleport.py`

Purpose: Phase-blink ability that moves the player up to 8 tiles in the facing
direction, passing through geometry.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `RANGE_PX` | 256 px | Maximum blink distance (8 tiles at 32 px) |
| `PHASE_TIME` | 0.6 s | Duration of the phasing window |
| `INVULN_AFTER` | 0.25 s | Invincibility granted after arrival |
| `COOLDOWN` | 3.0 s | Between teleports |
| `MANA_COST` | 20.0 | Mana consumed per teleport |
| `PHASE_MOVE_SPEED` | 7.0 px/tick | Cursor steering speed while phasing |

State sequence:

1. `request_teleport()` — checks cooldown and mana, sets
   `is_teleporting_phase = True`, zeroes velocity, begins `PHASE_TIME` timer.
2. While phasing: directional input steers `phase_cursor` within `RANGE_PX`
   of the origin. The player position does not move during this window.
3. On `teleport_cast_time` reaching 0: player snaps to `phase_cursor` (or the
   last free destination found by ray-stepping), velocity is zeroed,
   `is_teleporting_invuln = True` for `INVULN_AFTER` seconds, cooldown starts.

`_find_safe_destination` ray-steps 8 segments along the blink direction and
returns the last position that does not collide with tiles.

`can_activate` requires `teleport_cooldown <= 0 and mana >= MANA_COST`.

Input key: `F` (default).

---

### NinjutsuMechanic

File: `mechanics/ninjutsu.py`

Purpose: Stance-select-cast pattern. Currently implements one technique:
Purify, which removes hazard tiles in a radius around the player.

Key parameters:

| Constant | Value | Description |
|---|---|---|
| `PURIFY_COOLDOWN` | 12.0 s | Per-technique cooldown |
| `PURIFY_CAST_TIME` | 0.4 s | Animation window (currently instant in effect) |
| `PURIFY_MANA_COST` | 25.0 | Mana consumed per cast |
| `PURIFY_RADIUS_TILES` | 5 tiles | Cleared area radius (160 px at 32 px tile size) |

Usage model:

- `L` / `Q` held: `request_stance()` — sets `state.ninjutsu_active = True`.
  While the stance key is held the player can select a technique (currently
  only "purify").
- On key release: `request_cast("purify")` is called automatically by
  `process_input()` when it detects the stance key transitioning from held to
  released.

On cast, `hazard_manager.clear_poison_area(x, y, radius_px)` is called
immediately. The cast timer and `ninjutsu_casting` flag are set but the effect
is synchronous.

Per-technique cooldowns are stored in `state.ninjutsu_cooldowns: dict[str, float]`.

`can_activate` checks `ninjutsu_cooldowns.get("purify", 0) <= 0 and mana >= PURIFY_MANA_COST`.

Input keys: `L` or `Q` (hold to stance, release to cast).

---

## Adding a New Mechanic

1. Create `mechanics/my_mechanic.py` extending `BaseMechanic`.
2. Implement `on_tick(state, dt)` and `can_activate(state)` at minimum.
3. Subscribe to `CollisionEvent` in `__init__` if wall/ground responses are
   needed; unsubscribe in `cleanup()`.
4. Add an instance to `Player.__init__` and append it to `self.mechanics`.
   Insert it at the correct position in the ordered list.
5. Add input handling in `player.process_input()`, using the `bound()` helper
   for configurable keys (see below).
6. If ability gating applies, add an entry to `feature_flags` and check it in
   `process_input()` before calling the mechanic's request method.

---

## Key Integration Points

### player.process_input(keys)

Called once per frame with `pygame.key.get_pressed()`. The inner `bound()`
helper resolves a key binding:

```python
def bound(action: str, default: int) -> bool:
    return key_down(self._key_bindings.get(action, default))
```

Registered actions: `left`, `right`, `jump`, `dash`, `crouch`.

Key bindings are set at runtime via `player.set_key_bindings(bindings: dict[str, int])`.
WASD is hardcoded as a fallback and is always active regardless of bindings.

### Player.on_tick(event: TickEvent)

Subscribed at priority 50. Physics integration runs at priority 60 and
collision resolution at priority 55, so collision state (`on_ground`,
`on_wall`, `wall_dir`) is current when mechanics execute.

The resource update (`_update_resources`) runs at the end of `on_tick`:
- Running drains stamina at 4.0 units/s.
- Stamina regenerates at `stamina_regen_rate` on ground (half rate in air).
- Mana regenerates at `mana_regen_rate` unconditionally.

---

## File References

| File | Role |
|---|---|
| `mechanics/base.py` | Abstract base class for all mechanics |
| `mechanics/movement.py` | Horizontal movement with smooth interpolation |
| `mechanics/jump.py` | All jump types: ground, coyote, wall, double |
| `mechanics/dash.py` | Dash burst with cooldown |
| `mechanics/wall_slide.py` | Wall cling with stamina system |
| `mechanics/crouch.py` | Reduced hitbox, speed penalty, ceiling detection |
| `mechanics/combat_mechanic.py` | Enemy contact resolution: dash/jump/contact damage |
| `mechanics/damage.py` | Health, i-frames, death/respawn events |
| `mechanics/shuriken.py` | Ammo-limited ranged projectiles |
| `mechanics/teleport.py` | Phase blink with mana cost |
| `mechanics/ninjutsu.py` | Stance/cast system; Purify technique |
| `entities/player.py` | Composition owner; process_input; on_tick ordering |
| `config/physics_constants.py` | Jump, wall-jump, and gravity constants |
| `core/state.py` | PlayerState and PhysicsState definitions |
| `core/event_bus.py` | CollisionEvent, VelocityChangeEvent, TickEvent |
