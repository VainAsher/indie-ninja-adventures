"""
Shuriken Mechanic - Ammo-limited ranged throws with stun and button press support.
"""

from dataclasses import dataclass

import pygame

from core.event_bus import EventBus
from core.logger import MechanicLogger
from core.state import PlayerState
from mechanics.base import BaseMechanic


@dataclass
class ShurikenProjectile:
    x: float
    y: float
    vx: float
    vy: float
    ttl: float = 2.0  # seconds alive after impact/stick
    width: int = 12
    height: int = 12
    stuck: bool = False
    stuck_timer: float = 2.0


class ShurikenMechanic(BaseMechanic):
    """
    Manages shuriken throws with ammo and cooldown.
    """

    SPEED = 600.0 / 60.0  # pixels per tick (~600 px/s)
    COOLDOWN = 0.35
    DAMAGE = 1
    STUN = 0.4

    def __init__(
        self,
        entity_id: int,
        event_bus: EventBus,
        logger: MechanicLogger,
        collision_system=None,
        enemy_manager=None,
    ):
        super().__init__(entity_id, event_bus, logger)
        self.collision_system = collision_system
        self.enemy_manager = enemy_manager
        self.projectiles: list[ShurikenProjectile] = []
        self.throw_requested = False
        self.aim_offset_y = 0

    def set_context(self, collision_system=None, enemy_manager=None):
        self.collision_system = collision_system or self.collision_system
        self.enemy_manager = enemy_manager or self.enemy_manager

    def request_throw(self, aim_offset_y: int = 0):
        self.throw_requested = True
        self.aim_offset_y = aim_offset_y

    def _spawn_shuriken(self, state: PlayerState):
        if state.shuriken_ammo <= 0:
            return
        state.shuriken_ammo = max(0, state.shuriken_ammo - 1)
        facing = state.facing if state.facing != 0 else 1
        angle_y = self.aim_offset_y
        norm = max(1, abs(facing) + abs(angle_y))
        vx = facing * self.SPEED / norm
        vy = angle_y * self.SPEED / norm
        px = state.physics.x + state.physics.width // 2
        py = state.physics.y + state.physics.height // 2
        proj = ShurikenProjectile(x=px, y=py, vx=vx, vy=vy)
        self.projectiles.append(proj)
        state.is_throwing = True
        state.throw_cooldown = self.COOLDOWN
        self.logger.debug(f"Spawned shuriken (ammo={state.shuriken_ammo})")

    def _rects_overlap(self, a, b) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by

    def _check_tile_collision(self, proj: ShurikenProjectile) -> bool:
        if not self.collision_system:
            return False
        rect = pygame.Rect(int(proj.x), int(proj.y), proj.width, proj.height)
        for t in self.collision_system.tiles:
            if rect.colliderect(t):
                return True
        return False

    def _check_enemy_collision(self, proj: ShurikenProjectile):
        if not self.enemy_manager:
            try:
                from entities.enemy_manager import get_enemy_manager

                self.enemy_manager = get_enemy_manager()
            except Exception:
                return
        if not self.enemy_manager:
            return
        proj_rect = (proj.x, proj.y, proj.width, proj.height)
        for enemy_id, enemy in self.enemy_manager.enemies.items():
            if enemy.is_dead():
                continue
            if self._rects_overlap(proj_rect, enemy.get_rect()):
                from entities.enemy import EnemyType

                if enemy.enemy_type == EnemyType.SLIME:
                    # Projectiles are absorbed by the slime's oozy body — no damage,
                    # projectile disappears quickly (visually "swallowed").
                    proj.stuck = True
                    proj.stuck_timer = 0.05
                    return
                self.enemy_manager.damage_enemy(enemy_id, self.DAMAGE, 0.0, 0.0, self.STUN)
                proj.stuck = True
                proj.stuck_timer = 0.1  # despawn after hit
                return

    def on_tick(self, state: PlayerState, dt: float):
        if not self.enabled:
            return

        # Clear throw flag if cooldown finished
        if state.throw_cooldown > 0:
            state.throw_cooldown = max(0.0, state.throw_cooldown - dt)
        else:
            state.is_throwing = False

        if self.throw_requested and state.throw_cooldown <= 0.0:
            self._spawn_shuriken(state)
        self.throw_requested = False

        # Update projectiles
        active = []
        for proj in self.projectiles:
            if proj.stuck:
                proj.stuck_timer -= dt
                if proj.stuck_timer > 0:
                    active.append(proj)
                continue

            proj.x += proj.vx
            proj.y += proj.vy

            # Tile collision -> stick
            if self._check_tile_collision(proj):
                proj.stuck = True
                proj.stuck_timer = 2.0
                active.append(proj)
                continue

            # Enemy collision
            self._check_enemy_collision(proj)
            if not proj.stuck:
                # Lifetime clamp
                proj.ttl -= dt
                if proj.ttl > 0:
                    active.append(proj)
            else:
                active.append(proj)

        self.projectiles = active

    def can_activate(self, state: PlayerState) -> bool:
        """Can throw if ammo and cooldown ready."""
        return self.enabled and state.shuriken_ammo > 0 and state.throw_cooldown <= 0.0

    def reset(self, state: PlayerState):
        self.projectiles.clear()
        self.throw_requested = False
        state.is_throwing = False
        state.throw_cooldown = 0.0
