import pygame

from core.entity_system import Entity, EntityManager, EntityType
from core.event_bus import EventBus
from core.state import PhysicsState
from systems.collision_system import CollisionSystem


def make_player(x=50, y=50, w=28, h=56):
    physics = PhysicsState(x=x, y=y, vx=0.0, vy=0.0, width=w, height=h)
    dummy_entity = Entity(entity_id=0, entity_type=EntityType.PLAYER, physics=physics)
    return dummy_entity


def setup_collision(tiles, platforms=None):
    bus = EventBus()
    em = EntityManager(bus)
    cs = CollisionSystem(bus, em)
    cs.set_tiles(tiles, platforms or [])
    return cs


def test_pressing_into_wall_does_not_set_ground():
    pygame.init()
    # Position player overlapping the wall on the next tick
    player = make_player(x=30, y=10)
    # Wall to the right
    wall = pygame.Rect(40, 0, 10, 200)
    cs = setup_collision([wall])
    player.physics.vx = 5.0
    cs.check_and_resolve(player)
    assert player.physics.on_ground is False
    assert player.physics.on_wall is True


def test_landing_sets_ground_not_wall():
    pygame.init()
    player = make_player(x=50, y=100)
    floor = pygame.Rect(0, 150, 200, 20)
    cs = setup_collision([floor])
    player.physics.vy = 5.0
    cs.check_and_resolve(player)
    assert player.physics.on_ground is True
    assert player.physics.on_wall is False


def test_snap_to_ground_when_close():
    pygame.init()
    # Start a couple of pixels above the floor so predictive snap can engage
    player = make_player(x=50, y=92)  # y + height = 148 (2px gap to floor at 150)
    floor = pygame.Rect(0, 150, 200, 20)
    cs = setup_collision([floor])
    # Small downward velocity, close to floor
    player.physics.vy = 0.05
    cs.check_and_resolve(player)
    assert player.physics.on_ground is True
    assert abs(player.physics.y + player.physics.height - floor.top) < 1.0
