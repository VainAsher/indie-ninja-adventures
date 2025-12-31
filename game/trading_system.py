"""
Trading & Shop System - NPC Commerce for Campaign Mode

This module provides NPC trading and shop functionality:
- Tiered shop inventories (1-5 tiers)
- Deterministic shop generation per NPC
- Buy/sell transactions with pricing
- Currency exchange
- Shop inventory refresh mechanics

Version: v0.6.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random

from game.inventory_system import (
    Inventory, ItemDefinition, ItemType, ItemRarity,
    get_item_manager
)
from core import EventBus


# ============================================================
# Shop Configuration
# ============================================================

class ShopTier(Enum):
    """Shop tier levels (higher = better items)"""
    TIER_1 = 1  # Forest hub - basic items
    TIER_2 = 2  # Town hub - uncommon items
    TIER_3 = 3  # Caves hub - rare items
    TIER_4 = 4  # Castle hub - epic items
    TIER_5 = 5  # Sewer hub - legendary items


@dataclass
class ShopItemPool:
    """
    Configuration for shop item pools by tier.

    Defines which items can appear in shops of each tier.
    """
    tier: ShopTier
    allowed_item_ids: List[str]
    allowed_rarities: List[ItemRarity]
    min_items: int = 5
    max_items: int = 10
    stock_range: Tuple[int, int] = (1, 3)  # Stock quantity per item


# ============================================================
# Shop Tier Definitions
# ============================================================

SHOP_TIER_POOLS = {
    ShopTier.TIER_1: ShopItemPool(
        tier=ShopTier.TIER_1,
        allowed_item_ids=[
            # Basic weapons
            "weapon_dagger",
            "weapon_sword",

            # Basic armor
            "armor_cloth",
            "armor_leather",

            # Consumables
            "health_potion_small",
            "health_potion_medium",
            "speed_boost_potion",

            # Materials
            "material_cloth",
            "material_leather",
            "material_iron"
        ],
        allowed_rarities=[ItemRarity.COMMON, ItemRarity.UNCOMMON],
        min_items=6,
        max_items=10,
        stock_range=(2, 5)
    ),

    ShopTier.TIER_2: ShopItemPool(
        tier=ShopTier.TIER_2,
        allowed_item_ids=[
            # Better weapons
            "weapon_sword",
            "weapon_steel_sword",

            # Better armor
            "armor_leather",
            "armor_chain_mail",

            # Consumables
            "health_potion_medium",
            "health_potion_large",
            "speed_boost_potion",
            "invincibility_potion",

            # Materials
            "material_iron",
            "material_crystal"
        ],
        allowed_rarities=[ItemRarity.COMMON, ItemRarity.UNCOMMON, ItemRarity.RARE],
        min_items=7,
        max_items=12,
        stock_range=(1, 4)
    ),

    ShopTier.TIER_3: ShopItemPool(
        tier=ShopTier.TIER_3,
        allowed_item_ids=[
            # Advanced weapons
            "weapon_steel_sword",
            "weapon_nature_bow",
            "weapon_crystal_blade",

            # Advanced armor
            "armor_chain_mail",
            "armor_bark_plate",
            "armor_crystal_plate",

            # Rare consumables
            "health_potion_large",
            "max_hp_upgrade",
            "invincibility_potion",

            # Rare materials
            "material_crystal",
            "material_dark_essence",
            "quest_ancient_scroll"
        ],
        allowed_rarities=[ItemRarity.UNCOMMON, ItemRarity.RARE, ItemRarity.EPIC],
        min_items=8,
        max_items=14,
        stock_range=(1, 3)
    ),

    ShopTier.TIER_4: ShopItemPool(
        tier=ShopTier.TIER_4,
        allowed_item_ids=[
            # Epic weapons
            "weapon_crystal_blade",
            "weapon_dark_blade",

            # Epic armor
            "armor_crystal_plate",
            "armor_dark_plate",

            # Epic consumables
            "max_hp_upgrade",
            "invincibility_potion",

            # Epic materials
            "material_crystal",
            "material_dark_essence",
            "quest_ancient_scroll",
            "treasure_ruby"
        ],
        allowed_rarities=[ItemRarity.RARE, ItemRarity.EPIC],
        min_items=6,
        max_items=10,
        stock_range=(1, 2)
    ),

    ShopTier.TIER_5: ShopItemPool(
        tier=ShopTier.TIER_5,
        allowed_item_ids=[
            # Legendary weapons
            "weapon_dark_blade",
            "weapon_legendary_sword",

            # Legendary armor
            "armor_dark_plate",
            "armor_legendary_set",

            # Endgame consumables
            "max_hp_upgrade",
            "poison_resist_charm",

            # Legendary materials
            "material_dark_essence",
            "treasure_diamond",
            "ultimate_weapon",
            "ultimate_armor"
        ],
        allowed_rarities=[ItemRarity.EPIC, ItemRarity.LEGENDARY],
        min_items=5,
        max_items=8,
        stock_range=(1, 2)
    )
}


# ============================================================
# Pricing Configuration
# ============================================================

# Base price multipliers by rarity
RARITY_PRICE_MULTIPLIERS = {
    ItemRarity.COMMON: 1.0,
    ItemRarity.UNCOMMON: 2.0,
    ItemRarity.RARE: 4.0,
    ItemRarity.EPIC: 8.0,
    ItemRarity.LEGENDARY: 16.0
}

# Sell value percentage (player sells to NPC)
SELL_VALUE_PERCENT = 0.5  # 50% of item value

# Buy price percentage (player buys from NPC)
BUY_PRICE_PERCENT = 1.0  # 100% of item value


# ============================================================
# Shop Inventory
# ============================================================

@dataclass
class ShopItem:
    """Item in a shop with stock and pricing"""
    item_id: str
    stock: int
    price: int  # Buy price (what player pays)


@dataclass
class NPCInventory:
    """
    Shop inventory for an NPC.

    Manages shop items, stock levels, and transactions.
    """
    npc_id: str
    shop_tier: ShopTier
    items: List[ShopItem] = field(default_factory=list)
    currency: int = 10000  # NPC has plenty of money

    # Generation seed for deterministic inventory
    generation_seed: int = 0

    def generate_inventory(self):
        """
        Generate shop inventory based on tier.

        Uses generation_seed for deterministic results.
        """
        # Get tier configuration
        pool_config = SHOP_TIER_POOLS.get(self.shop_tier)
        if pool_config is None:
            print(f"[WARNING] Unknown shop tier: {self.shop_tier}")
            return

        # Seed RNG for deterministic generation
        rng = random.Random(self.generation_seed)

        # Determine number of items
        num_items = rng.randint(pool_config.min_items, pool_config.max_items)

        # Select random items from pool
        item_manager = get_item_manager()
        available_items = []

        for item_id in pool_config.allowed_item_ids:
            item_def = item_manager.get_item(item_id)
            if item_def and item_def.rarity in pool_config.allowed_rarities:
                available_items.append(item_def)

        # Randomly select items (no duplicates)
        if len(available_items) < num_items:
            num_items = len(available_items)

        selected_items = rng.sample(available_items, num_items)

        # Create shop items with stock and pricing
        self.items.clear()
        for item_def in selected_items:
            stock = rng.randint(pool_config.stock_range[0], pool_config.stock_range[1])
            price = self.calculate_buy_price(item_def)

            self.items.append(ShopItem(
                item_id=item_def.item_id,
                stock=stock,
                price=price
            ))

    def calculate_buy_price(self, item_def: ItemDefinition) -> int:
        """
        Calculate price for player to buy item from shop.

        Args:
            item_def: Item definition

        Returns:
            Price in currency
        """
        base_value = item_def.value
        rarity_multiplier = RARITY_PRICE_MULTIPLIERS.get(item_def.rarity, 1.0)
        return int(base_value * rarity_multiplier * BUY_PRICE_PERCENT)

    def calculate_sell_price(self, item_def: ItemDefinition) -> int:
        """
        Calculate price for player to sell item to shop.

        Args:
            item_def: Item definition

        Returns:
            Price in currency (50% of buy price)
        """
        buy_price = self.calculate_buy_price(item_def)
        return int(buy_price * SELL_VALUE_PERCENT)

    def get_shop_item(self, item_id: str) -> Optional[ShopItem]:
        """Get shop item by ID"""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    def has_stock(self, item_id: str, quantity: int = 1) -> bool:
        """Check if shop has stock of item"""
        shop_item = self.get_shop_item(item_id)
        if shop_item is None:
            return False
        return shop_item.stock >= quantity

    def buy_from_shop(self, item_id: str, quantity: int, player_inventory: Inventory) -> bool:
        """
        Player buys item from shop.

        Args:
            item_id: Item to buy
            quantity: Quantity to buy
            player_inventory: Player's inventory

        Returns:
            True if transaction successful
        """
        # Validate shop has item
        shop_item = self.get_shop_item(item_id)
        if shop_item is None:
            return False

        # Validate stock
        if shop_item.stock < quantity:
            return False

        # Calculate total cost
        total_cost = shop_item.price * quantity

        # Validate player has currency
        if player_inventory.currency < total_cost:
            return False

        # Validate item exists
        item_manager = get_item_manager()
        item_def = item_manager.get_item(item_id)
        if item_def is None:
            return False

        # Try to add items to player inventory
        success = player_inventory.add_item(item_id, quantity)
        if not success:
            return False  # Inventory full

        # Execute transaction (deduct currency and stock)
        player_inventory.currency -= total_cost
        self.currency += total_cost
        shop_item.stock -= quantity

        return True

    def sell_to_shop(self, item_id: str, quantity: int, player_inventory: Inventory) -> bool:
        """
        Player sells item to shop.

        Args:
            item_id: Item to sell
            quantity: Quantity to sell
            player_inventory: Player's inventory

        Returns:
            True if transaction successful
        """
        # Validate player has item
        if not player_inventory.has_item(item_id, quantity):
            return False

        # Get item definition
        item_manager = get_item_manager()
        item_def = item_manager.get_item(item_id)
        if item_def is None:
            return False

        # Don't buy quest items or key items
        if item_def.item_type in (ItemType.QUEST_ITEM, ItemType.KEY_ITEM):
            return False

        # Calculate sell price
        sell_price = self.calculate_sell_price(item_def)
        total_payment = sell_price * quantity

        # Validate shop has currency
        if self.currency < total_payment:
            return False

        # Execute transaction
        player_inventory.remove_item(item_id, quantity)
        player_inventory.currency += total_payment

        self.currency -= total_payment

        # Add to shop stock (if shop already sells this item)
        shop_item = self.get_shop_item(item_id)
        if shop_item:
            shop_item.stock += quantity

        return True

    def refresh_inventory(self):
        """
        Refresh shop inventory.

        Regenerates stock levels using new seed.
        """
        # Increment seed for different inventory
        self.generation_seed += 1
        self.generate_inventory()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            'npc_id': self.npc_id,
            'shop_tier': self.shop_tier.value,
            'items': [
                {
                    'item_id': item.item_id,
                    'stock': item.stock,
                    'price': item.price
                }
                for item in self.items
            ],
            'currency': self.currency,
            'generation_seed': self.generation_seed
        }

    @staticmethod
    def from_dict(data: dict) -> 'NPCInventory':
        """Deserialize from dictionary"""
        inventory = NPCInventory(
            npc_id=data['npc_id'],
            shop_tier=ShopTier(data['shop_tier']),
            currency=data.get('currency', 10000),
            generation_seed=data.get('generation_seed', 0)
        )

        # Restore items
        for item_data in data.get('items', []):
            inventory.items.append(ShopItem(
                item_id=item_data['item_id'],
                stock=item_data['stock'],
                price=item_data['price']
            ))

        return inventory


# ============================================================
# Trading Events
# ============================================================

@dataclass
class TradeEvent:
    """Event emitted when trade occurs"""
    npc_id: str
    item_id: str
    quantity: int
    total_cost: int
    is_purchase: bool  # True = player bought, False = player sold


@dataclass
class ShopOpenEvent:
    """Event emitted when shop UI opens"""
    npc_id: str
    shop_tier: ShopTier


@dataclass
class ShopCloseEvent:
    """Event emitted when shop UI closes"""
    npc_id: str


# ============================================================
# Trading Manager
# ============================================================

class TradingManager:
    """
    Manages NPC shops and trading transactions.

    Handles shop creation, inventory generation, and transaction processing.
    """

    def __init__(self, event_bus: EventBus, world_seed: int):
        """
        Initialize trading manager.

        Args:
            event_bus: Event bus for emitting events
            world_seed: World seed for deterministic shop generation
        """
        self.event_bus = event_bus
        self.world_seed = world_seed
        self.npc_shops: Dict[str, NPCInventory] = {}

    def create_shop(self, npc_id: str, shop_tier: ShopTier) -> NPCInventory:
        """
        Create a shop for an NPC.

        Args:
            npc_id: NPC identifier
            shop_tier: Shop tier level

        Returns:
            NPCInventory instance
        """
        # Derive shop seed from world seed and NPC ID
        generation_seed = hash(f"{self.world_seed}:{npc_id}") & 0x7FFFFFFF

        # Create shop inventory
        shop = NPCInventory(
            npc_id=npc_id,
            shop_tier=shop_tier,
            generation_seed=generation_seed
        )

        # Generate initial inventory
        shop.generate_inventory()

        # Register shop
        self.npc_shops[npc_id] = shop

        return shop

    def get_shop(self, npc_id: str) -> Optional[NPCInventory]:
        """Get shop by NPC ID"""
        return self.npc_shops.get(npc_id)

    def open_shop(self, npc_id: str, shop_tier: ShopTier):
        """
        Open shop UI for an NPC.

        Creates shop if it doesn't exist, then emits open event.

        Args:
            npc_id: NPC identifier
            shop_tier: Shop tier level
        """
        # Create shop if doesn't exist
        if npc_id not in self.npc_shops:
            self.create_shop(npc_id, shop_tier)

        # Emit open event
        self.event_bus.emit(ShopOpenEvent(
            npc_id=npc_id,
            shop_tier=shop_tier
        ))

    def close_shop(self, npc_id: str):
        """
        Close shop UI.

        Args:
            npc_id: NPC identifier
        """
        self.event_bus.emit(ShopCloseEvent(npc_id=npc_id))

    def buy_item(self, npc_id: str, item_id: str, quantity: int,
                 player_inventory: Inventory) -> bool:
        """
        Process player buying item from shop.

        Args:
            npc_id: NPC shop identifier
            item_id: Item to buy
            quantity: Quantity to buy
            player_inventory: Player's inventory

        Returns:
            True if transaction successful
        """
        shop = self.get_shop(npc_id)
        if shop is None:
            return False

        # Get shop item for price
        shop_item = shop.get_shop_item(item_id)
        if shop_item is None:
            return False

        # Execute transaction
        success = shop.buy_from_shop(item_id, quantity, player_inventory)

        if success:
            # Emit trade event
            total_cost = shop_item.price * quantity
            self.event_bus.emit(TradeEvent(
                npc_id=npc_id,
                item_id=item_id,
                quantity=quantity,
                total_cost=total_cost,
                is_purchase=True
            ))

        return success

    def sell_item(self, npc_id: str, item_id: str, quantity: int,
                  player_inventory: Inventory) -> bool:
        """
        Process player selling item to shop.

        Args:
            npc_id: NPC shop identifier
            item_id: Item to sell
            quantity: Quantity to sell
            player_inventory: Player's inventory

        Returns:
            True if transaction successful
        """
        shop = self.get_shop(npc_id)
        if shop is None:
            return False

        # Get item definition for price calculation
        item_manager = get_item_manager()
        item_def = item_manager.get_item(item_id)
        if item_def is None:
            return False

        # Calculate sell price
        sell_price = shop.calculate_sell_price(item_def)
        total_payment = sell_price * quantity

        # Execute transaction
        success = shop.sell_to_shop(item_id, quantity, player_inventory)

        if success:
            # Emit trade event
            self.event_bus.emit(TradeEvent(
                npc_id=npc_id,
                item_id=item_id,
                quantity=quantity,
                total_cost=total_payment,
                is_purchase=False
            ))

        return success

    def refresh_shop(self, npc_id: str):
        """
        Refresh shop inventory.

        Args:
            npc_id: NPC shop identifier
        """
        shop = self.get_shop(npc_id)
        if shop:
            shop.refresh_inventory()

    def save_shops(self) -> dict:
        """Save all shop states"""
        return {
            npc_id: shop.to_dict()
            for npc_id, shop in self.npc_shops.items()
        }

    def load_shops(self, data: dict):
        """Load shop states"""
        self.npc_shops.clear()
        for npc_id, shop_data in data.items():
            self.npc_shops[npc_id] = NPCInventory.from_dict(shop_data)


# ============================================================
# Global Trading Manager Instance
# ============================================================

_trading_manager: Optional[TradingManager] = None


def initialize_trading_manager(event_bus: EventBus, world_seed: int):
    """Initialize the global trading manager"""
    global _trading_manager
    _trading_manager = TradingManager(event_bus, world_seed)


def get_trading_manager() -> Optional[TradingManager]:
    """Get the global trading manager instance"""
    return _trading_manager
