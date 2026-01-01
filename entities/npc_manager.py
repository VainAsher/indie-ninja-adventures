"""
NPC Manager - Dynamic NPC spawning based on story state

Manages NPC presence in the hub based on The Hollowed Ninja story progression.

Features:
- Load NPC definitions from hub_states.json
- Spawn/despawn NPCs based on current act and story events
- Track active NPCs in the hub
- Provide NPC update and rendering interfaces

Version: v0.7.0
"""

import json
from pathlib import Path

from entities.npc import NPC, NPCType
from game.story_manager import StoryManager


class NPCManager:
    """
    Manages dynamic NPC spawning and despawning based on story state.

    Responsibilities:
    - Load hub state configurations
    - Spawn NPCs for current story act
    - Despawn NPCs when story progresses
    - Track active NPCs in hub
    - Provide NPC query methods
    """

    def __init__(self, hub_states_file: str = "data/hub_states.json"):
        """
        Initialize NPC manager.

        Args:
            hub_states_file: Path to hub states configuration
        """
        self.hub_states_file = hub_states_file
        self.hub_states_data: dict = {}
        self.npc_definitions: dict[str, dict] = {}

        # Active NPCs in hub (npc_id -> NPC instance)
        self.active_npcs: dict[str, NPC] = {}

        # Track current story state
        self.current_act: int = 0
        self.current_degradation_level: int = 0  # For Act 0
        self.current_lanterns_met: int = 0  # For Act 2

        # Load hub states configuration
        self._load_hub_states()

    def _load_hub_states(self) -> None:
        """Load hub states and NPC definitions from JSON."""
        try:
            hub_states_path = Path(self.hub_states_file)
            if not hub_states_path.exists():
                print(f"[NPCManager] WARNING: Hub states file not found: {self.hub_states_file}")
                print("[NPCManager] Creating empty configuration...")
                self.hub_states_data = {"act_states": {}, "npc_definitions": {}}
                return

            with open(hub_states_path) as f:
                self.hub_states_data = json.load(f)

            # Extract NPC definitions
            npc_defs = self.hub_states_data.get("npc_definitions", {})

            # Flatten all NPC definitions into a single dict
            for category, npcs in npc_defs.items():
                for npc_id, npc_data in npcs.items():
                    self.npc_definitions[npc_id] = npc_data

            print(f"[NPCManager] Loaded {len(self.npc_definitions)} NPC definitions")

        except Exception as e:
            print(f"[NPCManager] Error loading hub states: {e}")
            self.hub_states_data = {"act_states": {}, "npc_definitions": {}}
            self.npc_definitions = {}

    def update_from_story_manager(self, story_manager: StoryManager) -> dict[str, list[str]]:
        """
        Update NPC spawning based on story manager state.

        Args:
            story_manager: Current story manager instance

        Returns:
            Dictionary with 'spawned' and 'despawned' NPC lists
        """
        changes = {"spawned": [], "despawned": []}

        # Get target NPC list based on story state
        target_npcs = self._get_target_npcs(story_manager)

        # Determine which NPCs to spawn/despawn
        current_npc_ids = set(self.active_npcs.keys())
        target_npc_ids = set(target_npcs)

        # NPCs to spawn
        to_spawn = target_npc_ids - current_npc_ids
        for npc_id in to_spawn:
            if self._spawn_npc(npc_id):
                changes["spawned"].append(npc_id)

        # NPCs to despawn
        to_despawn = current_npc_ids - target_npc_ids
        for npc_id in to_despawn:
            if self._despawn_npc(npc_id):
                changes["despawned"].append(npc_id)

        # Update tracking
        self.current_act = story_manager.current_act
        self.current_degradation_level = story_manager.act0_hub_degradation_level
        self.current_lanterns_met = story_manager.act2_lanterns_met

        return changes

    def _get_target_npcs(self, story_manager: StoryManager) -> list[str]:
        """
        Get list of NPCs that should be active for current story state.

        Args:
            story_manager: Current story manager

        Returns:
            List of NPC IDs that should be spawned
        """
        act_states = self.hub_states_data.get("act_states", {})
        act = story_manager.current_act

        # Act 0: Progressive degradation
        if act == 0:
            act_data = act_states.get("act_0", {})
            degradation_levels = act_data.get("degradation_levels", {})

            # Find the appropriate degradation level
            degradation_level = story_manager.act0_hub_degradation_level

            # Get the degradation level data (use closest match)
            level_data = None
            for level_key in sorted(degradation_levels.keys(), key=int, reverse=True):
                if int(level_key) <= degradation_level:
                    level_data = degradation_levels[level_key]
                    break

            if level_data is None:
                level_data = degradation_levels.get("0", {})

            return level_data.get("npcs_active", [])

        # Act 1: Empty or just Veil Maiden
        elif act == 1:
            act_data = act_states.get("act_1", {})
            return act_data.get("npcs_active", [])

        # Act 2: Progressive Lanterns appearing
        elif act == 2:
            act_data = act_states.get("act_2", {})
            lantern_progression = act_data.get("lantern_progression", {})

            # Find appropriate lantern level
            lanterns_met = story_manager.act2_lanterns_met

            # Get lantern level data (use closest match)
            level_data = None
            for level_key in sorted(lantern_progression.keys(), key=int, reverse=True):
                if int(level_key) <= lanterns_met:
                    level_data = lantern_progression[level_key]
                    break

            if level_data is None:
                level_data = lantern_progression.get("0", {})

            return level_data.get("npcs_active", [])

        # Act 3 & 4: Fixed NPC list
        elif act == 3:
            act_data = act_states.get("act_3", {})
            return act_data.get("npcs_active", [])

        elif act == 4:
            act_data = act_states.get("act_4", {})
            return act_data.get("npcs_active", [])

        # Postgame
        elif story_manager.game_completed:
            postgame_data = act_states.get("postgame", {})
            npcs = postgame_data.get("npcs_active", [])

            # Check if Veil Maiden was saved (add redeemed version)
            if story_manager.ending_achieved == "save":
                if "veil_maiden_redeemed" not in npcs:
                    npcs = npcs.copy()
                    npcs.append("veil_maiden_redeemed")

            return npcs

        return []

    def _spawn_npc(self, npc_id: str) -> bool:
        """
        Spawn an NPC in the hub.

        Args:
            npc_id: ID of NPC to spawn

        Returns:
            True if spawned successfully
        """
        if npc_id in self.active_npcs:
            return False  # Already spawned

        # Get NPC definition
        npc_def = self.npc_definitions.get(npc_id)
        if not npc_def:
            print(f"[NPCManager] WARNING: NPC definition not found: {npc_id}")
            return False

        # Create NPC instance
        position = npc_def.get("position", [600, 350])
        role = npc_def.get("role", "ambient")

        # Map role to NPCType
        npc_type_map = {
            "tutorial": NPCType.TUTORIAL,
            "shop_weapons": NPCType.SHOP,
            "shop_armor": NPCType.SHOP,
            "story_critical": NPCType.LORE,
            "story_lantern": NPCType.LORE,
            "ambient": NPCType.LORE,
        }

        npc_type = npc_type_map.get(role, NPCType.LORE)

        npc = NPC(
            npc_id=npc_id,
            npc_type=npc_type,
            x=float(position[0]),
            y=float(position[1]),
            width=32,
            height=48,
        )

        self.active_npcs[npc_id] = npc
        print(f"[NPCManager] Spawned NPC: {npc_id} at ({position[0]}, {position[1]})")
        return True

    def _despawn_npc(self, npc_id: str) -> bool:
        """
        Despawn an NPC from the hub.

        Args:
            npc_id: ID of NPC to despawn

        Returns:
            True if despawned successfully
        """
        if npc_id not in self.active_npcs:
            return False  # Not spawned

        del self.active_npcs[npc_id]
        print(f"[NPCManager] Despawned NPC: {npc_id}")
        return True

    def get_active_npcs(self) -> list[NPC]:
        """Get list of all active NPCs."""
        return list(self.active_npcs.values())

    def get_npc_by_id(self, npc_id: str) -> NPC | None:
        """Get specific NPC by ID."""
        return self.active_npcs.get(npc_id)

    def get_npc_definition(self, npc_id: str) -> dict | None:
        """Get NPC definition data."""
        return self.npc_definitions.get(npc_id)

    def get_interactable_npcs_near_player(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> list[NPC]:
        """
        Get NPCs that the player can interact with.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            List of NPCs in interaction range
        """
        interactable = []
        for npc in self.active_npcs.values():
            if npc.can_interact_with_player(player_x, player_y, player_width, player_height):
                interactable.append(npc)

        return interactable

    def update(self, dt: float) -> None:
        """
        Update all active NPCs.

        Args:
            dt: Delta time in seconds
        """
        for npc in self.active_npcs.values():
            # Update NPC animation
            npc.animation_timer += dt
            if npc.animation_timer >= 0.2:  # 5 FPS animation
                npc.animation_timer = 0.0
                npc.animation_frame = (npc.animation_frame + 1) % 4

            # Update patrol movement (if NPC has patrol)
            if npc.has_patrol and npc.patrol_waypoints:
                self._update_npc_patrol(npc, dt)

    def _update_npc_patrol(self, npc: NPC, dt: float) -> None:
        """
        Update NPC patrol movement.

        Args:
            npc: NPC instance
            dt: Delta time
        """
        if not npc.patrol_waypoints:
            return

        # Get target waypoint
        waypoint = npc.patrol_waypoints[npc.current_waypoint_index]
        target_x, target_y = waypoint

        # Move toward waypoint
        dx = target_x - npc.x
        dy = target_y - npc.y
        distance = (dx**2 + dy**2) ** 0.5

        if distance < 5.0:
            # Reached waypoint, move to next
            npc.current_waypoint_index = (npc.current_waypoint_index + 1) % len(
                npc.patrol_waypoints
            )
        else:
            # Move toward waypoint
            move_amount = npc.patrol_speed * dt
            if distance > 0:
                npc.x += (dx / distance) * move_amount
                npc.y += (dy / distance) * move_amount
                npc.facing = 1 if dx > 0 else -1

    def clear_all_npcs(self) -> None:
        """Remove all NPCs from hub."""
        self.active_npcs.clear()
        print("[NPCManager] Cleared all NPCs")

    def get_hub_brightness(self, story_manager: StoryManager) -> float:
        """
        Get current hub brightness based on story state.

        Args:
            story_manager: Story manager instance

        Returns:
            Brightness value (0.0 - 1.0)
        """
        return story_manager.get_hub_brightness()

    def get_hub_atmosphere(self, story_manager: StoryManager) -> str:
        """
        Get current hub atmosphere based on story state.

        Args:
            story_manager: Story manager instance

        Returns:
            Atmosphere string ("vibrant", "dimming", "dark", etc.)
        """
        return story_manager.hub_state.atmosphere
