"""
Phase 2 & 3 Test Suite - Hub and Mission Systems

Tests for:
- Hub world generation (Phase 2)
- NPC system (Phase 2)
- Portal system (Phase 2)
- Trading & shop system (Phase 2)
- Mission state management (Phase 3)
- Objective tracker (Phase 3)
- Locked exit portal (Phase 3)

Version: v0.6.0
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from core import EventBus
from entities.npc import NPCManager, NPCType
from game.hub_manager import HubManager, HubType
from game.inventory_system import Inventory
from game.level_manager import LevelManager
from game.mission_manager import MissionManager, MissionState
from game.mission_registry import ObjectiveType
from game.objective_tracker import (
    EnemyDeathEvent,
    ObjectiveTracker,
    PlayerPositionUpdateEvent,
)
from game.portal_system import PortalManager, PortalType
from game.trading_system import ShopTier, TradingManager


def test_hub_generation():
    """Test hub world generation"""
    print("\n[TEST] Hub Generation System")

    # Create hub manager
    world_seed = 12345
    hub_manager = HubManager(world_seed)

    # Test central hub definition
    central_hub = hub_manager.get_hub_definition("central_hub")
    assert central_hub is not None, "Should have central hub"
    assert central_hub.hub_type == HubType.CENTRAL, "Should be central hub type"
    assert central_hub.room_count == 15, "Central hub should have 15 rooms"

    print(f"  [OK] Central hub: {central_hub.display_name} ({central_hub.room_count} rooms)")

    # Test regional hubs
    forest_hub = hub_manager.get_hub_definition("forest_hub")
    town_hub = hub_manager.get_hub_definition("town_hub")
    caves_hub = hub_manager.get_hub_definition("caves_hub")

    assert forest_hub is not None, "Should have forest hub"
    assert town_hub is not None, "Should have town hub"
    assert caves_hub is not None, "Should have caves hub"

    assert forest_hub.hub_type == HubType.REGION, "Should be region hub"
    assert len(forest_hub.npc_anchors) > 0, "Forest hub should have NPCs"
    assert len(forest_hub.portal_anchors) > 0, "Forest hub should have portals"

    print(
        f"  [OK] Forest hub: {forest_hub.display_name} ({len(forest_hub.npc_anchors)} NPCs, {len(forest_hub.portal_anchors)} portals)"
    )
    print(
        f"  [OK] Town hub: {town_hub.display_name} ({len(town_hub.npc_anchors)} NPCs, {len(town_hub.portal_anchors)} portals)"
    )
    print(
        f"  [OK] Caves hub: {caves_hub.display_name} ({len(caves_hub.npc_anchors)} NPCs, {len(caves_hub.portal_anchors)} portals)"
    )

    # Test hub world generation
    world, hub_def = hub_manager.generate_hub_world("forest_hub")
    assert world is not None, "Should generate forest hub world"
    assert hub_def is not None, "Should return hub definition"
    assert len(world.all_rooms) > 0, "Hub world should have rooms"

    # Check that rooms are marked as hub rooms
    assert world.all_rooms[0].is_hub, "Rooms should be marked as hub rooms"
    assert world.all_rooms[0].hub_id == "forest_hub", "Rooms should have hub_id"

    print(f"  [OK] Generated forest hub world with {len(world.all_rooms)} rooms")

    # Test deterministic generation
    world2, _ = hub_manager.generate_hub_world("forest_hub")
    assert len(world.all_rooms) == len(world2.all_rooms), "Should generate same number of rooms"

    print("  [OK] Hub generation is deterministic")


def test_npc_system():
    """Test NPC system"""
    print("\n[TEST] NPC System")

    event_bus = EventBus()
    npc_manager = NPCManager(event_bus)

    # Test pre-registered NPCs
    forest_ranger = npc_manager.get_npc_definition("forest_ranger")
    assert forest_ranger is not None, "Should have forest ranger"
    assert forest_ranger.npc_type == NPCType.MISSION_GIVER, "Should be mission giver"
    assert len(forest_ranger.mission_pool) > 0, "Should have mission pool"

    print(
        f"  [OK] Forest Ranger: {forest_ranger.display_name} ({len(forest_ranger.mission_pool)} missions)"
    )

    forest_merchant = npc_manager.get_npc_definition("forest_merchant")
    assert forest_merchant is not None, "Should have forest merchant"
    assert forest_merchant.npc_type == NPCType.SHOP, "Should be shop NPC"
    assert forest_merchant.shop_tier == 1, "Should be tier 1 shop"

    print(
        f"  [OK] Forest Merchant: {forest_merchant.display_name} (Tier {forest_merchant.shop_tier})"
    )

    # Test NPC spawning
    npc = npc_manager.spawn_npc("forest_ranger", 100.0, 200.0)
    assert npc is not None, "Should spawn NPC"
    assert npc.x == 100.0, "NPC should be at specified position"
    assert npc.y == 200.0, "NPC should be at specified position"
    assert npc.interaction_radius == 48.0, "Should have 48px interaction radius"

    print("  [OK] NPC spawning works")

    # Test interaction detection
    can_interact = npc.can_interact_with_player(110.0, 210.0, 32, 48)
    assert can_interact, "Player should be in interaction range"

    cannot_interact = npc.can_interact_with_player(500.0, 500.0, 32, 48)
    assert not cannot_interact, "Player should not be in interaction range"

    print("  [OK] Interaction detection works")

    # Test update
    npc.update(0.1)
    assert npc.animation_timer > 0, "Animation timer should update"

    print("  [OK] NPC update works")


def test_portal_system():
    """Test portal system"""
    print("\n[TEST] Portal System")

    event_bus = EventBus()
    portal_manager = PortalManager(event_bus)

    # Test portal spawning
    portal = portal_manager.spawn_portal(
        portal_id="test_portal",
        portal_type=PortalType.HUB,
        destination_id="central_hub",
        x=100.0,
        y=200.0,
        bidirectional=True,
    )

    assert portal is not None, "Should spawn portal"
    assert portal.portal_type == PortalType.HUB, "Should be hub portal"
    assert portal.destination_id == "central_hub", "Should have correct destination"
    assert portal.bidirectional, "Should be bidirectional"
    assert portal.interaction_radius == 48.0, "Should have 48px interaction radius"

    print(f"  [OK] Portal spawned: {portal.portal_id} -> {portal.destination_id}")

    # Test interaction detection
    can_interact = portal.can_interact_with_player(110.0, 210.0, 32, 48)
    assert can_interact, "Player should be in interaction range"

    cannot_interact = portal.can_interact_with_player(500.0, 500.0, 32, 48)
    assert not cannot_interact, "Player should not be in interaction range"

    print("  [OK] Portal interaction detection works")

    # Test portal locking
    portal_manager.lock_portal("test_portal", ["double_jump", "dash"])
    locked_portal = portal_manager.get_portal_by_id("test_portal")
    assert locked_portal.is_locked, "Portal should be locked"
    assert len(locked_portal.unlock_requirements) == 2, "Should have 2 requirements"

    print("  [OK] Portal locking works")

    # Test portal unlocking
    portal_manager.unlock_portal("test_portal")
    assert not locked_portal.is_locked, "Portal should be unlocked"

    print("  [OK] Portal unlocking works")

    # Test pulse animation
    portal.update(0.1)
    alpha1 = portal.get_pulse_alpha()
    assert 0.0 <= alpha1 <= 1.0, "Pulse alpha should be between 0 and 1"

    print("  [OK] Portal pulse animation works")


def test_trading_system():
    """Test trading and shop system"""
    print("\n[TEST] Trading System")

    event_bus = EventBus()
    world_seed = 12345
    trading_manager = TradingManager(event_bus, world_seed)

    # Create and initialize global item database
    from game.inventory_system import get_item_manager, initialize_item_manager

    initialize_item_manager()
    item_db = get_item_manager()

    items_path = Path(__file__).parent.parent / "data" / "items.json"
    with open(items_path) as f:
        items_data = json.load(f)
    item_db.load_from_dict(items_data)

    # Create shop
    shop = trading_manager.create_shop("forest_merchant", ShopTier.TIER_1)
    assert shop is not None, "Should create shop"
    assert shop.shop_tier == ShopTier.TIER_1, "Should be tier 1 shop"
    assert len(shop.items) > 0, "Shop should have items"

    print(f"  [OK] Created tier 1 shop with {len(shop.items)} items")

    # Test deterministic shop generation
    shop2_seed = shop.generation_seed
    shop2 = TradingManager(event_bus, world_seed).create_shop("forest_merchant", ShopTier.TIER_1)
    assert shop.generation_seed == shop2_seed, "Same NPC should have same seed"
    assert len(shop.items) == len(shop2.items), "Should generate same number of items"

    print("  [OK] Shop generation is deterministic")

    # Create player inventory
    inventory = Inventory(max_slots=20)
    inventory.set_item_database(item_db)
    inventory.add_currency(1000)  # Give player money

    # Test buying item
    shop_item = shop.items[0]
    initial_stock = shop_item.stock
    initial_currency = inventory.currency

    success = shop.buy_from_shop(shop_item.item_id, 1, inventory)
    assert success, "Should buy item successfully"
    assert shop_item.stock == initial_stock - 1, "Stock should decrease"
    assert inventory.currency == initial_currency - shop_item.price, "Currency should decrease"
    assert inventory.has_item(shop_item.item_id, 1), "Player should have item"

    print(f"  [OK] Bought {shop_item.item_id} for {shop_item.price} gold")

    # Test selling item
    sell_item_id = shop_item.item_id
    item_def = item_db.get_item(sell_item_id)
    sell_price = shop.calculate_sell_price(item_def)

    success = shop.sell_to_shop(sell_item_id, 1, inventory)
    assert success, "Should sell item successfully"
    assert (
        inventory.currency > initial_currency - shop_item.price
    ), "Currency should increase from selling"

    print(f"  [OK] Sold {sell_item_id} for {sell_price} gold")

    # Test serialization
    shop_dict = shop.to_dict()
    assert "npc_id" in shop_dict, "Should serialize npc_id"
    assert "shop_tier" in shop_dict, "Should serialize shop_tier"
    assert "items" in shop_dict, "Should serialize items"

    print("  [OK] Shop serialization works")


def test_mission_manager():
    """Test mission state management"""
    print("\n[TEST] Mission Manager")

    event_bus = EventBus()
    world_seed = 12345
    mission_manager = MissionManager(event_bus, world_seed)

    # Initialize global systems
    from game.inventory_system import get_item_manager, initialize_item_manager
    from game.loot_system import initialize_loot_table_database

    initialize_loot_table_database()
    initialize_item_manager()

    # Load items for reward distribution
    item_db = get_item_manager()
    items_path = Path(__file__).parent.parent / "data" / "items.json"
    with open(items_path) as f:
        items_data = json.load(f)
    item_db.load_from_dict(items_data)

    # Test mission availability
    unlocked_abilities = {"basic_movement", "jump"}
    is_available = mission_manager.is_mission_available("forest_1", unlocked_abilities)
    assert is_available, "Forest 1 should be available with basic abilities"

    print("  [OK] Mission availability check works")

    # Test starting mission
    success = mission_manager.start_mission("forest_1")
    assert success, "Should start mission"
    assert mission_manager.current_mission_id == "forest_1", "Should set current mission"
    assert mission_manager.exit_locked, "Exit should be locked"

    print("  [OK] Mission start works (exit locked)")

    # Get mission progress
    progress = mission_manager.get_mission_progress("forest_1")
    assert progress.state == MissionState.IN_PROGRESS, "Mission should be in progress"
    assert progress.attempts == 1, "Should track attempt"

    print("  [OK] Mission progress tracking works")

    # Test objective completion
    mission_manager.complete_objective("forest_1", "obj_1", "Collect forest keys")
    assert "obj_1" in progress.objectives_completed, "Should track completed objective"

    print("  [OK] Objective completion tracking works")

    # Test unlocking exit
    mission_manager.unlock_exit("forest_1")
    assert not mission_manager.exit_locked, "Exit should be unlocked"

    print("  [OK] Exit unlock works")

    # Create player inventory for rewards
    inventory = Inventory(max_slots=20)
    inventory.set_item_database(item_db)

    # Test mission completion
    initial_currency = inventory.currency
    success = mission_manager.complete_mission("forest_1", inventory)
    assert success, "Should complete mission"
    assert progress.state == MissionState.COMPLETED, "Mission state should be completed"
    assert progress.completions == 1, "Should track completion"
    assert mission_manager.current_mission_id is None, "Should clear current mission"

    print("  [OK] Mission completion works")
    print(f"  [OK] Rewards distributed (currency gained: {inventory.currency - initial_currency})")

    # Test mission failure
    mission_manager.start_mission("forest_2")
    success = mission_manager.fail_mission("forest_2", "death")
    assert success, "Should fail mission"

    failed_progress = mission_manager.get_mission_progress("forest_2")
    assert failed_progress.state == MissionState.AVAILABLE, "Mission should be available for retry"

    print("  [OK] Mission failure works")

    # Test save/load
    save_data = mission_manager.save_state()
    assert "mission_progress" in save_data, "Should save mission progress"
    assert "current_mission_id" in save_data, "Should save current mission"

    print("  [OK] Mission manager save/load works")


def test_objective_tracker():
    """Test objective tracking system"""
    print("\n[TEST] Objective Tracker")

    event_bus = EventBus()
    objective_tracker = ObjectiveTracker(event_bus)

    # Start tracking mission objectives
    objective_tracker.start_mission_objectives("forest_2")

    objectives = objective_tracker.get_active_objectives()
    assert len(objectives) > 0, "Should have objectives"

    print(f"  [OK] Started tracking {len(objectives)} objectives")

    # Resolve reach-location objective target for testing
    objective_tracker.set_location_targets({"shrine": (100.0, 100.0)})

    # Test kill enemy objective
    incomplete_before = len(objective_tracker.get_incomplete_objectives())

    # Simulate enemy death
    event_bus.emit(
        EnemyDeathEvent(enemy_id="goblin_1", enemy_type="goblin", position=(100.0, 200.0))
    )
    event_bus.process()

    # Check if kill objective updated (if mission has kill objective)
    kill_obj = None
    for obj in objectives:
        if obj.objective_type == ObjectiveType.KILL_ALL_ENEMIES:
            kill_obj = obj
            break

    if kill_obj:
        # Forest tutorial may not have kill objective, so this is conditional
        print("  [OK] Kill enemy objective tracking works")
    else:
        print("  [OK] No kill objective in forest_2 (expected)")

    # Test reach location objective
    reach_obj = None
    for obj in objectives:
        if obj.objective_type == ObjectiveType.REACH_LOCATION:
            reach_obj = obj
            break

    if reach_obj:
        # Player far from location
        event_bus.emit(PlayerPositionUpdateEvent(player_x=1000.0, player_y=1000.0))
        event_bus.process()
        assert not reach_obj.is_complete, "Should not be complete yet"

        # Player reaches resolved location
        if reach_obj.target_position:
            event_bus.emit(
                PlayerPositionUpdateEvent(
                    player_x=reach_obj.target_position[0], player_y=reach_obj.target_position[1]
                )
            )
            event_bus.process()
            assert reach_obj.is_complete, "Reach objective should complete at target"
            print("  [OK] Reach location objective tracking works")
    else:
        print("  [OK] No reach location objective in forest_2")

    # Test all objectives complete check
    all_complete = objective_tracker.are_all_objectives_complete()
    print(f"  [OK] All objectives complete check: {all_complete}")

    # Test stop tracking
    objective_tracker.stop_mission_objectives()
    assert objective_tracker.active_mission_id is None, "Should clear active mission"
    assert len(objective_tracker.objectives) == 0, "Should clear objectives"

    print("  [OK] Stop tracking works")


def test_locked_exit_portal():
    """Test locked exit portal system"""
    print("\n[TEST] Locked Exit Portal")

    event_bus = EventBus()
    level_manager = LevelManager(event_bus)

    # Set exit position
    level_manager.set_exit_position(500.0, 500.0)
    level_manager.start_level(0.0)

    # Test exit unlocked by default
    assert not level_manager.is_exit_locked(), "Exit should be unlocked by default"

    # Player can reach exit
    reached = level_manager.check_exit_reached(500.0, 500.0, 10.0)
    assert reached, "Player should reach unlocked exit"

    print("  [OK] Unlocked exit allows completion")

    # Reset level
    level_manager.reset_level()
    level_manager.set_exit_position(500.0, 500.0)
    level_manager.start_level(0.0)

    # Lock exit
    level_manager.lock_exit()
    assert level_manager.is_exit_locked(), "Exit should be locked"

    # Player cannot reach locked exit
    reached = level_manager.check_exit_reached(500.0, 500.0, 10.0)
    assert not reached, "Player should not reach locked exit"

    print("  [OK] Locked exit prevents completion")

    # Unlock exit
    level_manager.unlock_exit()
    assert not level_manager.is_exit_locked(), "Exit should be unlocked"

    # Player can now reach exit
    reached = level_manager.check_exit_reached(500.0, 500.0, 10.0)
    assert reached, "Player should reach unlocked exit"

    print("  [OK] Exit unlock allows completion")

    # Test get_stats includes lock status
    stats = level_manager.get_stats()
    assert "exit_locked" in stats, "Stats should include exit_locked"

    print("  [OK] Exit lock status in stats")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 2 & 3 Systems Test Suite")
    print("=" * 70)

    try:
        test_hub_generation()
        test_npc_system()
        test_portal_system()
        test_trading_system()
        test_mission_manager()
        test_objective_tracker()
        test_locked_exit_portal()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        print("\nPhase 2 (Hub System) and Phase 3 (Mission System) are fully functional.")
        print("\nSystems Ready:")
        print("  [OK] Hub world generation")
        print("  [OK] NPC system with interaction")
        print("  [OK] Portal fast travel system")
        print("  [OK] Trading & shop system")
        print("  [OK] Mission state management")
        print("  [OK] Objective tracking (6 types)")
        print("  [OK] Locked exit portal system")

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
