"""
Phase 1 Foundation Test Suite

Tests all systems created in Phase 1:
- Health system (HP, damage, invincibility frames)
- Inventory system (items, equipment, currency)
- Loot system (deterministic drops)
- Seed hierarchy (6-level derivation)
- Mission system (missions, regions, progression)
- Item database (loading from JSON)

Run with: python tests/test_phase1_foundation.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.health_system import HealthState
from game.inventory_system import Inventory, ItemDatabase, ItemRarity, ItemType
from game.loot_system import LootGenerator, LootTable, LootTableDatabase
from game.mission_registry import ObjectiveType, get_mission_registry
from systems.seed_hierarchy import SeedContext, SeedDerivation, SeedHierarchyValidator


def test_health_system():
    """Test health system functionality"""
    print("\n[TEST] Health System")

    # Create health state
    health = HealthState(current_hp=3, max_hp=5)

    # Test initial state
    assert health.is_alive(), "Should be alive with 3 HP"
    assert not health.is_full_health(), "Should not be at full health (3/5)"
    assert health.get_health_percentage() == 0.6, "Should be at 60% health"

    # Test damage without defense
    died = health.take_damage(1, defense=0)
    assert not died, "Should not die from 1 damage (3 -> 2 HP)"
    assert health.current_hp == 2, "Should have 2 HP after taking 1 damage"
    assert health.is_invincible(), "Should be invincible after taking damage"

    # Test invincibility frames prevent damage
    died = health.take_damage(5, defense=0)
    assert not died, "Should not take damage during invincibility"
    assert health.current_hp == 2, "HP should not change during invincibility"

    # Clear invincibility frames
    health.invincibility_frames = 0

    # Test damage with defense
    died = health.take_damage(2, defense=1)
    assert not died, "Should not die from 2 damage with 1 defense (2 -> 1 HP)"
    assert health.current_hp == 1, "Should have 1 HP (2 damage - 1 defense = 1 effective damage)"

    # Test low health warning
    assert health.is_low_health(threshold=0.25), "Should be low health at 1/5 HP"

    # Clear invincibility again
    health.invincibility_frames = 0

    # Test death
    died = health.take_damage(1, defense=0)
    assert died, "Should die when HP reaches 0"
    assert health.current_hp == 0, "Should have 0 HP"
    assert health.is_dead(), "Should be dead"
    assert not health.is_alive(), "Should not be alive"

    # Test healing
    health.heal(2)
    assert health.current_hp == 2, "Should heal to 2 HP"
    assert health.is_alive(), "Should be alive after healing"

    # Test heal capping at max HP
    health.heal(100)
    assert health.current_hp == 5, "Should cap at max_hp (5)"
    assert health.is_full_health(), "Should be at full health"

    # Test max HP increase
    health.increase_max_hp(2)
    assert health.max_hp == 7, "Max HP should increase to 7"
    assert health.current_hp == 7, "Current HP should also increase by 2"

    # Test reset to full
    health.current_hp = 3
    health.invincibility_frames = 30
    health.reset_to_full()
    assert health.current_hp == 7, "Should reset to max HP"
    assert health.invincibility_frames == 0, "Should clear invincibility frames"

    print("  [OK] Health state tracking works")
    print("  [OK] Damage calculation with defense works")
    print("  [OK] Invincibility frames prevent damage")
    print("  [OK] Healing and max HP increases work")
    print("  [OK] Death detection works correctly")


def test_inventory_system():
    """Test inventory system functionality"""
    print("\n[TEST] Inventory System")

    # Create item database
    item_db = ItemDatabase()

    # Load items from JSON
    items_path = Path(__file__).parent.parent / "data" / "items.json"
    with open(items_path) as f:
        items_data = json.load(f)
    item_db.load_from_dict(items_data)

    assert len(item_db.items) > 0, "Should load items from JSON"
    assert item_db.get_item("health_potion_small") is not None, "Should have health potions"
    assert item_db.get_item("weapon_sword") is not None, "Should have weapons"

    print(f"  [OK] Loaded {len(item_db.items)} items from database")

    # Create inventory
    inventory = Inventory(max_slots=20)
    inventory.set_item_database(item_db)

    # Test adding items
    success = inventory.add_item("health_potion_small", 3)
    assert success, "Should add 3 small health potions"
    assert inventory.has_item("health_potion_small", 3), "Should have 3 health potions"

    # Test item stacking
    success = inventory.add_item("health_potion_small", 5)
    assert success, "Should stack more health potions"
    assert inventory.get_item_count("health_potion_small") == 8, "Should have 8 total"

    # Test removing items
    success = inventory.remove_item("health_potion_small", 3)
    assert success, "Should remove 3 health potions"
    assert inventory.get_item_count("health_potion_small") == 5, "Should have 5 left"

    # Test equipment
    inventory.add_item("weapon_sword", 1)
    inventory.add_item("armor_leather", 1)

    success = inventory.equip_item("weapon_sword")
    assert success, "Should equip sword"
    assert inventory.equipped_weapon == "weapon_sword", "Sword should be equipped"

    success = inventory.equip_item("armor_leather")
    assert success, "Should equip leather armor"
    assert inventory.equipped_armor == "armor_leather", "Armor should be equipped"

    # Test stat bonuses from equipment
    stats = inventory.get_total_stats()
    assert stats["attack"] > 0, "Should have attack bonus from sword"
    assert stats["defense"] > 0, "Should have defense bonus from armor"

    print("  [OK] Item adding and stacking works")
    print("  [OK] Item removal works")
    print("  [OK] Equipment system works")
    print("  [OK] Stat bonuses calculated correctly")

    # Test currency
    inventory.add_currency(100)
    assert inventory.currency == 100, "Should have 100 currency"

    success = inventory.remove_currency(30)
    assert success, "Should remove 30 currency"
    assert inventory.currency == 70, "Should have 70 currency left"

    success = inventory.remove_currency(100)
    assert not success, "Should fail to remove more currency than available"
    assert inventory.currency == 70, "Currency should not change on failed removal"

    print("  [OK] Currency system works")

    # Test serialization
    inv_dict = inventory.to_dict()
    assert "slots" in inv_dict, "Should serialize slots"
    assert "currency" in inv_dict, "Should serialize currency"
    assert "equipped_weapon" in inv_dict, "Should serialize equipped weapon"

    # Test deserialization
    inventory2 = Inventory.from_dict(inv_dict)
    inventory2.set_item_database(item_db)
    assert inventory2.currency == 70, "Should deserialize currency"
    assert inventory2.equipped_weapon == "weapon_sword", "Should deserialize equipped weapon"

    print("  [OK] Serialization/deserialization works")


def test_loot_system():
    """Test loot system determinism"""
    print("\n[TEST] Loot System")

    # Create loot table database
    loot_db = LootTableDatabase()

    # Test that default tables are registered
    common_enemy_table = loot_db.get_table("enemy_common")
    assert common_enemy_table is not None, "Should have common enemy loot table"

    boss_table = loot_db.get_table("boss_forest_guardian")
    assert boss_table is not None, "Should have forest boss loot table"

    print(f"  [OK] Loaded {len(loot_db.tables)} loot tables")

    # Test deterministic loot generation
    seed = 12345

    gen1 = LootGenerator(seed)
    items1, currency1 = gen1.generate_loot(common_enemy_table)

    gen2 = LootGenerator(seed)
    items2, currency2 = gen2.generate_loot(common_enemy_table)

    assert items1 == items2, "Same seed should produce same items"
    assert currency1 == currency2, "Same seed should produce same currency"

    print("  [OK] Loot generation is deterministic")

    # Test different seeds produce different results
    gen3 = LootGenerator(54321)
    items3, currency3 = gen3.generate_loot(common_enemy_table)

    # Note: Different seeds MIGHT produce same results by chance, but unlikely
    different = (items1 != items3) or (currency1 != currency3)
    if different:
        print("  [OK] Different seeds produce different loot (verified)")
    else:
        print(r"  [\!] Different seeds produced same loot (possible but unlikely)")

    # Test boss loot (guaranteed drops)
    gen_boss = LootGenerator(99999)
    boss_items, boss_currency = gen_boss.generate_loot(boss_table)

    # Boss should have guaranteed drops
    assert len(boss_items) > 0, "Boss should drop items"
    assert boss_currency > 0, "Boss should drop currency"

    print("  [OK] Boss loot tables work")

    # Test loot table creation
    custom_table = LootTable(
        table_id="test_table", guaranteed_drops=[], chance_drops=[], currency_range=(10, 20)
    )
    custom_table.add_guaranteed_drop("health_potion_small", (1, 1))
    custom_table.add_chance_drop("weapon_sword", (1, 1), 0.5)

    gen_custom = LootGenerator(11111)
    custom_items, custom_currency = gen_custom.generate_loot(custom_table)

    # Should always have guaranteed drop
    has_potion = any(item_id == "health_potion_small" for item_id, qty in custom_items)
    assert has_potion, "Should have guaranteed health potion drop"
    assert 10 <= custom_currency <= 20, "Currency should be in range"

    print("  [OK] Custom loot tables work")


def test_seed_hierarchy():
    """Test 6-level seed hierarchy"""
    print("\n[TEST] Seed Hierarchy")

    world_seed = 42

    # Test level 2: region seeds
    forest_seed = SeedDerivation.derive_region_seed(world_seed, "forest")
    town_seed = SeedDerivation.derive_region_seed(world_seed, "town")

    assert forest_seed != town_seed, "Different regions should have different seeds"
    assert forest_seed > 0, "Seeds should be positive"

    # Test determinism - same inputs produce same outputs
    forest_seed2 = SeedDerivation.derive_region_seed(world_seed, "forest")
    assert forest_seed == forest_seed2, "Same inputs should produce same seed"

    print("  [OK] Level 2 (region) seeds are deterministic and unique")

    # Test level 3: mission seeds
    mission_seed1 = SeedDerivation.derive_mission_seed(forest_seed, "mission_01")
    mission_seed2 = SeedDerivation.derive_mission_seed(forest_seed, "mission_02")

    assert mission_seed1 != mission_seed2, "Different missions should have different seeds"

    print("  [OK] Level 3 (mission) seeds work")

    # Test level 4: room seeds
    room_seed1 = SeedDerivation.derive_room_seed_from_coords(mission_seed1, 0, 0)
    room_seed2 = SeedDerivation.derive_room_seed_from_coords(mission_seed1, 1, 1)

    assert room_seed1 != room_seed2, "Different room coordinates should have different seeds"

    print("  [OK] Level 4 (room) seeds work")

    # Test level 5: subroom seeds
    subroom_seed1 = SeedDerivation.derive_subroom_seed(room_seed1, 0)
    subroom_seed2 = SeedDerivation.derive_subroom_seed(room_seed1, 1)

    assert subroom_seed1 != subroom_seed2, "Different subrooms should have different seeds"

    print("  [OK] Level 5 (subroom) seeds work")

    # Test level 6: feature seeds
    hazard_seed = SeedDerivation.derive_feature_seed(subroom_seed1, "hazards")
    pickup_seed = SeedDerivation.derive_feature_seed(subroom_seed1, "pickups")

    assert hazard_seed != pickup_seed, "Different features should have different seeds"

    print("  [OK] Level 6 (feature) seeds work")

    # Test SeedContext
    ctx = SeedContext(world_seed=42)
    ctx = ctx.with_region("forest").with_mission("mission_01").with_room(0, 0)

    assert ctx.get_region_seed() == forest_seed, "Context should derive correct region seed"
    assert ctx.get_mission_seed() == mission_seed1, "Context should derive correct mission seed"
    assert ctx.get_room_seed() == room_seed1, "Context should derive correct room seed"

    feature_seed_ctx = ctx.get_feature_seed("hazards")
    assert feature_seed_ctx is not None, "Should derive feature seed from context"

    print("  [OK] SeedContext works correctly")

    # Test determinism validation
    is_deterministic = SeedHierarchyValidator.validate_determinism(
        world_seed=42, region_id="forest", mission_id="mission_01", grid_x=0, grid_y=0
    )
    assert is_deterministic, "Seed hierarchy should be deterministic"

    print("  [OK] Determinism validation passed")

    # Test uniqueness validation
    is_unique = SeedHierarchyValidator.validate_uniqueness(
        world_seed=42,
        region_ids=["forest", "town", "caves"],
        mission_ids=["mission_01", "mission_02", "mission_03"],
    )
    assert is_unique, "Seeds should be unique across regions and missions"

    print("  [OK] Uniqueness validation passed")


def test_mission_system():
    """Test mission and region system"""
    print("\n[TEST] Mission System")

    registry = get_mission_registry()

    # Test mission registry
    assert registry.get_mission_count() > 0, "Should have missions loaded"
    print(f"  [OK] Loaded {registry.get_mission_count()} missions")

    # Test getting missions
    forest_1 = registry.get_mission("forest_1")
    assert forest_1 is not None, "Should have forest_1 mission"
    assert forest_1.region == "forest", "Should be in forest region"
    assert len(forest_1.objectives) > 0, "Should have objectives"

    # Test objective types
    forest_2 = registry.get_mission("forest_2")
    assert forest_2 is not None, "Should have forest_2 mission"
    has_reach_objective = any(
        obj.objective_type == ObjectiveType.REACH_LOCATION for obj in forest_2.objectives
    )
    assert has_reach_objective, "Forest_2 should have reach objective"

    print("  [OK] Mission definitions work")

    # Test region lookup (via missions.json)
    forest_missions = registry.get_missions_in_region("forest")
    assert len(forest_missions) > 0, "Should get region missions"
    assert all(m.region == "forest" for m in forest_missions), "All missions should be in forest"

    print("  [OK] Region definitions work")

    # Test unlocking logic
    unlocked_abilities = {"basic_movement", "jump"}

    # Forest_1 should be unlocked with basic abilities
    forest_1_unlocked = registry.is_mission_unlocked("forest_1", unlocked_abilities, set())
    assert forest_1_unlocked, "forest_1 should be unlocked with basic abilities"

    # Forest_2 requires double_jump and forest_1 completion
    forest_2_locked = registry.is_mission_unlocked("forest_2", unlocked_abilities, set())
    assert not forest_2_locked, "forest_2 should be locked without double_jump and prereqs"

    # Add double jump ability
    unlocked_abilities.add("double_jump")

    forest_2_locked = registry.is_mission_unlocked("forest_2", unlocked_abilities, set())
    assert not forest_2_locked, "forest_2 should be locked without prereq completion"

    completed_missions = {"forest_1"}
    forest_2_unlocked = registry.is_mission_unlocked(
        "forest_2", unlocked_abilities, completed_missions
    )
    assert forest_2_unlocked, "forest_2 should unlock after forest_1 with double_jump"

    print("  [OK] Unlock requirements work")
    print("  [OK] Progression logic works")

    # Test mission rewards
    assert forest_1.rewards.currency > 0, "Mission should grant currency"
    assert len(forest_1.rewards.items) > 0, "Mission should grant items"

    print("  [OK] Mission rewards configured")


def test_item_database():
    """Test item database loading"""
    print("\n[TEST] Item Database")

    item_db = ItemDatabase()
    items_path = Path(__file__).parent.parent / "data" / "items.json"

    with open(items_path) as f:
        items_data = json.load(f)

    item_db.load_from_dict(items_data)

    # Test item counts by type
    weapons = item_db.get_items_by_type(ItemType.WEAPON)
    armor = item_db.get_items_by_type(ItemType.ARMOR)
    consumables = item_db.get_items_by_type(ItemType.CONSUMABLE)
    key_items = item_db.get_items_by_type(ItemType.KEY_ITEM)

    print(f"  [OK] {len(weapons)} weapons loaded")
    print(f"  [OK] {len(armor)} armor pieces loaded")
    print(f"  [OK] {len(consumables)} consumables loaded")
    print(f"  [OK] {len(key_items)} key items loaded")

    # Test health items specifically
    small_potion = item_db.get_item("health_potion_small")
    assert small_potion is not None, "Should have small health potion"
    assert small_potion.health_restore == 1, "Small potion should restore 1 HP"

    medium_potion = item_db.get_item("health_potion_medium")
    assert medium_potion.health_restore == 2, "Medium potion should restore 2 HP"

    large_potion = item_db.get_item("health_potion_large")
    assert large_potion.health_restore == 3, "Large potion should restore 3 HP"

    print("  [OK] Health items configured correctly")

    # Test rarity distribution
    legendaries = item_db.get_items_by_rarity(ItemRarity.LEGENDARY)
    epics = item_db.get_items_by_rarity(ItemRarity.EPIC)
    rares = item_db.get_items_by_rarity(ItemRarity.RARE)

    print(f"  [OK] {len(legendaries)} legendary items")
    print(f"  [OK] {len(epics)} epic items")
    print(f"  [OK] {len(rares)} rare items")

    # Test stat bonuses
    legendary_sword = item_db.get_item("weapon_legendary_sword")
    assert legendary_sword is not None, "Should have legendary sword"
    assert legendary_sword.attack_bonus > 0, "Legendary sword should have attack bonus"
    assert legendary_sword.rarity == ItemRarity.LEGENDARY, "Should be legendary rarity"

    legendary_armor = item_db.get_item("armor_legendary_set")
    assert legendary_armor.defense_bonus > 0, "Legendary armor should have defense bonus"
    assert legendary_armor.health_bonus > 0, "Legendary armor should have health bonus"

    print("  [OK] Item stats configured correctly")
    print(f"  [OK] Total items in database: {len(item_db.items)}")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 1 Foundation Test Suite")
    print("=" * 70)

    try:
        test_health_system()
        test_inventory_system()
        test_loot_system()
        test_seed_hierarchy()
        test_mission_system()
        test_item_database()

        print("\n" + "=" * 70)
        print("[PASS] ALL PHASE 1 TESTS PASSED")
        print("=" * 70)
        print("\nPhase 1 systems are working correctly!")
        print("Ready to proceed to Phase 2: Hub System")

    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"[FAIL] TEST FAILED: {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"[ERROR] {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        sys.exit(1)
