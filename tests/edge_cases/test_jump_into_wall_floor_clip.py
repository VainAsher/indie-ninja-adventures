"""
Regression test: jumping while pressing into a wall must not sink the player.

Reproduce scenario
------------------
Player stands on the floor tile, pressing horizontally into an adjacent wall.
The PhysicsSystem moves the player both upward (vy < 0, jump) and sideways
(vx != 0) in the same tick.  Before the fix, the swept / normal vertical
collision functions used physics.x (already moved into the wall) when tracing
the vertical path.  A wall tile whose y-centre was lower than the player
centre triggered the "ceiling from below" branch, snapping the player DOWN to
tile.bottom — below the floor — causing the floor-sink glitch.

Layout (32 px tiles, 28×56 player)
------------------------------------
  x=32         x=64
  [WALL y=0  ]            y=  0 – 32
  [WALL y=32 ]            y= 32 – 64
            [FLOOR y=64]  y= 64 – 96   player stands here (x=4)
"""

import pygame
import pytest

from core.entity_system import Entity, EntityManager, EntityType
from core.event_bus import EventBus
from core.state import PhysicsState
from systems.collision_system import CollisionSystem

pygame.init()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TILE_SIZE = 32
PLAYER_W = 28
PLAYER_H = 56

WALL_X = 32
FLOOR_Y = 64


def _make_system():
    bus = EventBus()
    mgr = EntityManager(bus)
    sys = CollisionSystem(bus, mgr)
    tiles = [
        pygame.Rect(WALL_X, 0, TILE_SIZE, TILE_SIZE),  # upper wall
        pygame.Rect(WALL_X, TILE_SIZE, TILE_SIZE, TILE_SIZE),  # lower wall (adjacent to floor)
        pygame.Rect(0, FLOOR_Y, TILE_SIZE * 4, TILE_SIZE),  # wide floor
    ]
    sys.set_tiles(tiles)
    return sys


def _make_player(vx: float, vy: float) -> Entity:
    """Player standing on the floor, pressed against the right wall."""
    # Position: right edge touching the wall (x + width == WALL_X)
    px = float(WALL_X - PLAYER_W)
    py = float(FLOOR_Y - PLAYER_H)
    return Entity(
        entity_id=0,
        entity_type=EntityType.PLAYER,
        physics=PhysicsState(
            x=px,
            y=py,
            vx=vx,
            vy=vy,
            width=PLAYER_W,
            height=PLAYER_H,
            on_ground=False,  # PhysicsSystem already cleared this before collision
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJumpIntoWallFloorClip:
    """Player must NOT be pushed below the floor when jumping into a wall."""

    def test_swept_jump_does_not_sink_below_floor(self):
        """
        High-speed upward jump (|vy| > 8) while pressing into wall.
        Uses _swept_vertical_collision internally.
        """
        sys = _make_system()
        # Simulate: PhysicsSystem already moved player right into wall (vx=8)
        # and up (vy=-14.5, first jump frame).
        player = _make_player(vx=8.0, vy=-14.5)
        # Apply the same displacement PhysicsSystem would have applied
        player.physics.x += player.physics.vx  # now overlapping wall
        player.physics.y += player.physics.vy  # now airborne

        entity_manager = sys.entity_manager
        entity_manager.entities[0] = player
        sys.check_and_resolve(player)

        floor_top = FLOOR_Y
        player_bottom = player.physics.y + PLAYER_H
        assert (
            player_bottom <= floor_top + 1
        ), f"Player sank below floor: feet at {player_bottom}, floor at {floor_top}"

    def test_normal_jump_does_not_sink_below_floor(self):
        """
        Low-speed upward movement (|vy| <= 8) while pressing into wall.
        Uses _check_vertical_collisions internally.
        """
        sys = _make_system()
        player = _make_player(vx=8.0, vy=-6.0)
        player.physics.x += player.physics.vx
        player.physics.y += player.physics.vy

        entity_manager = sys.entity_manager
        entity_manager.entities[0] = player
        sys.check_and_resolve(player)

        floor_top = FLOOR_Y
        player_bottom = player.physics.y + PLAYER_H
        assert (
            player_bottom <= floor_top + 1
        ), f"Player sank below floor: feet at {player_bottom}, floor at {floor_top}"

    def test_player_is_pushed_away_from_wall_not_into_floor(self):
        """
        After resolution the player should be outside the wall tile, not inside the floor.
        """
        sys = _make_system()
        player = _make_player(vx=8.0, vy=-14.5)
        player.physics.x += player.physics.vx
        player.physics.y += player.physics.vy

        entity_manager = sys.entity_manager
        entity_manager.entities[0] = player
        sys.check_and_resolve(player)

        player_rect = player.physics.get_rect()
        wall_tile = pygame.Rect(WALL_X, TILE_SIZE, TILE_SIZE, TILE_SIZE)
        floor_tile = pygame.Rect(0, FLOOR_Y, TILE_SIZE * 4, TILE_SIZE)

        assert not player_rect.colliderect(
            wall_tile
        ), "Player is still overlapping the wall tile after resolution"
        assert not player_rect.colliderect(
            floor_tile
        ), "Player is overlapping the floor tile — sank into the ground"

    def test_jump_velocity_not_zeroed_by_false_ceiling(self):
        """
        A false ceiling hit would zero vy.  After correct resolution the player
        should still have negative (upward) vy.
        """
        sys = _make_system()
        player = _make_player(vx=8.0, vy=-14.5)
        player.physics.x += player.physics.vx
        player.physics.y += player.physics.vy

        entity_manager = sys.entity_manager
        entity_manager.entities[0] = player
        sys.check_and_resolve(player)

        assert player.physics.vy < 0, (
            f"Jump velocity was zeroed (vy={player.physics.vy}); "
            "false ceiling hit likely triggered"
        )

    def test_pressing_left_into_wall_also_safe(self):
        """Same scenario mirrored: pressing left into a left-side wall."""
        bus = EventBus()
        mgr = EntityManager(bus)
        sys2 = CollisionSystem(bus, mgr)
        # Wall on the LEFT at x=0
        tiles = [
            pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE),
            pygame.Rect(0, TILE_SIZE, TILE_SIZE, TILE_SIZE),
            pygame.Rect(0, FLOOR_Y, TILE_SIZE * 4, TILE_SIZE),
        ]
        sys2.set_tiles(tiles)

        # Player stands to the right of the left wall, pressing left
        px = float(TILE_SIZE)  # left edge at x=32 (touching wall.right)
        py = float(FLOOR_Y - PLAYER_H)
        player = Entity(
            entity_id=0,
            entity_type=EntityType.PLAYER,
            physics=PhysicsState(
                x=px,
                y=py,
                vx=-8.0,
                vy=-14.5,
                width=PLAYER_W,
                height=PLAYER_H,
                on_ground=False,
            ),
        )
        player.physics.x += player.physics.vx
        player.physics.y += player.physics.vy

        mgr.entities[0] = player
        sys2.check_and_resolve(player)

        floor_top = FLOOR_Y
        player_bottom = player.physics.y + PLAYER_H
        assert (
            player_bottom <= floor_top + 1
        ), f"Player sank below floor when pressing left: feet at {player_bottom}"
        assert player.physics.vy < 0, "Jump velocity was zeroed by false ceiling (left wall)"
