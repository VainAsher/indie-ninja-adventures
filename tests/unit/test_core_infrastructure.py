"""
Test script for Phase 1: Core Infrastructure

This script verifies that all core systems are working correctly:
- Event bus (subscription, emission, processing)
- Logger (persistent storage, module loggers)
- Clock (fixed timestep, tick events)
- State (serialization, deserialization)
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    CollisionEvent,
    EventBus,
    GameClock,
    GameLogger,
    RenderEvent,
    StateManager,
    TickEvent,
)


def test_event_bus():
    """Test event bus functionality"""
    print("\n" + "=" * 60)
    print("Testing Event Bus")
    print("=" * 60)

    # Create event bus
    bus = EventBus()

    # Track events
    tick_events = []
    collision_events = []

    def on_tick(event: TickEvent):
        tick_events.append(event)
        print(f"  [OK] Received TickEvent: tick={event.tick_number}, dt={event.dt}")

    def on_collision(event: CollisionEvent):
        collision_events.append(event)
        print(
            f"  [OK] Received CollisionEvent: entity={event.entity_id}, type={event.collision_type}"
        )

    # Subscribe
    bus.subscribe(TickEvent, on_tick)
    bus.subscribe(CollisionEvent, on_collision)

    # Emit events
    print("\nEmitting events...")
    bus.emit(TickEvent(dt=0.0167, tick_number=1))
    bus.emit(CollisionEvent(entity_id=0, collision_type="ground", normal=(0, -1)))
    bus.emit(TickEvent(dt=0.0167, tick_number=2))

    # Process queue
    print("\nProcessing event queue...")
    bus.process()

    # Verify
    assert len(tick_events) == 2, f"Expected 2 tick events, got {len(tick_events)}"
    assert len(collision_events) == 1, f"Expected 1 collision event, got {len(collision_events)}"

    print("\n[PASS] Event Bus Test PASSED")
    print(f"   - Tick events received: {len(tick_events)}")
    print(f"   - Collision events received: {len(collision_events)}")


def test_logger():
    """Test logger functionality"""
    print("\n" + "=" * 60)
    print("Testing Logger System")
    print("=" * 60)

    # Create logger
    logger = GameLogger()

    print("\nLogger initialized:")
    print(f"  - Log directory: {logger.log_dir}")
    print(f"  - Log file: {logger.log_file.name}")

    # Get module logger
    test_logger = logger.get_logger("test_module")

    # Log messages
    print("\nLogging test messages...")
    test_logger.debug("This is a DEBUG message")
    test_logger.info("This is an INFO message")
    test_logger.warning("This is a WARNING message")

    # Verify log file exists
    assert logger.log_file.exists(), "Log file was not created"

    print("\n[PASS] Logger Test PASSED")
    print(f"   - Log file created: {logger.log_file}")
    print(f"   - Log file size: {logger.log_file.stat().st_size} bytes")


def test_clock():
    """Test game clock functionality"""
    print("\n" + "=" * 60)
    print("Testing Game Clock")
    print("=" * 60)

    # Create event bus and logger
    bus = EventBus()
    logger = GameLogger().get_logger("test_clock")

    # Create clock
    clock = GameClock(bus, logger)

    # Track events
    tick_count = 0
    render_count = 0

    def on_tick(event: TickEvent):
        nonlocal tick_count
        tick_count += 1

    def on_render(event: RenderEvent):
        nonlocal render_count
        render_count += 1

    bus.subscribe(TickEvent, on_tick)
    bus.subscribe(RenderEvent, on_render)

    # Run a few ticks
    print("\nRunning 5 frames...")
    import time

    for _ in range(5):
        time.sleep(0.02)  # Sleep 20ms to allow accumulator to build up
        clock.tick()
        bus.process()

    print("\nClock statistics:")
    print(f"  - Physics ticks: {tick_count}")
    print(f"  - Render frames: {render_count}")
    print(f"  - Current tick: {clock.get_current_tick()}")
    print(f"  - Current frame: {clock.get_current_frame()}")

    assert render_count == 5, f"Expected 5 render events, got {render_count}"
    assert tick_count > 0, f"Expected some tick events, got {tick_count}"

    print("\n[PASS] Clock Test PASSED")


def test_state():
    """Test state serialization"""
    print("\n" + "=" * 60)
    print("Testing State Management")
    print("=" * 60)

    # Create state manager
    state_manager = StateManager()

    # Add player
    print("\nAdding player...")
    state_manager.add_player(0, spawn_x=100.0, spawn_y=200.0)

    # Get player state
    player = state_manager.get_player_state(0)
    assert player is not None, "Player not found"

    print("Player state:")
    print(f"  - ID: {player.player_id}")
    print(f"  - Position: ({player.physics.x}, {player.physics.y})")
    print(f"  - Health: {player.health_state.current_hp}/{player.health_state.max_hp}")

    # Modify state
    player.physics.vx = 5.0
    player.physics.vy = -10.0
    player.health_state.current_hp = 3

    # Create snapshot
    print("\nCreating state snapshot...")
    snapshot = state_manager.snapshot()

    # Verify snapshot
    player_snapshot = snapshot["players"][0]
    assert player_snapshot["physics"]["x"] == 100.0
    assert player_snapshot["physics"]["vx"] == 5.0
    assert player_snapshot["health_state"]["current_hp"] == 3

    # Restore from snapshot
    print("Restoring from snapshot...")
    state_manager.restore(snapshot)
    restored_player = state_manager.get_player_state(0)

    assert restored_player.physics.x == 100.0
    assert restored_player.physics.vx == 5.0
    assert restored_player.health_state.current_hp == 3

    print("\n[PASS] State Test PASSED")
    print("   - Serialization: OK")
    print("   - Deserialization: OK")
    print("   - State restore: OK")


def test_integration():
    """Test all systems working together"""
    print("\n" + "=" * 60)
    print("Testing Integrated Systems")
    print("=" * 60)

    # Create all core systems
    bus = EventBus()
    logger = GameLogger()
    clock = GameClock(bus, logger.get_logger("clock"))
    state_manager = StateManager()

    # Add player
    state_manager.add_player(0, spawn_x=0.0, spawn_y=0.0)

    # Subscribe to tick events
    def on_tick(event: TickEvent):
        player = state_manager.get_player_state(0)
        if player:
            # Simulate simple physics
            player.physics.vy += 0.7  # Gravity
            player.physics.y += player.physics.vy

    bus.subscribe(TickEvent, on_tick)

    # Run simulation
    print("\nRunning integrated simulation for 10 frames...")
    import time

    for _ in range(10):
        time.sleep(0.02)  # Sleep 20ms to allow accumulator to build up
        clock.tick()
        bus.process()

    # Check player fell
    player = state_manager.get_player_state(0)
    print("\nPlayer state after simulation:")
    print(f"  - Position: ({player.physics.x:.1f}, {player.physics.y:.1f})")
    print(f"  - Velocity: ({player.physics.vx:.1f}, {player.physics.vy:.1f})")

    assert player.physics.y > 0, "Player should have fallen"
    assert player.physics.vy > 0, "Player should have downward velocity"

    print("\n[PASS] Integration Test PASSED")
    print("   - Event bus + Clock: OK")
    print("   - Clock + State: OK")
    print("   - Full pipeline: OK")


def main():
    """Run all tests"""
    print("\n" + "#" * 60)
    print("#  NINJA DASH - PHASE 1 CORE INFRASTRUCTURE TEST")
    print("#" * 60)

    try:
        test_event_bus()
        test_logger()
        test_clock()
        test_state()
        test_integration()

        print("\n" + "=" * 60)
        print("[PASS] ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 1 core infrastructure is working correctly!")
        print("Next steps:")
        print("  - Phase 2: Implement collision system")
        print("  - Phase 3: Implement first mechanic (jump)")
        print("\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
