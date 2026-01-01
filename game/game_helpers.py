"""
Game Helper Functions

Helper functions extracted from demo_game.py main() function to reduce complexity.
These functions handle persistence, arcade mode, and other game utilities.
"""

from typing import Any
from systems.save_system import SaveManager
from game.story_manager import StoryManager
from game.inventory_system import Inventory
from game.hub_manager import HubManager
from systems.seed_hierarchy import SeedDerivation
from network import InputPipeline


def persist_player_inventory(save_manager: SaveManager, player_inventory: Inventory) -> None:
    """Persist current inventory/currency into campaign save data."""
    if save_manager and save_manager.data and save_manager.data.campaign:
        inv_dict = {}
        for slot in player_inventory.slots:
            if slot:
                inv_dict[slot.item_id] = inv_dict.get(slot.item_id, 0) + slot.quantity
        save_manager.save_inventory(
            inv_dict,
            player_inventory.equipped_weapon,
            player_inventory.equipped_armor,
            player_inventory.currency
        )


def persist_story_state(save_manager: SaveManager, story_manager: StoryManager) -> None:
    """Persist current story state into campaign save data (v0.7.0)."""
    if save_manager and save_manager.data and save_manager.data.campaign:
        save_manager.data.campaign.story_state = story_manager.to_dict()
        save_manager.mark_dirty()


def get_arcade_seed(hub_manager: HubManager, depth: int) -> int:
    """Derive deterministic arcade seed for a given depth."""
    base_seed = SeedDerivation.derive_region_seed(hub_manager.world_seed, "arcade_loop")
    return SeedDerivation.derive_seed(base_seed, f"depth:{depth}")


def update_replay_metadata(
    input_pipeline: InputPipeline,
    current_play_mode: Any,
    current_hub_id: str,
    current_world_context: str,
    current_seed: int,
    hub_manager: HubManager,
    mission_id: str | None = None
) -> None:
    """Capture current context into replay metadata for determinism."""
    ctx = {
        "mode": current_play_mode.value if current_play_mode else None,
        "hub_id": current_hub_id,
        "world_context": current_world_context,
        "current_seed": current_seed,
        "world_seed": hub_manager.world_seed if hub_manager else current_seed,
        "mission_id": mission_id,
    }
    input_pipeline.metadata.update(ctx)
