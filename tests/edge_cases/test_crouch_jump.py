"""Edge test: crouch should reduce jump power but still allow a jump when requested."""

import pygame

from config.physics_constants import CROUCH_JUMP_MULT, JUMP_POWER
from core.event_bus import EventBus
from core.logger import GameLogger
from core.state import PhysicsState, PlayerState
from mechanics.crouch import CrouchMechanic
from mechanics.jump import JumpMechanic


def main():
    pygame.init()
    bus = EventBus()
    logger = GameLogger()

    state = PlayerState(
        player_id=0,
        physics=PhysicsState(x=0, y=0, vx=0, vy=0, width=20, height=20),
        crouching=False,
        is_dashing=False,
    )

    jump = JumpMechanic(entity_id=0, event_bus=bus, logger=logger.get_logger("test.jump"))
    crouch = CrouchMechanic(
        entity_id=0,
        event_bus=bus,
        logger=logger.get_logger("test.crouch"),
        collision_checker=None,
    )

    print("\n=== Test 1: Normal jump (not crouched) ===")
    state.physics.on_ground = True
    jump.request_jump()
    jump.on_tick(state, 1 / 60)
    print("Before: crouching=False, on_ground=True, vy=0")
    print(
        f"After: crouching={state.crouching}, on_ground={state.physics.on_ground}, vy={state.physics.vy}"
    )

    print("\n=== Test 2: Enter crouch ===")
    crouch.set_crouch(True)
    crouch.on_tick(state, 1 / 60)
    print("Before: crouching=False, height=20")
    print(f"After: crouching={state.crouching}, height={state.physics.height}")

    print("\n=== Test 3: Try to jump while crouched ===")
    state.physics.on_ground = True
    state.physics.vy = 0
    jump.request_jump()
    result = jump.on_tick(state, 1 / 60)
    print("Before: crouching=True, on_ground=True, vy=0")
    print(
        f"After: crouching={state.crouching}, on_ground={state.physics.on_ground}, vy={state.physics.vy}"
    )
    print(f"Jump result: {result}")

    print("\n=== Test 4: Check crouch jump power ===")
    expected_vy = -JUMP_POWER * CROUCH_JUMP_MULT
    if abs(state.physics.vy - expected_vy) < 0.01:
        print(f"[OK] Crouch jump applied reduced power: vy={state.physics.vy:.2f}")
    else:
        print(f"[FAIL] Expected vy={expected_vy:.2f}, got {state.physics.vy:.2f}")


if __name__ == "__main__":
    main()
