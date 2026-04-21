# Loot & Drop System

**Indie Ninja Adventures** | v0.7.1 | 2026-03-28

---

## Rationale

Item drops use a deterministic seeded RNG so that the same world seed produces the same drops in the same run. This is required for replay consistency (the replay system replays inputs, not outcomes — so outcomes must be deterministic). It also supports future multiplayer where both peers must agree on drop results.

---

## Architecture

**File**: `game/loot_system.py`

```
LootDrop          item_id + quantity_range + drop_chance (0.0–1.0)
LootTable         table_id, guaranteed_drops[], chance_drops[], currency_range
LootGenerator     seeded random.Random; generate_loot(table) → (items, currency)
LootTableDatabase registry; _register_default_tables() at init
```

---

## Drop generation

`LootGenerator.generate_loot(table)` processes in order:

1. **Guaranteed drops** (`drop_chance = 1.0`): always roll a quantity from `quantity_range`; add if > 0
2. **Chance drops**: roll `rng.random() <= drop_chance`; if hit, roll quantity
3. **Currency**: roll `rng.randint(min, max)` from `currency_range` if max > 0

Returns `(list[(item_id, quantity)], currency_int)`.

The `LootGenerator` is initialized with the world seed so the entire session's drops are reproducible.

---

## Enemy loot tiers

| Table ID | Enemy type | Currency | Notable drops |
| --- | --- | --- | --- |
| `enemy_common` | Goblin, slime | 1–5 | 15% small health potion, 25% cloth |
| `enemy_uncommon` | Bat, wolf | 3–10 | 20% small HP, 10% medium HP, 5% dagger |
| `enemy_rare` | Elite variants | 10–25 | Guaranteed medium HP, 10% sword/armor |

---

## Boss loot tables

All boss kills are **guaranteed drops** for key items and weapons, plus currency:

| Table ID | Boss | Currency | Guaranteed | Chance |
| --- | --- | --- | --- | --- |
| `boss_forest_guardian` | Forest boss | 50–100 | Large HP ×2-3, `key_item_forest_heart`, `weapon_nature_bow` | 50% bark plate, 25% max HP upgrade |
| `boss_corrupt_mayor` | Town boss | 75–150 | Large HP ×2-3, `key_item_town_seal`, `weapon_steel_sword` | 50% chain mail, 25% max HP upgrade |
| `boss_crystal_golem` | Caves boss | 100–200 | Large HP ×3-4, `key_item_crystal_core`, `armor_crystal_plate` | 50% crystal blade, 30% max HP upgrade |
| `boss_dark_knight` | Castle boss | 100+ | Large HP ×3-5, `key_item_dark_key`, `weapon_dark_blade` | 50% dark plate, 35% max HP upgrade |

---

## Adding a loot table

```python
# In LootTableDatabase._register_default_tables() or at runtime:
table = LootTable(table_id="enemy_custom")
table.add_guaranteed_drop("health_potion_small", (1, 1))
table.add_chance_drop("weapon_katana", (1, 1), 0.10)   # 10% chance
table.currency_range = (5, 20)
db.register_table(table)
```

Then call:
```python
items, currency = loot_generator.generate_loot_by_id("enemy_custom", loot_table_db)
```

---

## Integration with PickupManager

The `PickupManager` (`entities/pickup_spawner.py`) consumes loot results to spawn `PickupComponent` entities in the world. Enemy death events trigger loot generation and pickup spawning at the enemy's last position.

---

## Current status

`LootSystem` is implemented and functional. The default tables cover common/uncommon/rare enemies and all four currently-implemented bosses. Table IDs for the remaining two boss regions (sewer, hollow_depths) are not yet registered. The rarity tier naming (`common`, `uncommon`, `rare`) is internal — there is no visible rarity label in the UI.
