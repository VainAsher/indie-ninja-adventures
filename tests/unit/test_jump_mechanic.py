"""
Test script for Jump Mechanic

Verifies:
- Ground jump
- Coyote time (grace period after leaving ground)
- Jump buffering (input window)
- Double jump
- Wall jump
- Crouch jump modifier
- Collision response (reset jumps on landing)
- Feature flag toggling (enable/disable double/wall jump)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    EventBus, GameLogger, PhysicsState, PlayerState,
    CollisionEvent, VelocityChangeEvent
)
from game.health_system import HealthState
from mechanics import JumpMechanic


def test_ground_jump():
    """Test basic ground jump"""
    print("\n" + "="*60)
    print("Testing Ground Jump")
    print("="*60)

    # Initialize systems
    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    # Create player state
    physics = PhysicsState(x=100, y=100, vx=0.0, vy=0.0, width=20, height=20)
    physics.on_ground = True
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )

    # Create jump mechanic
    jump_mechanic = JumpMechanic(entity_id=0, event_bus=bus, logger=logger)

    print(f"\nInitial state:")
    print(f"  Position: ({state.physics.x}, {state.physics.y})")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")
    print(f"  On ground: {state.physics.on_ground}")
    print(f"  Jumps left: {state.jumps_left}")

    # Track velocity change events
    velocity_changes = []
    def on_velocity_change(event: VelocityChangeEvent):
        velocity_changes.append(event)
        print(f"  [VELOCITY] {event.reason}: ({event.old_vx}, {event.old_vy}) -> ({event.new_vx}, {event.new_vy})")

    bus.subscribe(VelocityChangeEvent, on_velocity_change)

    # Request jump
    print(f"\nRequesting jump...")
    jump_mechanic.request_jump()

    # Process tick
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"\nAfter jump:")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")
    print(f"  On ground: {state.physics.on_ground}")
    print(f"  Jumps left: {state.jumps_left}")

    # Verify jump executed
    assert state.physics.vy < 0, f"Expected negative vy (jumping up), got {state.physics.vy}"
    assert state.physics.vy == -14.5, f"Expected vy=-14.5, got {state.physics.vy}"
    assert state.jumps_left == 1, f"Expected 1 jump remaining, got {state.jumps_left}"
    assert len(velocity_changes) == 1, f"Expected 1 velocity change, got {len(velocity_changes)}"
    assert velocity_changes[0].reason == "ground_jump"

    print(f"\n[PASS] Ground Jump Test PASSED")


def test_coyote_time():
    """Test coyote time (grace period after leaving ground)"""
    print("\n" + "="*60)
    print("Testing Coyote Time")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=0.0, width=20, height=20)
    physics.on_ground = False  # In air
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )

    # Set coyote time active
    state.coyote_time = 0.12

    jump_mechanic = JumpMechanic(entity_id=0, event_bus=bus, logger=logger)

    print(f"\nInitial state:")
    print(f"  On ground: {state.physics.on_ground}")
    print(f"  Coyote time: {state.coyote_time:.3f}s")
    print(f"  Can activate: {jump_mechanic.can_activate(state)}")

    # Request jump during coyote time
    print(f"\nRequesting jump during coyote time...")
    jump_mechanic.request_jump()
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"\nAfter jump:")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")
    print(f"  Coyote time: {state.coyote_time:.3f}s")

    # Verify coyote jump executed
    assert state.physics.vy < 0, "Coyote jump should execute"
    assert state.coyote_time == 0.0, "Coyote time should be cleared"

    print(f"\n[PASS] Coyote Time Test PASSED")


def test_jump_buffering():
    """Test jump buffering (input window)"""
    print("\n" + "="*60)
    print("Testing Jump Buffering")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=0.0, width=20, height=20)
    physics.on_ground = False  # In air
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )
    state.jumps_left = 0  # No jumps available

    jump_mechanic = JumpMechanic(entity_id=0, event_bus=bus, logger=logger)

    print(f"\nInitial state:")
    print(f"  On ground: {state.physics.on_ground}")
    print(f"  Jumps left: {state.jumps_left}")
    print(f"  Can activate: {jump_mechanic.can_activate(state)}")

    # Request jump when can't jump (should buffer)
    print(f"\nRequesting jump (buffered - no jumps available)...")
    jump_mechanic.request_jump()
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"  Jump buffer time: {state.jump_buffer_time:.3f}s")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")

    # Verify jump didn't execute yet
    assert state.physics.vy == 0.0, "Jump should be buffered, not executed"
    assert state.jump_buffer_time > 0.0, "Jump buffer should be active"

    # Land on ground
    print(f"\nLanding on ground...")
    physics.on_ground = True
    state.jumps_left = 2

    # Process another tick (buffered jump should execute)
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")
    print(f"  Jump buffer time: {state.jump_buffer_time:.3f}s")

    # Verify buffered jump executed
    assert state.physics.vy < 0, "Buffered jump should execute on landing"
    assert state.jump_buffer_time == 0.0, "Jump buffer should be cleared"

    print(f"\n[PASS] Jump Buffering Test PASSED")


def test_double_jump():
    """Test double jump (air jump)"""
    print("\n" + "="*60)
    print("Testing Double Jump")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=5.0, width=20, height=20)
    physics.on_ground = False  # In air
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )
    state.jumps_left = 1  # One jump remaining
    state.stamina = 10.0
    state.stamina_max = 10.0

    jump_mechanic = JumpMechanic(
        entity_id=0,
        event_bus=bus,
        logger=logger,
        feature_flags={"double_jump": True}
    )

    print(f"\nInitial state:")
    print(f"  On ground: {state.physics.on_ground}")
    print(f"  Jumps left: {state.jumps_left}")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")

    # Track velocity changes
    velocity_changes = []
    bus.subscribe(VelocityChangeEvent, lambda e: velocity_changes.append(e))

    # Request double jump
    print(f"\nRequesting double jump...")
    jump_mechanic.request_jump()
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"\nAfter double jump:")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")
    print(f"  Jumps left: {state.jumps_left}")

    # Verify double jump executed
    assert state.physics.vy < 0, "Double jump should set negative vy"
    assert state.jumps_left == 0, f"Expected 0 jumps remaining, got {state.jumps_left}"
    assert len(velocity_changes) == 1
    assert velocity_changes[0].reason == "double_jump"

    print(f"\n[PASS] Double Jump Test PASSED")


def test_wall_jump():
    """Test wall jump"""
    print("\n" + "="*60)
    print("Testing Wall Jump")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=0.0, width=20, height=20)
    physics.on_ground = False
    physics.on_wall = True
    physics.wall_dir = 1  # Wall on right

    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )
    state.stamina = 10.0
    state.stamina_max = 10.0

    jump_mechanic = JumpMechanic(
        entity_id=0,
        event_bus=bus,
        logger=logger,
        feature_flags={"wall_jump": True}
    )

    print(f"\nInitial state:")
    print(f"  On wall: {state.physics.on_wall}")
    print(f"  Wall dir: {state.physics.wall_dir}")
    print(f"  Facing: {state.facing}")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")

    # Track velocity changes
    velocity_changes = []
    bus.subscribe(VelocityChangeEvent, lambda e: velocity_changes.append(e))

    # Request wall jump
    print(f"\nRequesting wall jump...")
    jump_mechanic.request_jump()
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"\nAfter wall jump:")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")
    print(f"  Facing: {state.facing}")
    print(f"  Wall jump lock: {state.wall_jump_lock:.3f}s")
    print(f"  Is dashing: {state.is_dashing}")

    # Verify wall jump executed
    assert state.physics.vy < 0, "Wall jump should set negative vy"
    assert state.physics.vx < 0, f"Wall jump should push left (wall on right), got vx={state.physics.vx}"
    assert state.facing == -1, "Should face away from wall"
    assert state.wall_jump_lock > 0.0, "Wall jump lock should be active"
    assert state.is_dashing == False, "Dash should be cancelled"
    assert len(velocity_changes) == 1
    assert velocity_changes[0].reason == "wall_jump"

    print(f"\n[PASS] Wall Jump Test PASSED")


def test_crouch_jump():
    """Test crouch jump modifier (reduced power)"""
    print("\n" + "="*60)
    print("Testing Crouch Jump Modifier")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=0.0, width=20, height=20)
    physics.on_ground = True
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=True,  # Crouching
        is_dashing=False
    )

    jump_mechanic = JumpMechanic(entity_id=0, event_bus=bus, logger=logger)

    print(f"\nInitial state:")
    print(f"  Crouching: {state.crouching}")
    print(f"  On ground: {state.physics.on_ground}")

    # Request jump while crouching
    print(f"\nRequesting jump while crouching...")
    jump_mechanic.request_jump()
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"\nAfter crouch jump:")
    print(f"  Velocity: ({state.physics.vx}, {state.physics.vy})")

    # Verify reduced jump power
    expected_vy = -14.5 * 0.7  # JUMP_POWER * CROUCH_JUMP_MULT
    assert abs(state.physics.vy - expected_vy) < 0.01, \
        f"Expected vy={expected_vy:.2f}, got {state.physics.vy:.2f}"

    print(f"\n[PASS] Crouch Jump Test PASSED")


def test_collision_reset():
    """Test collision response (reset jumps on ground landing)"""
    print("\n" + "="*60)
    print("Testing Collision Response")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=5.0, width=20, height=20)
    physics.on_ground = False
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )
    state.jumps_left = 0  # No jumps remaining

    jump_mechanic = JumpMechanic(entity_id=0, event_bus=bus, logger=logger)

    print(f"\nInitial state:")
    print(f"  Jumps left: {state.jumps_left}")
    print(f"  On ground: {state.physics.on_ground}")

    # Emit ground collision event
    print(f"\nEmitting ground collision event...")
    collision_event = CollisionEvent(
        entity_id=0,
        collision_type='ground',
        normal=(0, -1),
        tile_rect=None
    )

    # Call collision handler directly
    jump_mechanic.on_collision(state, collision_event)

    print(f"\nAfter ground collision:")
    print(f"  Jumps left: {state.jumps_left}")

    # Verify jumps reset
    assert state.jumps_left == 2, f"Expected jumps reset to 2, got {state.jumps_left}"

    print(f"\n[PASS] Collision Response Test PASSED")


def test_feature_flags():
    """Test feature flag toggling"""
    print("\n" + "="*60)
    print("Testing Feature Flags")
    print("="*60)

    bus = EventBus()
    logger = GameLogger().get_logger("test_jump")

    physics = PhysicsState(x=100, y=100, vx=0.0, vy=0.0, width=20, height=20)
    physics.on_ground = False
    state = PlayerState(
        player_id=0,
        physics=physics,
        health_state=HealthState(current_hp=5, max_hp=5),
        facing=1,
        crouching=False,
        is_dashing=False
    )
    state.jumps_left = 1

    # Create mechanic with double jump disabled
    jump_mechanic = JumpMechanic(
        entity_id=0,
        event_bus=bus,
        logger=logger,
        feature_flags={"double_jump": False}
    )

    print(f"\nDouble jump disabled:")
    print(f"  Jumps left: {state.jumps_left}")
    print(f"  Can activate: {jump_mechanic.can_activate(state)}")

    # Try double jump (should fail)
    jump_mechanic.request_jump()
    jump_mechanic.on_tick(state, dt=1/60)
    bus.process()

    print(f"  After jump request: vy={state.physics.vy}")

    assert state.physics.vy == 0.0, "Double jump should be disabled"

    print(f"\n[PASS] Feature Flags Test PASSED")


def main():
    """Run all jump mechanic tests"""
    print("\n" + "#"*60)
    print("#  JUMP MECHANIC TEST")
    print("#"*60)

    try:
        test_ground_jump()
        test_coyote_time()
        test_jump_buffering()
        test_double_jump()
        test_wall_jump()
        test_crouch_jump()
        test_collision_reset()
        test_feature_flags()

        print("\n" + "="*60)
        print("[PASS] ALL JUMP MECHANIC TESTS PASSED")
        print("="*60)
        print("\nJump mechanic is working correctly!")
        print("Features verified:")
        print("  - Ground jump")
        print("  - Coyote time (grace period)")
        print("  - Jump buffering (input window)")
        print("  - Double jump")
        print("  - Wall jump")
        print("  - Crouch jump modifier")
        print("  - Collision response")
        print("  - Feature flag toggling")
        print("\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
