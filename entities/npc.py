"""
NPC System - Non-Player Characters for Hubs

This module provides NPC entities for hub worlds:
- Mission giver NPCs
- Shop NPCs
- Lore NPCs (dialogue only)
- Tutorial NPCs
- Interaction detection
- Event emission for dialogue/shops

Version: v0.6.0
"""

from dataclasses import dataclass, field
from enum import Enum

import pygame

from core import EventBus


class NPCType(Enum):
    """NPC functional types"""

    MISSION_GIVER = "mission_giver"
    SHOP = "shop"
    LORE = "lore"
    TUTORIAL = "tutorial"


@dataclass
class NPCDefinition:
    """
    Static NPC definition.

    Defines NPC properties and behavior.
    """

    npc_id: str
    npc_type: NPCType
    display_name: str
    sprite_id: str = "npc_default"  # Sprite sheet identifier
    dialogue_id: str | None = None  # Dialogue tree ID
    shop_tier: int = 1  # For shop NPCs (1-5)
    mission_pool: list[str] = field(default_factory=list)  # For mission givers


@dataclass
class NPC:
    """
    NPC instance in the game world.

    Represents an active NPC with position and state.
    """

    npc_id: str
    npc_type: NPCType
    x: float
    y: float
    width: int = 32
    height: int = 48

    # Visual state
    facing: int = 1  # -1 left, 1 right
    animation_frame: int = 0
    animation_timer: float = 0.0

    # Interaction state
    interaction_radius: float = 48.0  # Pixels
    is_interactable: bool = True
    show_indicator: bool = True  # Show "!" or "?" above NPC

    # Movement state (optional patrol)
    patrol_waypoints: list[tuple[float, float]] = field(default_factory=list)
    current_waypoint_index: int = 0
    patrol_wait_time: float = 0.0  # Time to wait at waypoint
    patrol_speed: float = 30.0  # Slow walking speed (px/s)
    has_patrol: bool = False  # Whether NPC patrols

    def get_rect(self) -> pygame.Rect:
        """Get NPC bounding box for collision/interaction"""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def get_interaction_rect(self) -> pygame.Rect:
        """Get interaction radius rect"""
        radius = int(self.interaction_radius)
        center_x = int(self.x + self.width / 2)
        center_y = int(self.y + self.height / 2)
        return pygame.Rect(center_x - radius, center_y - radius, radius * 2, radius * 2)

    def can_interact_with_player(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> bool:
        """
        Check if player is in interaction range.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            True if player can interact with this NPC
        """
        if not self.is_interactable:
            return False

        # Get player center
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        # Get NPC center
        npc_center_x = self.x + self.width / 2
        npc_center_y = self.y + self.height / 2

        # Check distance
        dx = player_center_x - npc_center_x
        dy = player_center_y - npc_center_y
        distance = (dx * dx + dy * dy) ** 0.5

        return distance <= self.interaction_radius

    def set_patrol_waypoints(self, waypoints: list[tuple[float, float]]):
        """Set patrol waypoints for NPC"""
        self.patrol_waypoints = waypoints
        self.current_waypoint_index = 0
        self.has_patrol = len(waypoints) > 0

    def get_current_waypoint(self) -> tuple[float, float] | None:
        """Get current patrol waypoint"""
        if not self.patrol_waypoints:
            return None
        if self.current_waypoint_index >= len(self.patrol_waypoints):
            return None
        return self.patrol_waypoints[self.current_waypoint_index]

    def advance_waypoint(self):
        """Move to next waypoint (loops)"""
        if not self.patrol_waypoints:
            return
        self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.patrol_waypoints)

    def face_toward(self, target_x: float):
        """
        Face toward a target X position.

        Args:
            target_x: X position to face toward
        """
        npc_center_x = self.x + self.width / 2
        if target_x > npc_center_x:
            self.facing = 1  # Face right
        elif target_x < npc_center_x:
            self.facing = -1  # Face left

    def update(self, dt: float, player_x: float | None = None, player_y: float | None = None):
        """
        Update NPC state.

        Args:
            dt: Delta time in seconds
            player_x: Optional player X position (for facing)
            player_y: Optional player Y position (for interaction range check)
        """
        # Face player if nearby and player position provided
        if player_x is not None and player_y is not None:
            player_center_x = player_x + 16  # Assume 32px player width
            player_center_y = player_y + 28  # Assume 56px player height

            # Get NPC center
            npc_center_x = self.x + self.width / 2
            npc_center_y = self.y + self.height / 2

            # Check if player is nearby (within interaction radius)
            dx = player_center_x - npc_center_x
            dy = player_center_y - npc_center_y
            distance = (dx * dx + dy * dy) ** 0.5

            if distance <= self.interaction_radius:
                # Face player when nearby
                self.face_toward(player_center_x)

        # Handle patrol movement
        if self.has_patrol and len(self.patrol_waypoints) > 0:
            self._update_patrol(dt)

        # Simple idle animation
        self.animation_timer += dt
        if self.animation_timer >= 0.3:  # 300ms per frame
            self.animation_timer = 0.0
            self.animation_frame = (self.animation_frame + 1) % 4

    def _update_patrol(self, dt: float):
        """
        Update patrol movement.

        Args:
            dt: Delta time in seconds
        """
        waypoint = self.get_current_waypoint()
        if waypoint is None:
            return

        # Calculate distance to waypoint
        dx = waypoint[0] - self.x
        dy = waypoint[1] - self.y
        distance = (dx * dx + dy * dy) ** 0.5

        # Check if reached waypoint
        if distance < 8.0:  # Within 8 pixels of waypoint
            # Wait at waypoint
            if self.patrol_wait_time <= 0.0:
                # Start waiting
                self.patrol_wait_time = 2.0  # 2 second wait (longer than enemies)
            else:
                # Continue waiting
                self.patrol_wait_time -= dt

                if self.patrol_wait_time <= 0.0:
                    # Done waiting, advance to next waypoint
                    self.advance_waypoint()
                    self.patrol_wait_time = 0.0
        else:
            # Move toward waypoint
            if distance > 0:
                # Normalize direction
                dir_x = dx / distance

                # Move horizontally only (NPCs don't fly)
                move_x = dir_x * self.patrol_speed * dt
                self.x += move_x

                # Face movement direction
                if move_x > 0:
                    self.facing = 1  # Face right
                elif move_x < 0:
                    self.facing = -1  # Face left


# ============================================================
# NPC Events
# ============================================================


@dataclass
class NPCInteractionEvent:
    """Event emitted when player interacts with NPC"""

    npc_id: str
    npc_type: NPCType
    player_id: int


@dataclass
class DialogueStartEvent:
    """Event emitted to start dialogue with NPC"""

    npc_id: str
    dialogue_id: str


@dataclass
class ShopOpenEvent:
    """Event emitted to open shop interface"""

    npc_id: str
    shop_tier: int


@dataclass
class MissionMenuOpenEvent:
    """Event emitted to open mission selection menu"""

    npc_id: str
    mission_pool: list[str]


# ============================================================
# NPC Manager
# ============================================================


class NPCManager:
    """
    Manages NPC instances and interactions.

    Handles NPC spawning, updates, and interaction detection.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize NPC manager.

        Args:
            event_bus: Event bus for emitting events
        """
        self.event_bus = event_bus
        self.npcs: list[NPC] = []
        self.npc_definitions: dict[str, NPCDefinition] = {}
        self._register_default_npcs()

    def register_npc_definition(self, npc_def: NPCDefinition):
        """Register an NPC definition"""
        self.npc_definitions[npc_def.npc_id] = npc_def

    def get_npc_definition(self, npc_id: str) -> NPCDefinition | None:
        """Get NPC definition by ID"""
        return self.npc_definitions.get(npc_id)

    def spawn_npc(self, npc_id: str, x: float, y: float) -> NPC | None:
        """
        Spawn an NPC instance.

        Args:
            npc_id: NPC definition ID
            x: World X position
            y: World Y position

        Returns:
            NPC instance or None if definition not found
        """
        npc_def = self.get_npc_definition(npc_id)
        if npc_def is None:
            print(f"[WARNING] NPC definition not found: {npc_id}")
            return None

        npc = NPC(npc_id=npc_id, npc_type=npc_def.npc_type, x=x, y=y)

        self.npcs.append(npc)
        return npc

    def clear_npcs(self):
        """Remove all NPCs (e.g., when changing hubs)"""
        self.npcs.clear()

    def set_npc_patrol(self, npc_id: str, waypoints: list[tuple[float, float]]):
        """
        Set patrol waypoints for an NPC.

        Args:
            npc_id: NPC ID to set patrol for
            waypoints: List of (x, y) waypoint positions
        """
        for npc in self.npcs:
            if npc.npc_id == npc_id:
                npc.set_patrol_waypoints(waypoints)
                return
        print(f"[WARNING] NPC not found for patrol setup: {npc_id}")

    def update(self, dt: float, player_x: float | None = None, player_y: float | None = None):
        """
        Update all NPCs.

        Args:
            dt: Delta time in seconds
            player_x: Optional player X position (for NPCs to face player)
            player_y: Optional player Y position (for NPCs to face player)
        """
        for npc in self.npcs:
            npc.update(dt, player_x, player_y)

    def check_interaction(
        self,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        player_id: int = 0,
    ) -> NPC | None:
        """
        Check if player can interact with any NPC.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height
            player_id: Player ID

        Returns:
            Closest NPC player can interact with, or None
        """
        closest_npc = None
        closest_distance = float("inf")

        # Get player center
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        for npc in self.npcs:
            if npc.can_interact_with_player(player_x, player_y, player_width, player_height):
                # Calculate distance to this NPC
                npc_center_x = npc.x + npc.width / 2
                npc_center_y = npc.y + npc.height / 2
                dx = player_center_x - npc_center_x
                dy = player_center_y - npc_center_y
                distance = (dx * dx + dy * dy) ** 0.5

                # Keep track of closest
                if distance < closest_distance:
                    closest_distance = distance
                    closest_npc = npc

        return closest_npc

    def interact_with_npc(self, npc: NPC, player_id: int = 0):
        """
        Interact with an NPC.

        Emits appropriate event based on NPC type.

        Args:
            npc: NPC to interact with
            player_id: Player ID
        """
        # Emit general interaction event
        self.event_bus.emit(
            NPCInteractionEvent(npc_id=npc.npc_id, npc_type=npc.npc_type, player_id=player_id)
        )

        # Get NPC definition
        npc_def = self.get_npc_definition(npc.npc_id)
        if npc_def is None:
            return

        # Emit type-specific events
        if npc.npc_type == NPCType.SHOP:
            self.event_bus.emit(ShopOpenEvent(npc_id=npc.npc_id, shop_tier=npc_def.shop_tier))

        elif npc.npc_type == NPCType.MISSION_GIVER:
            self.event_bus.emit(
                MissionMenuOpenEvent(npc_id=npc.npc_id, mission_pool=npc_def.mission_pool)
            )

        elif npc.npc_type in (NPCType.LORE, NPCType.TUTORIAL):
            if npc_def.dialogue_id:
                self.event_bus.emit(
                    DialogueStartEvent(npc_id=npc.npc_id, dialogue_id=npc_def.dialogue_id)
                )

    def get_nearby_npcs(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> list[NPC]:
        """
        Get all NPCs in interaction range of player.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            List of NPCs in range
        """
        nearby = []
        for npc in self.npcs:
            if npc.can_interact_with_player(player_x, player_y, player_width, player_height):
                nearby.append(npc)
        return nearby

    def _register_default_npcs(self):
        """Register default NPC definitions"""

        # Central Hub NPCs
        self.register_npc_definition(
            NPCDefinition(
                npc_id="tutorial_elder",
                npc_type=NPCType.TUTORIAL,
                display_name="Elder Guardian",
                dialogue_id="tutorial_elder",
            )
        )

        # Forest Hub NPCs
        self.register_npc_definition(
            NPCDefinition(
                npc_id="forest_ranger",
                npc_type=NPCType.MISSION_GIVER,
                display_name="Forest Ranger",
                mission_pool=[
                    "demo_coin_run",
                    "forest_1",
                    "forest_2",
                    "forest_3",
                    "forest_4",
                    "forest_5",
                ],
            )
        )

        self.register_npc_definition(
            NPCDefinition(
                npc_id="forest_merchant",
                npc_type=NPCType.SHOP,
                display_name="Forest Merchant",
                shop_tier=1,
            )
        )

        # Town Hub NPCs
        self.register_npc_definition(
            NPCDefinition(
                npc_id="town_captain",
                npc_type=NPCType.MISSION_GIVER,
                display_name="Town Captain",
                mission_pool=["town_1", "town_2", "town_3", "town_4", "town_5", "town_6"],
            )
        )

        self.register_npc_definition(
            NPCDefinition(
                npc_id="town_blacksmith",
                npc_type=NPCType.SHOP,
                display_name="Blacksmith",
                shop_tier=2,
            )
        )

        self.register_npc_definition(
            NPCDefinition(
                npc_id="town_historian",
                npc_type=NPCType.LORE,
                display_name="Town Historian",
                dialogue_id="town_history",
            )
        )

        # Caves Hub NPCs
        self.register_npc_definition(
            NPCDefinition(
                npc_id="cave_explorer",
                npc_type=NPCType.MISSION_GIVER,
                display_name="Cave Explorer",
                mission_pool=["caves_1", "caves_2", "caves_3", "caves_4", "caves_5"],
            )
        )

        self.register_npc_definition(
            NPCDefinition(
                npc_id="crystal_trader",
                npc_type=NPCType.SHOP,
                display_name="Crystal Trader",
                shop_tier=3,
            )
        )

        # Castle Hub NPCs
        self.register_npc_definition(
            NPCDefinition(
                npc_id="castle_commander",
                npc_type=NPCType.MISSION_GIVER,
                display_name="Castle Commander",
                mission_pool=[
                    "castle_1",
                    "castle_2",
                    "castle_3",
                    "castle_4",
                    "castle_5",
                    "castle_6",
                ],
            )
        )

        self.register_npc_definition(
            NPCDefinition(
                npc_id="castle_armorer",
                npc_type=NPCType.SHOP,
                display_name="Castle Armorer",
                shop_tier=4,
            )
        )

        # Sewer Hub NPCs
        self.register_npc_definition(
            NPCDefinition(
                npc_id="sewer_scout",
                npc_type=NPCType.MISSION_GIVER,
                display_name="Sewer Scout",
                mission_pool=["sewer_1", "sewer_2", "sewer_3"],
            )
        )

        self.register_npc_definition(
            NPCDefinition(
                npc_id="sewer_vendor",
                npc_type=NPCType.SHOP,
                display_name="Sewer Vendor",
                shop_tier=5,
            )
        )
