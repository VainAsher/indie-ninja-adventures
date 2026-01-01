"""
Loot & Drop System - Deterministic Item Generation

This module provides loot table management and deterministic drop generation:
- Loot table definitions for enemies, chests, bosses
- Probability-based drop calculations
- Currency (gold/coins) drops
- Guaranteed and chance-based drops
- Deterministic generation using seeded RNG
- Support for replay consistency

Version: v0.6.0
"""

import random
from dataclasses import dataclass, field


@dataclass
class LootDrop:
    """
    Single item drop definition with quantity range and drop chance.

    Used in loot tables to define what items can drop and their probabilities.
    """

    item_id: str
    quantity_range: tuple[int, int]  # (min, max) quantity
    drop_chance: float  # 0.0-1.0 probability

    def __post_init__(self):
        """Validate drop configuration"""
        if self.drop_chance < 0.0 or self.drop_chance > 1.0:
            raise ValueError(f"drop_chance must be 0.0-1.0, got {self.drop_chance}")
        if self.quantity_range[0] < 0 or self.quantity_range[1] < self.quantity_range[0]:
            raise ValueError(f"Invalid quantity_range: {self.quantity_range}")


@dataclass
class LootTable:
    """
    Loot table defining what items drop from a source.

    Contains:
    - Guaranteed drops (always drop)
    - Chance drops (probability-based)
    - Currency range (gold/coins)
    """

    table_id: str
    guaranteed_drops: list[LootDrop] = field(default_factory=list)
    chance_drops: list[LootDrop] = field(default_factory=list)
    currency_range: tuple[int, int] = (0, 0)  # (min, max) gold/coins

    def add_guaranteed_drop(self, item_id: str, quantity_range: tuple[int, int]):
        """Add guaranteed drop to table"""
        self.guaranteed_drops.append(
            LootDrop(item_id=item_id, quantity_range=quantity_range, drop_chance=1.0)
        )

    def add_chance_drop(self, item_id: str, quantity_range: tuple[int, int], drop_chance: float):
        """Add chance-based drop to table"""
        self.chance_drops.append(
            LootDrop(item_id=item_id, quantity_range=quantity_range, drop_chance=drop_chance)
        )


class LootGenerator:
    """
    Deterministic loot generation engine.

    Generates loot from loot tables using seeded RNG for replay consistency.
    """

    def __init__(self, seed: int):
        """
        Initialize loot generator with seed.

        Args:
            seed: Seed for deterministic RNG
        """
        self.rng = random.Random(seed)

    def generate_loot(self, loot_table: LootTable) -> tuple[list[tuple[str, int]], int]:
        """
        Generate loot from loot table.

        Args:
            loot_table: LootTable to generate from

        Returns:
            Tuple of (items, currency) where:
            - items: List of (item_id, quantity) tuples
            - currency: Amount of gold/coins dropped
        """
        items = []

        # Process guaranteed drops
        for drop in loot_table.guaranteed_drops:
            quantity = self.rng.randint(drop.quantity_range[0], drop.quantity_range[1])
            if quantity > 0:
                items.append((drop.item_id, quantity))

        # Process chance drops
        for drop in loot_table.chance_drops:
            if self.rng.random() <= drop.drop_chance:
                quantity = self.rng.randint(drop.quantity_range[0], drop.quantity_range[1])
                if quantity > 0:
                    items.append((drop.item_id, quantity))

        # Generate currency
        currency = 0
        if loot_table.currency_range[1] > 0:
            currency = self.rng.randint(loot_table.currency_range[0], loot_table.currency_range[1])

        return items, currency

    def generate_loot_by_id(
        self, loot_table_id: str, loot_tables: "LootTableDatabase"
    ) -> tuple[list[tuple[str, int]], int]:
        """
        Generate loot from loot table by ID.

        Args:
            loot_table_id: ID of loot table
            loot_tables: LootTableDatabase instance

        Returns:
            Tuple of (items, currency)
        """
        table = loot_tables.get_table(loot_table_id)
        if table is None:
            return [], 0

        return self.generate_loot(table)


class LootTableDatabase:
    """
    Database of loot tables.

    Manages loot table definitions for enemies, chests, bosses, and missions.
    """

    def __init__(self):
        self.tables: dict[str, LootTable] = {}
        self._register_default_tables()

    def register_table(self, loot_table: LootTable):
        """Register loot table"""
        self.tables[loot_table.table_id] = loot_table

    def get_table(self, table_id: str) -> LootTable | None:
        """Get loot table by ID"""
        return self.tables.get(table_id)

    def _register_default_tables(self):
        """Register default loot tables for v0.6.0"""

        # ============================================================
        # Enemy Loot Tables
        # ============================================================

        # Common enemies (goblins, slimes)
        common_enemy = LootTable(
            table_id="enemy_common",
            guaranteed_drops=[],
            chance_drops=[
                LootDrop("health_potion_small", (1, 1), 0.15),  # 15% chance
                LootDrop("material_cloth", (1, 2), 0.25),  # 25% chance
            ],
            currency_range=(1, 5),
        )
        self.register_table(common_enemy)

        # Uncommon enemies (bats, wolves)
        uncommon_enemy = LootTable(
            table_id="enemy_uncommon",
            guaranteed_drops=[],
            chance_drops=[
                LootDrop("health_potion_small", (1, 2), 0.20),
                LootDrop("health_potion_medium", (1, 1), 0.10),
                LootDrop("material_leather", (1, 2), 0.30),
                LootDrop("weapon_dagger", (1, 1), 0.05),  # 5% weapon drop
            ],
            currency_range=(3, 10),
        )
        self.register_table(uncommon_enemy)

        # Rare enemies (elite variants)
        rare_enemy = LootTable(
            table_id="enemy_rare",
            guaranteed_drops=[
                LootDrop("health_potion_medium", (1, 2), 1.0),
            ],
            chance_drops=[
                LootDrop("health_potion_large", (1, 1), 0.15),
                LootDrop("material_iron", (1, 3), 0.40),
                LootDrop("weapon_sword", (1, 1), 0.10),
                LootDrop("armor_leather", (1, 1), 0.10),
            ],
            currency_range=(10, 25),
        )
        self.register_table(rare_enemy)

        # ============================================================
        # Boss Loot Tables
        # ============================================================

        # Forest Guardian (Boss 1)
        forest_boss = LootTable(
            table_id="boss_forest_guardian",
            guaranteed_drops=[
                LootDrop("health_potion_large", (2, 3), 1.0),
                LootDrop("key_item_forest_heart", (1, 1), 1.0),
                LootDrop("weapon_nature_bow", (1, 1), 1.0),
            ],
            chance_drops=[
                LootDrop("armor_bark_plate", (1, 1), 0.50),
                LootDrop("max_hp_upgrade", (1, 1), 0.25),
            ],
            currency_range=(50, 100),
        )
        self.register_table(forest_boss)

        # Corrupt Mayor (Boss 2)
        town_boss = LootTable(
            table_id="boss_corrupt_mayor",
            guaranteed_drops=[
                LootDrop("health_potion_large", (2, 3), 1.0),
                LootDrop("key_item_town_seal", (1, 1), 1.0),
                LootDrop("weapon_steel_sword", (1, 1), 1.0),
            ],
            chance_drops=[
                LootDrop("armor_chain_mail", (1, 1), 0.50),
                LootDrop("max_hp_upgrade", (1, 1), 0.25),
            ],
            currency_range=(75, 150),
        )
        self.register_table(town_boss)

        # Crystal Golem (Boss 3)
        caves_boss = LootTable(
            table_id="boss_crystal_golem",
            guaranteed_drops=[
                LootDrop("health_potion_large", (3, 4), 1.0),
                LootDrop("key_item_crystal_core", (1, 1), 1.0),
                LootDrop("armor_crystal_plate", (1, 1), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_crystal_blade", (1, 1), 0.50),
                LootDrop("max_hp_upgrade", (1, 1), 0.30),
            ],
            currency_range=(100, 200),
        )
        self.register_table(caves_boss)

        # Dark Knight (Boss 4)
        castle_boss = LootTable(
            table_id="boss_dark_knight",
            guaranteed_drops=[
                LootDrop("health_potion_large", (3, 5), 1.0),
                LootDrop("key_item_dark_key", (1, 1), 1.0),
                LootDrop("weapon_dark_blade", (1, 1), 1.0),
            ],
            chance_drops=[
                LootDrop("armor_dark_plate", (1, 1), 0.50),
                LootDrop("max_hp_upgrade", (1, 1), 0.35),
            ],
            currency_range=(150, 250),
        )
        self.register_table(castle_boss)

        # Plague Rat (Boss 5)
        sewer_boss = LootTable(
            table_id="boss_plague_rat",
            guaranteed_drops=[
                LootDrop("health_potion_large", (4, 5), 1.0),
                LootDrop("key_item_plague_cure", (1, 1), 1.0),
                LootDrop("armor_legendary_set", (1, 1), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_legendary_sword", (1, 1), 0.75),
                LootDrop("max_hp_upgrade", (2, 2), 0.50),
            ],
            currency_range=(200, 500),
        )
        self.register_table(sewer_boss)

        # ============================================================
        # Chest Loot Tables
        # ============================================================

        # Common chest
        common_chest = LootTable(
            table_id="chest_common",
            guaranteed_drops=[],
            chance_drops=[
                LootDrop("health_potion_small", (1, 3), 0.60),
                LootDrop("material_cloth", (2, 5), 0.50),
                LootDrop("weapon_dagger", (1, 1), 0.15),
            ],
            currency_range=(5, 20),
        )
        self.register_table(common_chest)

        # Rare chest
        rare_chest = LootTable(
            table_id="chest_rare",
            guaranteed_drops=[
                LootDrop("health_potion_medium", (1, 2), 1.0),
            ],
            chance_drops=[
                LootDrop("health_potion_large", (1, 1), 0.30),
                LootDrop("weapon_sword", (1, 1), 0.40),
                LootDrop("armor_leather", (1, 1), 0.40),
                LootDrop("max_hp_upgrade", (1, 1), 0.10),
            ],
            currency_range=(25, 75),
        )
        self.register_table(rare_chest)

        # Epic chest
        epic_chest = LootTable(
            table_id="chest_epic",
            guaranteed_drops=[
                LootDrop("health_potion_large", (2, 3), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_legendary_sword", (1, 1), 0.20),
                LootDrop("armor_legendary_set", (1, 1), 0.20),
                LootDrop("max_hp_upgrade", (1, 2), 0.50),
            ],
            currency_range=(100, 300),
        )
        self.register_table(epic_chest)

        # ============================================================
        # Mission Reward Tables
        # ============================================================

        # Forest region missions
        mission_forest = LootTable(
            table_id="mission_reward_forest",
            guaranteed_drops=[
                LootDrop("health_potion_medium", (2, 3), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_dagger", (1, 1), 0.30),
                LootDrop("armor_cloth", (1, 1), 0.30),
            ],
            currency_range=(20, 50),
        )
        self.register_table(mission_forest)

        # Town region missions
        mission_town = LootTable(
            table_id="mission_reward_town",
            guaranteed_drops=[
                LootDrop("health_potion_medium", (2, 4), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_sword", (1, 1), 0.40),
                LootDrop("armor_leather", (1, 1), 0.40),
            ],
            currency_range=(40, 100),
        )
        self.register_table(mission_town)

        # Caves region missions
        mission_caves = LootTable(
            table_id="mission_reward_caves",
            guaranteed_drops=[
                LootDrop("health_potion_large", (2, 3), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_crystal_blade", (1, 1), 0.30),
                LootDrop("armor_crystal_plate", (1, 1), 0.30),
                LootDrop("max_hp_upgrade", (1, 1), 0.15),
            ],
            currency_range=(75, 150),
        )
        self.register_table(mission_caves)

        # Castle region missions
        mission_castle = LootTable(
            table_id="mission_reward_castle",
            guaranteed_drops=[
                LootDrop("health_potion_large", (3, 4), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_dark_blade", (1, 1), 0.35),
                LootDrop("armor_dark_plate", (1, 1), 0.35),
                LootDrop("max_hp_upgrade", (1, 1), 0.20),
            ],
            currency_range=(100, 200),
        )
        self.register_table(mission_castle)

        # Sewer region missions
        mission_sewer = LootTable(
            table_id="mission_reward_sewer",
            guaranteed_drops=[
                LootDrop("health_potion_large", (4, 5), 1.0),
                LootDrop("max_hp_upgrade", (1, 1), 1.0),
            ],
            chance_drops=[
                LootDrop("weapon_legendary_sword", (1, 1), 0.50),
                LootDrop("armor_legendary_set", (1, 1), 0.50),
            ],
            currency_range=(150, 300),
        )
        self.register_table(mission_sewer)

    def load_from_dict(self, data: dict):
        """Load loot tables from dictionary (from JSON)"""
        for table_data in data.get("loot_tables", []):
            table = LootTable(
                table_id=table_data["table_id"],
                currency_range=tuple(table_data.get("currency_range", [0, 0])),
            )

            # Load guaranteed drops
            for drop_data in table_data.get("guaranteed_drops", []):
                table.guaranteed_drops.append(
                    LootDrop(
                        item_id=drop_data["item_id"],
                        quantity_range=tuple(drop_data["quantity_range"]),
                        drop_chance=1.0,
                    )
                )

            # Load chance drops
            for drop_data in table_data.get("chance_drops", []):
                table.chance_drops.append(
                    LootDrop(
                        item_id=drop_data["item_id"],
                        quantity_range=tuple(drop_data["quantity_range"]),
                        drop_chance=drop_data["drop_chance"],
                    )
                )

            self.register_table(table)


# ============================================================
# Global Loot Table Database Instance
# ============================================================

_loot_table_database: LootTableDatabase | None = None


def initialize_loot_table_database():
    """Initialize the global loot table database"""
    global _loot_table_database
    _loot_table_database = LootTableDatabase()


def get_loot_table_database() -> LootTableDatabase | None:
    """Get the global loot table database instance"""
    return _loot_table_database
