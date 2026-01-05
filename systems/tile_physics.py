"""
Tile Physics System - State Management for Interactive Tiles

Tracks mutable state for:
- Breakable blocks (health, break animation)
- Cracked blocks (crack timer, fall state)
- Pushable blocks (position, velocity, pushed state)
- Fluid zones (entry/exit events)

This system provides a centralized way to manage tile-level physics and state
that changes during gameplay.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple

from config.physics_constants import (
    BREAKABLE_BREAK_TIME,
    BREAKABLE_HEALTH,
    CRACKED_DELAY,
    CRACKED_FALL_DELAY,
    ICE_ACCEL_MULT,
    ICE_FRICTION,
    LAVA_DAMAGE_RATE,
    LAVA_GRAVITY_MULT,
    LAVA_INVINCIBILITY_TIME,
    LAVA_SPEED_MULT,
    MUD_ACCEL_MULT,
    MUD_FRICTION,
    MUD_JUMP_MULT,
    MUD_SPEED_MULT,
    PUSHABLE_FRICTION,
    PUSHABLE_MASS,
    PUSHABLE_PUSH_FORCE,
    WATER_FRICTION,
    WATER_GRAVITY_MULT,
    WATER_JUMP_MULT,
    WATER_SPEED_MULT,
)
from systems.room_generation import (
    TILE_BREAKABLE,
    TILE_CRACKED,
    TILE_ICE,
    TILE_LAVA,
    TILE_MUD,
    TILE_PUSHABLE,
    TILE_STICKY,
    TILE_WATER,
)


@dataclass
class TileState:
    """Mutable state for a single interactive tile"""

    tile_type: int
    health: int = 3  # For breakable blocks
    timer: float = 0.0  # For cracked blocks, break animations
    velocity: Tuple[float, float] = (0.0, 0.0)  # For pushable blocks
    is_broken: bool = False  # Whether tile is destroyed
    is_falling: bool = False  # For cracked blocks


@dataclass
class PhysicsModifiers:
    """Physics modifiers applied by tile types"""

    gravity_mult: float = 1.0  # Gravity multiplier
    speed_mult: float = 1.0  # Movement speed multiplier
    accel_mult: float = 1.0  # Acceleration multiplier
    friction: float = 0.8  # Ground friction
    jump_mult: float = 1.0  # Jump power multiplier
    damage_rate: float = 0.0  # Damage per second
    invincibility_time: float = 0.0  # Time between damage ticks


class TilePhysicsManager:
    """Manages all tile-level physics and state"""

    def __init__(self):
        """Initialize tile physics manager"""
        self.tile_states: Dict[Tuple[int, int], TileState] = {}
        self._last_damage_time: Dict[Tuple[int, int], float] = {}  # Track damage timing
        self.game_time: float = 0.0  # Track game time for damage intervals

    def get_tile_modifiers(self, tile_type: int) -> PhysicsModifiers:
        """
        Get physics modifiers for tile type

        Args:
            tile_type: The tile type ID

        Returns:
            PhysicsModifiers with appropriate values for this tile type
        """
        if tile_type == TILE_WATER:
            return PhysicsModifiers(
                gravity_mult=WATER_GRAVITY_MULT,
                speed_mult=WATER_SPEED_MULT,
                friction=WATER_FRICTION,
                jump_mult=WATER_JUMP_MULT,
            )

        elif tile_type == TILE_LAVA:
            return PhysicsModifiers(
                gravity_mult=LAVA_GRAVITY_MULT,
                speed_mult=LAVA_SPEED_MULT,
                friction=WATER_FRICTION,  # Similar to water
                jump_mult=WATER_JUMP_MULT,  # Similar to water
                damage_rate=LAVA_DAMAGE_RATE,
                invincibility_time=LAVA_INVINCIBILITY_TIME,
            )

        elif tile_type == TILE_ICE:
            return PhysicsModifiers(
                friction=ICE_FRICTION,
                accel_mult=ICE_ACCEL_MULT,
            )

        elif tile_type == TILE_MUD:
            return PhysicsModifiers(
                speed_mult=MUD_SPEED_MULT,
                accel_mult=MUD_ACCEL_MULT,
                friction=MUD_FRICTION,
                jump_mult=MUD_JUMP_MULT,
            )

        elif tile_type == TILE_STICKY:
            # Sticky blocks act like wall jump surfaces
            return PhysicsModifiers(friction=0.5)  # High friction for wall cling

        else:
            # Default modifiers (no effect)
            return PhysicsModifiers()

    def update(self, dt: float, tilemap: list[list[int]]):
        """
        Update all tile states (timers, animations)

        Args:
            dt: Delta time in seconds
            tilemap: Current tilemap (will be modified if tiles break)
        """
        self.game_time += dt

        # Update each tile state
        tiles_to_remove = []

        for (tx, ty), state in self.tile_states.items():
            # Update cracked block timers
            if state.tile_type == TILE_CRACKED and not state.is_broken:
                state.timer += dt

                # Check if should start falling
                if state.timer >= CRACKED_DELAY and not state.is_falling:
                    state.is_falling = True
                    state.timer = 0.0  # Reset timer for fall phase

                # Check if should break
                if state.is_falling and state.timer >= CRACKED_FALL_DELAY:
                    state.is_broken = True
                    # Remove from tilemap
                    if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]):
                        from systems.room_generation import TILE_EMPTY

                        tilemap[ty][tx] = TILE_EMPTY
                    tiles_to_remove.append((tx, ty))

            # Update breakable block break animation
            elif state.tile_type == TILE_BREAKABLE and state.is_broken:
                state.timer += dt
                if state.timer >= BREAKABLE_BREAK_TIME:
                    # Remove from tilemap
                    if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]):
                        from systems.room_generation import TILE_EMPTY

                        tilemap[ty][tx] = TILE_EMPTY
                    tiles_to_remove.append((tx, ty))

        # Remove broken tiles from state tracking
        for coords in tiles_to_remove:
            del self.tile_states[coords]

    def damage_tile(self, tx: int, ty: int, tilemap: list[list[int]]) -> bool:
        """
        Damage a tile (for breakable blocks)

        Args:
            tx: Tile X coordinate
            ty: Tile Y coordinate
            tilemap: Current tilemap

        Returns:
            True if tile was destroyed, False otherwise
        """
        tile_type = tilemap[ty][tx] if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]) else 0

        if tile_type != TILE_BREAKABLE:
            return False

        # Get or create tile state
        coords = (tx, ty)
        if coords not in self.tile_states:
            self.tile_states[coords] = TileState(tile_type=TILE_BREAKABLE, health=BREAKABLE_HEALTH)

        state = self.tile_states[coords]

        # Damage the tile
        state.health -= 1

        # Check if broken
        if state.health <= 0:
            state.is_broken = True
            state.timer = 0.0  # Start break animation timer
            return True

        return False

    def trigger_cracked_tile(self, tx: int, ty: int, tilemap: list[list[int]]):
        """
        Trigger a cracked tile to start breaking

        Args:
            tx: Tile X coordinate
            ty: Tile Y coordinate
            tilemap: Current tilemap
        """
        tile_type = tilemap[ty][tx] if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]) else 0

        if tile_type != TILE_CRACKED:
            return

        # Get or create tile state
        coords = (tx, ty)
        if coords not in self.tile_states:
            self.tile_states[coords] = TileState(tile_type=TILE_CRACKED)

        # Start the timer if not already started
        state = self.tile_states[coords]
        if state.timer == 0.0:
            state.timer = 0.0  # Will increment in update()

    def push_tile(self, tx: int, ty: int, push_direction: float, tilemap: list[list[int]]) -> bool:
        """
        Attempt to push a pushable block

        Args:
            tx: Tile X coordinate
            ty: Tile Y coordinate
            push_direction: Direction of push (-1 for left, +1 for right)
            tilemap: Current tilemap

        Returns:
            True if tile was pushed successfully
        """
        tile_type = tilemap[ty][tx] if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]) else 0

        if tile_type != TILE_PUSHABLE:
            return False

        # TODO: Implement pushable block physics
        # This would require:
        # 1. Check if destination is clear
        # 2. Move the tile in tilemap
        # 3. Update pushable state with velocity
        # 4. Handle collision with other tiles
        #
        # For now, this is a placeholder
        return False

    def check_damage_from_tile(self, tile_type: int, coords: Tuple[int, int], dt: float) -> bool:
        """
        Check if player should take damage from standing on this tile

        Args:
            tile_type: The tile type
            coords: Tile coordinates (for tracking damage timing)
            dt: Delta time

        Returns:
            True if damage should be applied this frame
        """
        modifiers = self.get_tile_modifiers(tile_type)

        if modifiers.damage_rate <= 0:
            return False

        # Check if enough time has passed since last damage
        last_damage = self._last_damage_time.get(coords, 0.0)
        time_since_damage = self.game_time - last_damage

        if time_since_damage >= modifiers.invincibility_time:
            self._last_damage_time[coords] = self.game_time
            return True

        return False

    def is_sticky_surface(self, tile_type: int) -> bool:
        """
        Check if tile type is a sticky surface (for wall jumps)

        Args:
            tile_type: The tile type

        Returns:
            True if player can wall jump on this tile
        """
        return tile_type == TILE_STICKY

    def reset(self):
        """Reset all tile states (for new level)"""
        self.tile_states.clear()
        self._last_damage_time.clear()
        self.game_time = 0.0
