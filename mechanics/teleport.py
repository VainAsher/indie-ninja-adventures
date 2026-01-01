"""
Teleport Mechanic - Short phase blink with mana cost and cooldown.
"""

import pygame

from core.event_bus import EventBus
from core.logger import MechanicLogger
from core.state import PlayerState
from mechanics.base import BaseMechanic


class TeleportMechanic(BaseMechanic):
    RANGE_PX = 256  # 8 tiles
    PHASE_TIME = 0.6
    INVULN_AFTER = 0.25
    COOLDOWN = 3.0
    MANA_COST = 20.0
    PHASE_MOVE_SPEED = 420.0 / 60.0  # px per tick while phasing

    def __init__(
        self, entity_id: int, event_bus: EventBus, logger: MechanicLogger, collision_system=None
    ):
        super().__init__(entity_id, event_bus, logger)
        self.collision_system = collision_system
        self.teleport_requested = False
        self._vertical_aim = 0
        self.phase_cursor = None  # (x, y) while phasing
        self.phase_dir = (0, 0)

    def set_collision_system(self, collision_system):
        self.collision_system = collision_system

    def request_teleport(self, vertical_aim: int = 0):
        self.teleport_requested = True
        self._vertical_aim = vertical_aim

    def update_phase_direction(self, dx: int, dy: int):
        self.phase_dir = (dx, dy)

    def _find_safe_destination(self, state: PlayerState) -> tuple:
        facing = state.facing if state.facing != 0 else 1
        dir_y = self._vertical_aim
        norm = max(1, abs(facing) + abs(dir_y))
        step_x = facing * (self.RANGE_PX / norm) / 8.0
        step_y = dir_y * (self.RANGE_PX / norm) / 8.0
        target_x = state.physics.x
        target_y = state.physics.y
        last_free = (target_x, target_y)
        for _ in range(8):
            target_x += step_x
            target_y += step_y
            if self._is_free(target_x, target_y, state.physics.width, state.physics.height):
                last_free = (target_x, target_y)
            else:
                break
        return last_free

    def _is_free(self, x: float, y: float, w: int, h: int) -> bool:
        if not self.collision_system:
            return True
        test_rect = pygame.Rect(int(x), int(y), w, h)
        for t in self.collision_system.tiles:
            if test_rect.colliderect(t):
                return False
        return True

    def on_tick(self, state: PlayerState, dt: float):
        if not self.enabled:
            return

        if state.teleport_cooldown > 0.0:
            state.teleport_cooldown = max(0.0, state.teleport_cooldown - dt)

        if state.is_teleporting_invuln:
            state.teleport_cast_time = max(0.0, state.teleport_cast_time - dt)
            if state.teleport_cast_time == 0.0:
                state.is_teleporting_invuln = False

        if state.is_teleporting_phase:
            # phase timer counts down; cannot move during phase
            state.teleport_cast_time = max(0.0, state.teleport_cast_time - dt)
            if self.phase_cursor is None:
                self.phase_cursor = (state.physics.x, state.physics.y)
            # Steer cursor during phase
            dir_x, dir_y = self.phase_dir
            if dir_x != 0 or dir_y != 0:
                cx, cy = self.phase_cursor
                cx += dir_x * self.PHASE_MOVE_SPEED
                cy += dir_y * self.PHASE_MOVE_SPEED
                # Clamp within range of origin
                ox, oy = state.physics.x, state.physics.y
                dx = cx - ox
                dy = cy - oy
                dist2 = dx * dx + dy * dy
                max_dist = self.RANGE_PX
                if dist2 > max_dist * max_dist:
                    import math

                    scale = max_dist / math.sqrt(dist2)
                    cx = ox + dx * scale
                    cy = oy + dy * scale
                self.phase_cursor = (cx, cy)
            if state.teleport_cast_time == 0.0:
                dest_x, dest_y = (
                    self.phase_cursor if self.phase_cursor else self._find_safe_destination(state)
                )
                state.physics.x = dest_x
                state.physics.y = dest_y
                state.physics.vx = 0.0
                state.physics.vy = 0.0
                state.is_teleporting_phase = False
                state.is_teleporting_invuln = True
                state.teleport_cast_time = self.INVULN_AFTER
                state.teleport_cooldown = self.COOLDOWN
                self.phase_cursor = None
            return

        if self.teleport_requested and state.teleport_cooldown <= 0.0:
            if state.mana >= self.MANA_COST:
                state.mana = max(0.0, state.mana - self.MANA_COST)
                state.is_teleporting_phase = True
                state.teleport_cast_time = self.PHASE_TIME
                # lock movement during phase; velocity zeroed
                state.physics.vx = 0.0
                state.physics.vy = 0.0
            self.teleport_requested = False
        else:
            self.teleport_requested = False

    def can_activate(self, state: PlayerState) -> bool:
        return self.enabled and state.teleport_cooldown <= 0.0 and state.mana >= self.MANA_COST

    def reset(self, state: PlayerState):
        self.teleport_requested = False
        state.is_teleporting_phase = False
        state.is_teleporting_invuln = False
        state.teleport_cooldown = 0.0
        state.teleport_cast_time = 0.0
        self.phase_cursor = None
        self.phase_dir = (0, 0)
