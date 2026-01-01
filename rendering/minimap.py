"""
Enhanced Minimap System - Visual World Navigation

Features:
- Room type color coding (start, exit, shop, combat, treasure, boss)
- Player position indicator (dot within current room)
- Connection lines between adjacent rooms
- Current room highlight
- Scalable layout using megamap room positions

Based on: Phase 6 Enhanced Minimap specification
"""

from dataclasses import dataclass

import pygame

from systems.megamap import Megamap
from systems.world_generation import RoomNode, RoomType, World

# Minimap display settings
MINIMAP_ROOM_SIZE = 16  # Pixels per room on minimap
MINIMAP_PADDING = 8  # Padding around minimap
MINIMAP_BORDER = 2  # Border thickness
MINIMAP_BG_COLOR = (20, 20, 30, 200)  # Semi-transparent background
MINIMAP_BORDER_COLOR = (100, 100, 120)

# Room type colors
ROOM_COLORS = {
    RoomType.START: (80, 220, 80),  # Green - spawn point
    RoomType.EXIT: (220, 80, 80),  # Red - goal
    RoomType.SHOP: (220, 180, 80),  # Gold - shop
    RoomType.COMBAT: (180, 80, 80),  # Dark red - danger
    RoomType.PLATFORM: (120, 120, 160),  # Blue-gray - platforming challenge
    RoomType.TREASURE: (220, 220, 80),  # Yellow - loot
    RoomType.BOSS: (180, 80, 180),  # Purple - boss fight
}

# Player indicator
PLAYER_DOT_COLOR = (255, 255, 255)  # White dot
PLAYER_DOT_SIZE = 3  # Radius in pixels

# Current room highlight
CURRENT_ROOM_COLOR = (255, 255, 255)  # White outline
CURRENT_ROOM_THICKNESS = 2  # Border thickness

# Connection lines
CONNECTION_COLOR = (80, 80, 100)  # Gray lines between rooms
CONNECTION_THICKNESS = 1


@dataclass
class MinimapConfig:
    """
    Configuration for minimap rendering

    Attributes:
        position: (x, y) position on screen (top-left corner)
        show_connections: Draw lines between connected rooms
        show_player: Draw player position indicator
        highlight_current: Highlight current room
        scale: Room size in pixels
    """

    position: tuple[int, int] = (10, 400)
    show_connections: bool = True
    show_player: bool = True
    highlight_current: bool = True
    scale: int = MINIMAP_ROOM_SIZE


class MinimapRenderer:
    """
    Enhanced minimap renderer with room type colors and player position
    """

    def __init__(self, config: MinimapConfig | None = None):
        """
        Initialize minimap renderer

        Args:
            config: Optional configuration, uses defaults if None
        """
        self.config = config or MinimapConfig()
        self.surface: pygame.Surface | None = None

    def render(
        self,
        screen: pygame.Surface,
        world: World,
        megamap: Megamap,
        player_pos: tuple[float, float],
        current_room_coords: tuple[int, int] | None = None,
    ) -> None:
        """
        Render the minimap to screen

        Args:
            screen: Pygame screen surface to draw on
            world: Generated world with room graph
            megamap: Megamap with room positions
            player_pos: Player position in pixels (x, y)
            current_room_coords: Current room coordinates (grid_x, grid_y)
        """
        # Calculate minimap dimensions
        minx, miny, maxx, maxy = world.bounds
        span_w = maxx - minx + 1
        span_h = maxy - miny + 1

        minimap_w = span_w * self.config.scale + 2 * MINIMAP_PADDING
        minimap_h = span_h * self.config.scale + 2 * MINIMAP_PADDING

        # Create surface with alpha
        if self.surface is None or self.surface.get_size() != (minimap_w, minimap_h):
            self.surface = pygame.Surface((minimap_w, minimap_h), pygame.SRCALPHA)

        self.surface.fill(MINIMAP_BG_COLOR)

        # Draw border
        pygame.draw.rect(
            self.surface,
            MINIMAP_BORDER_COLOR,
            pygame.Rect(0, 0, minimap_w, minimap_h),
            MINIMAP_BORDER,
        )

        # Build room position lookup (grid coords -> minimap pixel coords)
        room_positions = {}
        for room in world.all_rooms:
            mx = MINIMAP_PADDING + (room.grid_x - minx) * self.config.scale
            my = MINIMAP_PADDING + (room.grid_y - miny) * self.config.scale
            room_positions[(room.grid_x, room.grid_y)] = (mx, my)

        # Draw connections first (under rooms)
        if self.config.show_connections:
            self._draw_connections(room_positions, world)

        # Draw rooms
        for room in world.all_rooms:
            mx, my = room_positions[(room.grid_x, room.grid_y)]
            self._draw_room(room, mx, my, room == current_room_coords)

        # Draw player position
        if self.config.show_player and current_room_coords:
            self._draw_player(player_pos, current_room_coords, room_positions, megamap, minx, miny)

        # Blit to screen
        screen.blit(self.surface, self.config.position)

    def _draw_room(self, room: RoomNode, mx: int, my: int, is_current: bool) -> None:
        """
        Draw a single room on the minimap

        Args:
            room: Room to draw
            mx, my: Position on minimap
            is_current: Whether this is the current room
        """
        # Get room color based on type
        color = ROOM_COLORS.get(room.room_type, (100, 100, 100))

        # Draw room rectangle
        room_rect = pygame.Rect(mx, my, self.config.scale, self.config.scale)
        pygame.draw.rect(self.surface, color, room_rect)

        # Highlight current room
        if is_current and self.config.highlight_current:
            pygame.draw.rect(self.surface, CURRENT_ROOM_COLOR, room_rect, CURRENT_ROOM_THICKNESS)

    def _draw_connections(
        self, room_positions: dict[tuple[int, int], tuple[int, int]], world: World
    ) -> None:
        """
        Draw connection lines between adjacent rooms

        Args:
            room_positions: Map of room coords -> minimap position
            world: World with room graph
        """
        drawn_connections = set()

        for room in world.all_rooms:
            room_coords = (room.grid_x, room.grid_y)
            if room_coords not in room_positions:
                continue

            mx1, my1 = room_positions[room_coords]
            center_x1 = mx1 + self.config.scale // 2
            center_y1 = my1 + self.config.scale // 2

            # Draw line to each neighbor
            for neighbor_coords in room.neighbors:
                if neighbor_coords not in room_positions:
                    continue

                # Avoid drawing same connection twice
                connection = tuple(sorted([room_coords, neighbor_coords]))
                if connection in drawn_connections:
                    continue
                drawn_connections.add(connection)

                mx2, my2 = room_positions[neighbor_coords]
                center_x2 = mx2 + self.config.scale // 2
                center_y2 = my2 + self.config.scale // 2

                pygame.draw.line(
                    self.surface,
                    CONNECTION_COLOR,
                    (center_x1, center_y1),
                    (center_x2, center_y2),
                    CONNECTION_THICKNESS,
                )

    def _draw_player(
        self,
        player_pos: tuple[float, float],
        current_room_coords: tuple[int, int],
        room_positions: dict[tuple[int, int], tuple[int, int]],
        megamap: Megamap,
        minx: int,
        miny: int,
    ) -> None:
        """
        Draw player position indicator on minimap

        Args:
            player_pos: Player position in world pixels
            current_room_coords: Current room coordinates
            room_positions: Map of room coords -> minimap position
            megamap: Megamap for room position calculations
            minx, miny: World bounds
        """
        if current_room_coords not in room_positions:
            return

        # Get current room's minimap position
        mx, my = room_positions[current_room_coords]

        # Get current room's world position (in pixels)
        if current_room_coords not in megamap.room_positions:
            return

        room_world_px, room_world_py = megamap.room_positions[current_room_coords]

        # Player position relative to room (in pixels)
        player_x, player_y = player_pos
        rel_x = player_x - room_world_px
        rel_y = player_y - room_world_py

        # Room size in pixels (160 tiles * 32 pixels/tile = 5120 pixels)
        room_pixel_w = 160 * 32
        room_pixel_h = 160 * 32

        # Normalize to 0.0-1.0 range
        norm_x = max(0.0, min(1.0, rel_x / room_pixel_w))
        norm_y = max(0.0, min(1.0, rel_y / room_pixel_h))

        # Convert to minimap coordinates
        dot_x = int(mx + norm_x * self.config.scale)
        dot_y = int(my + norm_y * self.config.scale)

        # Draw player dot
        pygame.draw.circle(self.surface, PLAYER_DOT_COLOR, (dot_x, dot_y), PLAYER_DOT_SIZE)


def get_current_room_coords(megamap: Megamap, player_pos: tuple[float, float]) -> tuple[int, int]:
    """
    Get the room coordinates containing the player

    Args:
        megamap: Megamap with room positions
        player_pos: Player position in pixels (x, y)

    Returns:
        Room coordinates (grid_x, grid_y)
    """
    from systems.megamap import get_room_at_position

    return get_room_at_position(megamap, player_pos[0], player_pos[1])
