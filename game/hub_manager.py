"""
Hub Manager - Hub World Generation and Management

This module provides hub world generation for campaign mode:
- Central hub connecting all regions
- Regional hubs for each biome
- NPC placement via anchor system
- Portal placement for fast travel
- Deterministic generation using seed hierarchy

Version: v0.6.0
"""

from dataclasses import dataclass, field
from enum import Enum

from config.physics_constants import ROOM_HEIGHT_TILES, ROOM_WIDTH_TILES, TILE_SIZE
from systems.seed_hierarchy import SeedDerivation
from systems.world_generation import BiomeTheme, WorldGenerator, WorldShape

ROOM_PIXEL_CENTER_X = ROOM_WIDTH_TILES * TILE_SIZE // 2
ROOM_PIXEL_CENTER_Y = ROOM_HEIGHT_TILES * TILE_SIZE // 2


class HubType(Enum):
    """Hub world types"""

    CENTRAL = "central"  # Main hub connecting all regions
    REGION = "region"  # Region-specific hub


@dataclass
class NPCAnchor:
    """
    NPC placement anchor in hub world.

    Defines where an NPC should be spawned and their properties.
    """

    npc_id: str
    npc_type: str  # "mission_giver", "shop", "lore", "tutorial"
    grid_x: int
    grid_y: int
    local_x: int = ROOM_PIXEL_CENTER_X  # Center of room
    local_y: int = ROOM_PIXEL_CENTER_Y

    def get_world_position(self, room_px: int, room_py: int) -> tuple[int, int]:
        """Get NPC world position from room position"""
        return (room_px + self.local_x, room_py + self.local_y)


@dataclass
class PortalAnchor:
    """
    Portal placement anchor in hub world.

    Defines portal location and destination.
    """

    portal_id: str
    destination_hub_id: str
    grid_x: int
    grid_y: int
    local_x: int = ROOM_PIXEL_CENTER_X
    local_y: int = ROOM_PIXEL_CENTER_Y
    bidirectional: bool = True  # Can travel both ways

    def get_world_position(self, room_px: int, room_py: int) -> tuple[int, int]:
        """Get portal world position from room position"""
        return (room_px + self.local_x, room_py + self.local_y)


@dataclass
class HubDefinition:
    """
    Hub world definition.

    Contains all data needed to generate a hub world.
    """

    hub_id: str
    hub_type: HubType
    display_name: str
    description: str
    biome_theme: BiomeTheme
    room_count: int
    world_shape: WorldShape

    # Anchors for NPCs and portals
    npc_anchors: list[NPCAnchor] = field(default_factory=list)
    portal_anchors: list[PortalAnchor] = field(default_factory=list)

    # Spawn point (grid coordinates + local offset)
    spawn_grid: tuple[int, int] = (0, 0)
    spawn_local: tuple[int, int] = (ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y)


class HubManager:
    """
    Manages hub world generation and state.

    Provides hub creation using existing world generation
    with hub-specific configuration.
    """

    def __init__(self, world_seed: int):
        """
        Initialize hub manager.

        Args:
            world_seed: Base seed for campaign world
        """
        self.world_seed = world_seed
        self.hub_definitions: dict[str, HubDefinition] = {}
        self._register_default_hubs()

    def register_hub(self, hub_def: HubDefinition):
        """Register a hub definition"""
        self.hub_definitions[hub_def.hub_id] = hub_def

    def get_hub_definition(self, hub_id: str) -> HubDefinition | None:
        """Get hub definition by ID"""
        return self.hub_definitions.get(hub_id)

    def generate_hub_world(self, hub_id: str):
        """
        Generate a hub world.

        Args:
            hub_id: ID of hub to generate

        Returns:
            Tuple of (world, hub_definition) or (None, None) if hub not found
        """
        hub_def = self.get_hub_definition(hub_id)
        if hub_def is None:
            return None, None

        # Derive hub-specific seed
        hub_seed = SeedDerivation.derive_region_seed(self.world_seed, hub_id)

        # Generate world using WorldGenerator
        generator = WorldGenerator(hub_seed)
        world = generator.generate(
            num_biomes=1, rooms_per_biome=hub_def.room_count, shape=hub_def.world_shape
        )

        # Mark rooms as hub rooms
        for room in world.all_rooms:
            room.is_hub = True
            room.hub_id = hub_id

        return world, hub_def

    def _resolve_anchor_room_coords(
        self,
        room_positions: dict,
        anchor_coords: tuple[int, int],
        base_room_coords: tuple[int, int] | None,
    ) -> tuple[int, int] | None:
        if anchor_coords in room_positions:
            return anchor_coords

        if base_room_coords is not None:
            offset_coords = (
                base_room_coords[0] + anchor_coords[0],
                base_room_coords[1] + anchor_coords[1],
            )
            if offset_coords in room_positions:
                return offset_coords
            if base_room_coords in room_positions:
                return base_room_coords

        if room_positions:
            return next(iter(room_positions))

        return None

    def get_spawn_position(
        self, hub_id: str, room_positions: dict, base_room_coords: tuple[int, int] | None = None
    ) -> tuple[int, int] | None:
        """
        Get spawn position for a hub.

        Args:
            hub_id: Hub ID
            room_positions: Dictionary mapping (grid_x, grid_y) -> (px, py)

        Returns:
            World position (x, y) or None if hub not found
        """
        hub_def = self.get_hub_definition(hub_id)
        if hub_def is None:
            return None

        # Get room position
        spawn_coords = self._resolve_anchor_room_coords(
            room_positions, hub_def.spawn_grid, base_room_coords
        )
        if spawn_coords is None:
            return None

        room_px, room_py = room_positions[spawn_coords]

        # Add local offset
        spawn_x = room_px + hub_def.spawn_local[0]
        spawn_y = room_py + hub_def.spawn_local[1]

        return (spawn_x, spawn_y)

    def get_npc_positions(
        self, hub_id: str, room_positions: dict, base_room_coords: tuple[int, int] | None = None
    ) -> list[tuple[NPCAnchor, int, int]]:
        """
        Get NPC spawn positions for a hub.

        Args:
            hub_id: Hub ID
            room_positions: Dictionary mapping (grid_x, grid_y) -> (px, py)

        Returns:
            List of (npc_anchor, world_x, world_y) tuples
        """
        hub_def = self.get_hub_definition(hub_id)
        if hub_def is None:
            return []

        npc_positions = []
        for anchor in hub_def.npc_anchors:
            anchor_coords = (anchor.grid_x, anchor.grid_y)
            room_coords = self._resolve_anchor_room_coords(
                room_positions, anchor_coords, base_room_coords
            )
            if room_coords is None:
                continue
            room_px, room_py = room_positions[room_coords]
            world_x, world_y = anchor.get_world_position(room_px, room_py)
            npc_positions.append((anchor, world_x, world_y))

        return npc_positions

    def get_portal_positions(
        self, hub_id: str, room_positions: dict, base_room_coords: tuple[int, int] | None = None
    ) -> list[tuple[PortalAnchor, int, int]]:
        """
        Get portal spawn positions for a hub.

        Args:
            hub_id: Hub ID
            room_positions: Dictionary mapping (grid_x, grid_y) -> (px, py)

        Returns:
            List of (portal_anchor, world_x, world_y) tuples
        """
        hub_def = self.get_hub_definition(hub_id)
        if hub_def is None:
            return []

        portal_positions = []
        for anchor in hub_def.portal_anchors:
            anchor_coords = (anchor.grid_x, anchor.grid_y)
            room_coords = self._resolve_anchor_room_coords(
                room_positions, anchor_coords, base_room_coords
            )
            if room_coords is None:
                continue
            room_px, room_py = room_positions[room_coords]
            world_x, world_y = anchor.get_world_position(room_px, room_py)
            portal_positions.append((anchor, world_x, world_y))

        return portal_positions

    def _register_default_hubs(self):
        """Register default hub definitions"""

        # ============================================================
        # CENTRAL HUB
        # ============================================================

        central_hub = HubDefinition(
            hub_id="central_hub",
            hub_type=HubType.CENTRAL,
            display_name="Adventurer's Nexus",
            description="The central hub connecting all regions of the world.",
            biome_theme=BiomeTheme.DUNGEON,  # Neutral theme
            room_count=15,
            world_shape=WorldShape.GRID,
            spawn_grid=(0, 0),
            spawn_local=(ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y),
        )

        # Add tutorial NPC at spawn
        central_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="tutorial_elder",
                npc_type="tutorial",
                grid_x=0,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X + 240,  # Slightly right of spawn
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Add portals to regional hubs (assuming BLOB generates rooms around origin)
        # Note: Actual room positions depend on world generation
        # These are example placements - will need adjustment based on generated layout

        # Forest portal (north)
        central_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_forest",
                destination_hub_id="forest_hub",
                grid_x=0,
                grid_y=-1,  # North room
                local_x=ROOM_PIXEL_CENTER_X,
                local_y=ROOM_PIXEL_CENTER_Y - 180,
                bidirectional=True,
            )
        )

        # Town portal (east)
        central_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_town",
                destination_hub_id="town_hub",
                grid_x=1,
                grid_y=0,  # East room
                local_x=ROOM_PIXEL_CENTER_X + 240,
                local_y=ROOM_PIXEL_CENTER_Y,
                bidirectional=True,
            )
        )

        # Caves portal (south)
        central_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_caves",
                destination_hub_id="caves_hub",
                grid_x=0,
                grid_y=1,  # South room
                local_x=ROOM_PIXEL_CENTER_X,
                local_y=ROOM_PIXEL_CENTER_Y + 180,
                bidirectional=True,
            )
        )

        # Castle portal (shares east room with town)
        central_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_castle",
                destination_hub_id="castle_hub",
                grid_x=1,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X + 320,
                local_y=ROOM_PIXEL_CENTER_Y - 180,
                bidirectional=True,
            )
        )

        # Sewer portal (shares south room with caves)
        central_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_sewer",
                destination_hub_id="sewer_hub",
                grid_x=0,
                grid_y=1,
                local_x=ROOM_PIXEL_CENTER_X - 320,
                local_y=ROOM_PIXEL_CENTER_Y + 180,
                bidirectional=True,
            )
        )

        # Arcade portal (west) - endless procedural loop
        central_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_arcade",
                destination_hub_id="arcade_loop",
                grid_x=-1,
                grid_y=0,  # West room
                local_x=ROOM_PIXEL_CENTER_X - 240,
                local_y=ROOM_PIXEL_CENTER_Y,
                bidirectional=True,
            )
        )

        self.register_hub(central_hub)

        # ============================================================
        # FOREST HUB
        # ============================================================

        forest_hub = HubDefinition(
            hub_id="forest_hub",
            hub_type=HubType.REGION,
            display_name="Whispering Grove",
            description="A peaceful clearing in the mystical forest.",
            biome_theme=BiomeTheme.DUNGEON,  # Will use forest theme
            room_count=4,
            world_shape=WorldShape.GRID,
            spawn_grid=(0, 0),
            spawn_local=(ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y),
        )

        # Mission giver NPC
        forest_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="forest_ranger",
                npc_type="mission_giver",
                grid_x=0,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X - 240,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Shop NPC
        forest_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="forest_merchant",
                npc_type="shop",
                grid_x=0,
                grid_y=1,
                local_x=ROOM_PIXEL_CENTER_X + 200,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Portal back to central hub
        forest_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_central",
                destination_hub_id="central_hub",
                grid_x=0,
                grid_y=-1,
                bidirectional=True,
            )
        )

        self.register_hub(forest_hub)

        # ============================================================
        # TOWN HUB
        # ============================================================

        town_hub = HubDefinition(
            hub_id="town_hub",
            hub_type=HubType.REGION,
            display_name="Ashenvale Square",
            description="The heart of the troubled town.",
            biome_theme=BiomeTheme.DUNGEON,  # Will use town theme
            room_count=4,
            world_shape=WorldShape.GRID,
            spawn_grid=(0, 0),
            spawn_local=(ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y),
        )

        # Mission giver NPC
        town_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="town_captain",
                npc_type="mission_giver",
                grid_x=0,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X - 240,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Shop NPC (better inventory than forest)
        town_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="town_blacksmith",
                npc_type="shop",
                grid_x=1,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X + 200,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Lore NPC
        town_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="town_historian",
                npc_type="lore",
                grid_x=-1,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Portal back to central hub
        town_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_central",
                destination_hub_id="central_hub",
                grid_x=0,
                grid_y=-1,
                bidirectional=True,
            )
        )

        self.register_hub(town_hub)

        # ============================================================
        # CAVES HUB
        # ============================================================

        caves_hub = HubDefinition(
            hub_id="caves_hub",
            hub_type=HubType.REGION,
            display_name="Crystal Cavern Haven",
            description="A safe refuge deep in the crystal caverns.",
            biome_theme=BiomeTheme.DUNGEON,  # Will use caves theme
            room_count=4,
            world_shape=WorldShape.GRID,
            spawn_grid=(0, 0),
            spawn_local=(ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y),
        )

        # Mission giver NPC
        caves_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="cave_explorer",
                npc_type="mission_giver",
                grid_x=0,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X - 240,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Shop NPC (high tier inventory)
        caves_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="crystal_trader",
                npc_type="shop",
                grid_x=0,
                grid_y=1,
                local_x=ROOM_PIXEL_CENTER_X + 200,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Portal back to central hub
        caves_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_central",
                destination_hub_id="central_hub",
                grid_x=0,
                grid_y=-1,
                bidirectional=True,
            )
        )

        self.register_hub(caves_hub)

        # ============================================================
        # CASTLE HUB
        # ============================================================

        castle_hub = HubDefinition(
            hub_id="castle_hub",
            hub_type=HubType.REGION,
            display_name="Obsidian Castle",
            description="A fortress of stone and shadow.",
            biome_theme=BiomeTheme.BUILDING,
            room_count=4,
            world_shape=WorldShape.GRID,
            spawn_grid=(0, 0),
            spawn_local=(ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y),
        )

        # Mission giver NPC
        castle_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="castle_commander",
                npc_type="mission_giver",
                grid_x=0,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X - 240,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Shop NPC
        castle_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="castle_armorer",
                npc_type="shop",
                grid_x=1,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X + 200,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Portal back to central hub
        castle_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_central",
                destination_hub_id="central_hub",
                grid_x=0,
                grid_y=-1,
                bidirectional=True,
            )
        )

        self.register_hub(castle_hub)

        # ============================================================
        # SEWER HUB
        # ============================================================

        sewer_hub = HubDefinition(
            hub_id="sewer_hub",
            hub_type=HubType.REGION,
            display_name="Shadow Sewers",
            description="Toxic tunnels beneath the city.",
            biome_theme=BiomeTheme.DUNGEON,
            room_count=4,
            world_shape=WorldShape.GRID,
            spawn_grid=(0, 0),
            spawn_local=(ROOM_PIXEL_CENTER_X, ROOM_PIXEL_CENTER_Y),
        )

        # Mission giver NPC
        sewer_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="sewer_scout",
                npc_type="mission_giver",
                grid_x=0,
                grid_y=0,
                local_x=ROOM_PIXEL_CENTER_X - 240,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Shop NPC
        sewer_hub.npc_anchors.append(
            NPCAnchor(
                npc_id="sewer_vendor",
                npc_type="shop",
                grid_x=0,
                grid_y=1,
                local_x=ROOM_PIXEL_CENTER_X + 200,
                local_y=ROOM_PIXEL_CENTER_Y,
            )
        )

        # Portal back to central hub
        sewer_hub.portal_anchors.append(
            PortalAnchor(
                portal_id="portal_to_central",
                destination_hub_id="central_hub",
                grid_x=0,
                grid_y=-1,
                bidirectional=True,
            )
        )

        self.register_hub(sewer_hub)


# Global hub manager instance (will be initialized with campaign seed)
_hub_manager: HubManager | None = None


def initialize_hub_manager(world_seed: int):
    """Initialize the global hub manager with campaign seed"""
    global _hub_manager
    _hub_manager = HubManager(world_seed)


def get_hub_manager() -> HubManager | None:
    """Get the global hub manager instance"""
    return _hub_manager
