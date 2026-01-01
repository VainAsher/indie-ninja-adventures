"""
Inventory & Item System - Equipment, Consumables, and Trading

This module provides inventory management for entities with:
- Item types (weapons, armor, consumables, key items, quest items)
- Item rarity system (common to legendary)
- Equipment slots with stat bonuses
- Stackable items
- Currency management
- Deterministic behavior for replays

Version: v0.6.0
"""

from dataclasses import dataclass
from enum import Enum

# ============================================================
# Inventory Bounds Constants
# ============================================================

MAX_CURRENCY = 999999  # Maximum currency to prevent overflow
MAX_QUANTITY_PER_OPERATION = 9999  # Maximum items per single operation


class ItemType(Enum):
    """Item category classification"""

    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    KEY_ITEM = "key_item"
    QUEST_ITEM = "quest_item"
    MATERIAL = "material"
    CURRENCY = "currency"


class ItemRarity(Enum):
    """Item rarity for loot tables and value scaling"""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class ItemDefinition:
    """
    Static item definition loaded from items.json database.

    Defines all properties of an item type including stats,
    effects, and metadata.
    """

    item_id: str
    item_type: ItemType
    rarity: ItemRarity
    display_name: str
    description: str
    max_stack: int = 1
    value: int = 0  # Gold/coin value for buying/selling
    consumable: bool = False

    # Equipment stats (if applicable)
    attack_bonus: int = 0
    defense_bonus: int = 0
    speed_bonus: float = 0.0
    health_bonus: int = 0

    # Consumable effects (if applicable)
    health_restore: int = 0
    temporary_buff: str | None = None
    buff_duration: float = 0.0


@dataclass
class InventorySlot:
    """
    Single inventory slot containing an item stack.

    Tracks item ID, quantity, and equipped status.
    """

    item_id: str
    quantity: int
    equipped: bool = False


class Inventory:
    """
    Inventory management system with equipment slots.

    Features:
    - 20 inventory slots (default)
    - Automatic item stacking
    - Equipment slots (weapon, armor)
    - Currency tracking
    - Stat bonus calculation from equipped items
    """

    def __init__(self, max_slots: int = 20):
        self.slots: list[InventorySlot | None] = [None] * max_slots
        self.currency: int = 0  # Gold/coins
        self.equipped_weapon: str | None = None
        self.equipped_armor: str | None = None

        # Item database reference (will be set by ItemDatabase)
        self.item_db: ItemDatabase | None = None

    def set_item_database(self, item_db: "ItemDatabase"):
        """Set reference to item database for stat lookups"""
        self.item_db = item_db

    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        """
        Add item to inventory.

        Args:
            item_id: Item identifier
            quantity: Number of items to add

        Returns:
            True if items added successfully, False if inventory full
        """
        # Bounds checking: prevent negative or excessive quantities
        if quantity <= 0:
            return False
        if quantity > MAX_QUANTITY_PER_OPERATION:
            return False

        if self.item_db is None:
            return False

        item_def = self.item_db.get_item(item_id)
        if item_def is None:
            return False

        # Try to stack with existing items
        if item_def.max_stack > 1:
            for slot in self.slots:
                if slot is not None and slot.item_id == item_id:
                    space_available = item_def.max_stack - slot.quantity
                    if space_available > 0:
                        add_amount = min(quantity, space_available)
                        slot.quantity += add_amount
                        quantity -= add_amount

                        if quantity <= 0:
                            return True

        # Add to empty slots
        while quantity > 0:
            empty_slot = self._find_empty_slot()
            if empty_slot is None:
                return False  # Inventory full

            stack_size = min(quantity, item_def.max_stack)
            self.slots[empty_slot] = InventorySlot(
                item_id=item_id, quantity=stack_size, equipped=False
            )
            quantity -= stack_size

        return True

    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """
        Remove item from inventory.

        Args:
            item_id: Item identifier
            quantity: Number of items to remove

        Returns:
            True if items removed successfully, False if not enough items
        """
        # Bounds checking: prevent negative or excessive quantities
        if quantity <= 0:
            return False
        if quantity > MAX_QUANTITY_PER_OPERATION:
            return False

        # Check if we have enough items
        if not self.has_item(item_id, quantity):
            return False

        remaining = quantity

        for i, slot in enumerate(self.slots):
            if slot is not None and slot.item_id == item_id:
                if slot.quantity >= remaining:
                    slot.quantity -= remaining
                    if slot.quantity == 0:
                        # Unequip if equipped
                        if slot.equipped:
                            self._unequip_slot(i)
                        self.slots[i] = None
                    return True
                else:
                    remaining -= slot.quantity
                    if slot.equipped:
                        self._unequip_slot(i)
                    self.slots[i] = None

        return False

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """
        Check if inventory contains item.

        Args:
            item_id: Item identifier
            quantity: Required quantity

        Returns:
            True if inventory has at least quantity of item
        """
        total = 0
        for slot in self.slots:
            if slot is not None and slot.item_id == item_id:
                total += slot.quantity
                if total >= quantity:
                    return True
        return False

    def get_item_count(self, item_id: str) -> int:
        """Get total quantity of item in inventory"""
        total = 0
        for slot in self.slots:
            if slot is not None and slot.item_id == item_id:
                total += slot.quantity
        return total

    def equip_item(self, item_id: str) -> bool:
        """
        Equip weapon or armor item.

        Args:
            item_id: Item to equip

        Returns:
            True if equipped successfully
        """
        if self.item_db is None:
            return False

        item_def = self.item_db.get_item(item_id)
        if item_def is None:
            return False

        # Find item in inventory
        for i, slot in enumerate(self.slots):
            if slot is not None and slot.item_id == item_id:
                if item_def.item_type == ItemType.WEAPON:
                    # Unequip current weapon
                    if self.equipped_weapon is not None:
                        self._unequip_weapon()
                    self.equipped_weapon = item_id
                    slot.equipped = True
                    return True

                elif item_def.item_type == ItemType.ARMOR:
                    # Unequip current armor
                    if self.equipped_armor is not None:
                        self._unequip_armor()
                    self.equipped_armor = item_id
                    slot.equipped = True
                    return True

        return False

    def unequip_item(self, item_id: str) -> bool:
        """
        Unequip weapon or armor item.

        Args:
            item_id: Item to unequip

        Returns:
            True if unequipped successfully
        """
        if item_id == self.equipped_weapon:
            self._unequip_weapon()
            return True
        elif item_id == self.equipped_armor:
            self._unequip_armor()
            return True
        return False

    def use_consumable(self, item_id: str) -> bool:
        """
        Use a consumable item (removes 1 from inventory).

        Args:
            item_id: Consumable item to use

        Returns:
            True if consumed successfully
        """
        if self.item_db is None:
            return False

        item_def = self.item_db.get_item(item_id)
        if item_def is None or not item_def.consumable:
            return False

        return self.remove_item(item_id, 1)

    def get_total_stats(self) -> dict[str, float]:
        """
        Calculate total stat bonuses from equipped items.

        Returns:
            Dictionary with stat totals (attack, defense, speed, max_health)
        """
        stats = {"attack": 0.0, "defense": 0.0, "speed": 0.0, "max_health": 0}

        if self.item_db is None:
            return stats

        # Add weapon stats
        if self.equipped_weapon is not None:
            weapon = self.item_db.get_item(self.equipped_weapon)
            if weapon:
                stats["attack"] += weapon.attack_bonus
                stats["defense"] += weapon.defense_bonus
                stats["speed"] += weapon.speed_bonus
                stats["max_health"] += weapon.health_bonus

        # Add armor stats
        if self.equipped_armor is not None:
            armor = self.item_db.get_item(self.equipped_armor)
            if armor:
                stats["attack"] += armor.attack_bonus
                stats["defense"] += armor.defense_bonus
                stats["speed"] += armor.speed_bonus
                stats["max_health"] += armor.health_bonus

        return stats

    def add_currency(self, amount: int):
        """Add currency to inventory (with bounds checking)"""
        # Bounds checking: prevent negative amounts and overflow
        if amount < 0:
            return  # Reject negative amounts

        # Clamp to maximum currency to prevent integer overflow exploits
        self.currency = min(MAX_CURRENCY, max(0, self.currency + amount))

    def remove_currency(self, amount: int) -> bool:
        """
        Remove currency from inventory.

        Returns:
            True if had enough currency
        """
        # Bounds checking: prevent negative amounts
        if amount < 0:
            return False

        if self.currency >= amount:
            self.currency -= amount
            return True
        return False

    def to_dict(self) -> dict:
        """Serialize inventory to dictionary"""
        return {
            "slots": [
                (
                    {"item_id": slot.item_id, "quantity": slot.quantity, "equipped": slot.equipped}
                    if slot is not None
                    else None
                )
                for slot in self.slots
            ],
            "currency": self.currency,
            "equipped_weapon": self.equipped_weapon,
            "equipped_armor": self.equipped_armor,
        }

    @classmethod
    def from_dict(cls, data: dict, max_slots: int = 20) -> "Inventory":
        """Deserialize inventory from dictionary"""
        inventory = cls(max_slots)
        inventory.currency = data.get("currency", 0)
        inventory.equipped_weapon = data.get("equipped_weapon")
        inventory.equipped_armor = data.get("equipped_armor")

        slots_data = data.get("slots", [])
        for i, slot_data in enumerate(slots_data):
            if i >= max_slots:
                break
            if slot_data is not None:
                inventory.slots[i] = InventorySlot(
                    item_id=slot_data["item_id"],
                    quantity=slot_data["quantity"],
                    equipped=slot_data.get("equipped", False),
                )

        return inventory

    # Private helper methods

    def _find_empty_slot(self) -> int | None:
        """Find first empty inventory slot"""
        for i, slot in enumerate(self.slots):
            if slot is None:
                return i
        return None

    def _unequip_weapon(self):
        """Unequip current weapon"""
        if self.equipped_weapon is not None:
            for slot in self.slots:
                if slot is not None and slot.item_id == self.equipped_weapon:
                    slot.equipped = False
            self.equipped_weapon = None

    def _unequip_armor(self):
        """Unequip current armor"""
        if self.equipped_armor is not None:
            for slot in self.slots:
                if slot is not None and slot.item_id == self.equipped_armor:
                    slot.equipped = False
            self.equipped_armor = None

    def _unequip_slot(self, slot_index: int):
        """Unequip item at slot index"""
        slot = self.slots[slot_index]
        if slot is not None and slot.equipped:
            if slot.item_id == self.equipped_weapon:
                self.equipped_weapon = None
            elif slot.item_id == self.equipped_armor:
                self.equipped_armor = None
            slot.equipped = False


class ItemDatabase:
    """
    Item definition database loaded from items.json.

    Provides lookup for item definitions by ID.
    """

    def __init__(self):
        self.items: dict[str, ItemDefinition] = {}

    def register_item(self, item_def: ItemDefinition):
        """Register item definition"""
        self.items[item_def.item_id] = item_def

    def get_item(self, item_id: str) -> ItemDefinition | None:
        """Get item definition by ID"""
        return self.items.get(item_id)

    def get_items_by_type(self, item_type: ItemType) -> list[ItemDefinition]:
        """Get all items of a specific type"""
        return [item for item in self.items.values() if item.item_type == item_type]

    def get_items_by_rarity(self, rarity: ItemRarity) -> list[ItemDefinition]:
        """Get all items of a specific rarity"""
        return [item for item in self.items.values() if item.rarity == rarity]

    def load_from_dict(self, data: dict):
        """Load item database from dictionary (from JSON)"""
        for item_data in data.get("items", []):
            item_def = ItemDefinition(
                item_id=item_data["item_id"],
                item_type=ItemType(item_data["item_type"]),
                rarity=ItemRarity(item_data["rarity"]),
                display_name=item_data["display_name"],
                description=item_data["description"],
                max_stack=item_data.get("max_stack", 1),
                value=item_data.get("value", 0),
                consumable=item_data.get("consumable", False),
                attack_bonus=item_data.get("attack_bonus", 0),
                defense_bonus=item_data.get("defense_bonus", 0),
                speed_bonus=item_data.get("speed_bonus", 0.0),
                health_bonus=item_data.get("health_bonus", 0),
                health_restore=item_data.get("health_restore", 0),
                temporary_buff=item_data.get("temporary_buff"),
                buff_duration=item_data.get("buff_duration", 0.0),
            )
            self.register_item(item_def)


# ============================================================
# Global Item Manager Instance
# ============================================================

_item_manager: ItemDatabase | None = None


def initialize_item_manager():
    """Initialize the global item manager"""
    global _item_manager
    _item_manager = ItemDatabase()


def get_item_manager() -> ItemDatabase | None:
    """Get the global item manager instance"""
    return _item_manager
