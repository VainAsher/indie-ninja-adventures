---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Loot, Inventory, and Economy (Java)

## Scope

Pickup drops, inventory state, item definitions, recipes, crafting/trade requests, and persistence across Java client/server.

## Primary Java owners

- Simulation/domain:
  - `java/shadowascent/src/main/java/com/indieniinja/sim/SimPickup.java`
  - `java/shadowascent/src/main/java/com/indieniinja/sim/SimInventory.java`
  - `java/shadowascent/src/main/java/com/indieniinja/sim/ItemDatabase.java`
  - `java/shadowascent/src/main/java/com/indieniinja/sim/RecipeBook.java`
- Wire state:
  - `java/core/src/main/java/com/indieniinja/network/PickupState.java`
  - `java/core/src/main/java/com/indieniinja/network/InventoryState.java`
  - `java/core/src/main/java/com/indieniinja/network/ShopState.java`
- Server endpoints/persistence:
  - `java/server/src/main/java/com/indieniinja/server/ServerProtocolHandler.java`
  - `java/server/src/main/java/com/indieniinja/server/InventoryRepository.java`
  - `java/server/src/main/java/com/indieniinja/server/InventoryDatabaseLoader.java`
  - `java/server/src/main/java/com/indieniinja/server/ItemCache.java`
- Client UI:
  - `java/client/src/main/java/com/indieniinja/client/ui/InventoryOverlay.java`
  - `java/client/src/main/java/com/indieniinja/client/ui/ShopOverlay.java`
  - `java/client/src/main/java/com/indieniinja/client/ui/CraftingOverlay.java`

## Runtime flow

1. Simulation spawns pickups and updates player inventories.
2. Server snapshots publish pickup/inventory/shop wire states.
3. Client overlays send trade/craft/use/equip requests to server.
4. Server validates and mutates authoritative inventory/economy state.
5. DB and cache layers persist/prime item and inventory data.

## Method-level call graphs

- Client request graph:
  - `CraftingOverlay.setOnCraft(...)` callback in `GameScreen` -> `networkClient.sendMessage(MessageType.CRAFT_REQUEST, payload)`
  - `ShopOverlay.setOnTrade(...)` callback in `GameScreen` -> `networkClient.sendMessage(MessageType.TRADE_REQUEST, payload)`
  - `InventoryOverlay.setOnUseItem(...)` / `setOnEquipItem(...)` callbacks in `GameScreen` -> `networkClient.sendMessage(MessageType.USE_ITEM/EQUIP_ITEM, payload)`
- Server handler graph:
  - `ServerProtocolHandler.channelRead0(...)` -> `handleTradeRequest/handleCraftRequest/handleUseItem/handleEquipItem`
  - Handler -> `zone.simulator.handleTradeRequest/handleCraftRequest/handleUseItem/handleEquipItem`
- Authoritative economy graph:
  - Trade: `GameSimulator.handleTradeRequest(...)` -> `SimShop.buy(...)` or `SimShop.sell(...)` -> `SimInventory.addItem/removeItem/addCurrency/removeCurrency`
  - Craft: `GameSimulator.handleCraftRequest(...)` -> `RecipeBook.get(recipeId)` -> `CraftingRecipe.craft(inv)`
  - Consumable/equip: `GameSimulator.handleUseItem(...)` / `handleEquipItem(...)` -> `ItemDatabase.get(itemId)` -> `SimInventory.removeItem(...)` / `SimInventory.equipItem(...)` / `SimInventory.unequipItem(...)`
- Pickup lifecycle graph:
  - `GameSimulator.step(...)` -> `stepPickups()` -> `applyPickup(player, pickupType)` -> `startRespawn(slotIdx)` -> `stepPickupRespawns()`
- Persistence/bootstrap graph:
  - `InventoryDatabaseLoader.initOrSeed()` -> `InventoryRepository.ensureSchema()` -> `loadItemDefs/loadRecipeDefs` (or `seedItemDefs/seedRecipeDefs`) -> `ItemCache.putAll(...)`
  - Player state persistence -> `InventoryRepository.saveInventory(...)` / `InventoryRepository.loadInventory(...)`

## Contracts

- Pickup IDs and inventory slots are authoritative on server.
- Item and recipe registries can be DB-seeded and reloaded.
- Mission objectives can consume loot events via `MissionManager.onItemCollected(...)`.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/LOOT.md`
