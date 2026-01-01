"""
Portal System - Fast Travel Between Hubs and Missions

This module provides portal entities for hub navigation:
- Hub-to-hub portals (bidirectional)
- Hub-to-mission portals (one-way, return on completion)
- Visual effects (pulsing, colored)
- Interaction detection
- Travel event emission

Version: v0.6.0
"""

import math
from dataclasses import dataclass
from enum import Enum

import pygame

from core import EventBus


class PortalType(Enum):
    """Portal destination types"""

    HUB = "hub"  # Travel to another hub
    MISSION = "mission"  # Travel to mission (one-way)


@dataclass
class Portal:
    """
    Portal instance in the game world.

    Represents an active portal with position, destination, and state.
    """

    portal_id: str
    portal_type: PortalType
    destination_id: str  # Hub ID or mission ID
    x: float
    y: float
    width: int = 64
    height: int = 64

    # Visual properties
    color: tuple[int, int, int] = (100, 200, 255)  # Default blue
    pulse_speed: float = 2.0  # Oscillations per second
    pulse_timer: float = 0.0

    # Interaction
    interaction_radius: float = 48.0
    is_active: bool = True
    bidirectional: bool = True  # Can return through this portal

    # Lock state (for progression-gated portals)
    is_locked: bool = False
    unlock_requirements: list[str] = None  # List of required abilities/items

    def get_rect(self) -> pygame.Rect:
        """Get portal bounding box"""
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
            True if player can interact with this portal
        """
        if not self.is_active or self.is_locked:
            return False

        # Get player center
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        # Get portal center
        portal_center_x = self.x + self.width / 2
        portal_center_y = self.y + self.height / 2

        # Check distance
        dx = player_center_x - portal_center_x
        dy = player_center_y - portal_center_y
        distance = (dx * dx + dy * dy) ** 0.5

        return distance <= self.interaction_radius

    def update(self, dt: float):
        """
        Update portal state (animation).

        Args:
            dt: Delta time in seconds
        """
        if self.is_active:
            self.pulse_timer += dt * self.pulse_speed

    def get_pulse_alpha(self) -> float:
        """
        Get current pulse alpha (0.0-1.0) for visual effect.

        Returns:
            Alpha value for pulsing effect
        """
        # Sine wave oscillation
        return 0.5 + 0.5 * math.sin(self.pulse_timer * 2 * math.pi)

    def get_color_with_pulse(self) -> tuple[int, int, int, int]:
        """
        Get current color with pulse effect applied.

        Returns:
            RGBA color tuple
        """
        alpha = int(self.get_pulse_alpha() * 255)
        return (*self.color, alpha)


# ============================================================
# Portal Color Schemes
# ============================================================

PORTAL_COLORS = {
    "central": (200, 200, 200),  # Gray (neutral)
    "forest": (50, 200, 50),  # Green
    "town": (100, 150, 255),  # Blue
    "caves": (200, 100, 255),  # Purple
    "castle": (255, 100, 100),  # Red
    "sewer": (100, 255, 100),  # Lime (toxic)
    "mission": (255, 200, 50),  # Gold
}


# ============================================================
# Portal Events
# ============================================================


@dataclass
class PortalInteractionEvent:
    """Event emitted when player interacts with portal"""

    portal_id: str
    portal_type: PortalType
    destination_id: str
    player_id: int


@dataclass
class PortalTravelEvent:
    """Event emitted to initiate travel through portal"""

    portal_id: str
    destination_id: str
    portal_type: PortalType
    player_id: int


# ============================================================
# Portal Manager
# ============================================================


class PortalManager:
    """
    Manages portal instances and interactions.

    Handles portal spawning, updates, and travel initiation.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize portal manager.

        Args:
            event_bus: Event bus for emitting events
        """
        self.event_bus = event_bus
        self.portals: list[Portal] = []

    def spawn_portal(
        self,
        portal_id: str,
        portal_type: PortalType,
        destination_id: str,
        x: float,
        y: float,
        bidirectional: bool = True,
        color: tuple[int, int, int] | None = None,
    ) -> Portal:
        """
        Spawn a portal instance.

        Args:
            portal_id: Unique portal identifier
            portal_type: Type of portal (hub or mission)
            destination_id: Destination hub/mission ID
            x: World X position
            y: World Y position
            bidirectional: Can travel both ways
            color: Portal color (auto-determined if None)

        Returns:
            Portal instance
        """
        # Auto-determine color if not specified
        if color is None:
            # Try to extract region from destination_id
            for region_key in PORTAL_COLORS:
                if region_key in destination_id:
                    color = PORTAL_COLORS[region_key]
                    break
            if color is None:
                color = PORTAL_COLORS.get(
                    "mission" if portal_type == PortalType.MISSION else "central"
                )

        portal = Portal(
            portal_id=portal_id,
            portal_type=portal_type,
            destination_id=destination_id,
            x=x,
            y=y,
            color=color,
            bidirectional=bidirectional,
        )

        self.portals.append(portal)
        return portal

    def clear_portals(self):
        """Remove all portals (e.g., when changing hubs)"""
        self.portals.clear()

    def update(self, dt: float):
        """
        Update all portals.

        Args:
            dt: Delta time in seconds
        """
        for portal in self.portals:
            portal.update(dt)

    def check_interaction(
        self,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        player_id: int = 0,
    ) -> Portal | None:
        """
        Check if player can interact with any portal.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height
            player_id: Player ID

        Returns:
            Portal player can interact with, or None
        """
        for portal in self.portals:
            if portal.can_interact_with_player(player_x, player_y, player_width, player_height):
                return portal
        return None

    def interact_with_portal(self, portal: Portal, player_id: int = 0):
        """
        Interact with a portal (initiate travel).

        Emits travel event for game state to handle.

        Args:
            portal: Portal to interact with
            player_id: Player ID
        """
        # Emit interaction event
        self.event_bus.emit(
            PortalInteractionEvent(
                portal_id=portal.portal_id,
                portal_type=portal.portal_type,
                destination_id=portal.destination_id,
                player_id=player_id,
            )
        )

        # Emit travel event
        self.event_bus.emit(
            PortalTravelEvent(
                portal_id=portal.portal_id,
                destination_id=portal.destination_id,
                portal_type=portal.portal_type,
                player_id=player_id,
            )
        )

    def get_portal_by_id(self, portal_id: str) -> Portal | None:
        """Get portal by ID"""
        for portal in self.portals:
            if portal.portal_id == portal_id:
                return portal
        return None

    def lock_portal(self, portal_id: str, requirements: list[str]):
        """
        Lock a portal with requirements.

        Args:
            portal_id: Portal to lock
            requirements: List of required abilities/items
        """
        portal = self.get_portal_by_id(portal_id)
        if portal:
            portal.is_locked = True
            portal.unlock_requirements = requirements

    def unlock_portal(self, portal_id: str):
        """
        Unlock a portal.

        Args:
            portal_id: Portal to unlock
        """
        portal = self.get_portal_by_id(portal_id)
        if portal:
            portal.is_locked = False
            portal.unlock_requirements = None

    def check_portal_unlocked(
        self, portal_id: str, unlocked_abilities: set, owned_items: set
    ) -> bool:
        """
        Check if portal is unlocked for player.

        Args:
            portal_id: Portal to check
            unlocked_abilities: Player's unlocked abilities
            owned_items: Player's key items

        Returns:
            True if portal can be used
        """
        portal = self.get_portal_by_id(portal_id)
        if portal is None:
            return False

        if not portal.is_locked:
            return True

        if portal.unlock_requirements is None:
            return True

        # Check all requirements
        for req in portal.unlock_requirements:
            if req not in unlocked_abilities and req not in owned_items:
                return False

        return True

    def get_nearby_portals(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> list[Portal]:
        """
        Get all portals in interaction range of player.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            List of portals in range
        """
        nearby = []
        for portal in self.portals:
            if portal.can_interact_with_player(player_x, player_y, player_width, player_height):
                nearby.append(portal)
        return nearby


# ============================================================
# Portal Rendering Helper
# ============================================================


def draw_portal(surface: pygame.Surface, portal: Portal, camera_x: int, camera_y: int):
    """
    Draw a portal to the surface.

    Args:
        surface: Surface to draw on
        portal: Portal to draw
        camera_x: Camera X offset
        camera_y: Camera Y offset
    """
    # Calculate screen position
    screen_x = int(portal.x - camera_x)
    screen_y = int(portal.y - camera_y)

    # Get pulsing color
    color_with_alpha = portal.get_color_with_pulse()

    # Draw outer glow (larger circle, semi-transparent)
    glow_radius = int(portal.width / 2 * 1.5)
    glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
    glow_color = (*portal.color, int(color_with_alpha[3] * 0.3))
    pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
    surface.blit(
        glow_surface,
        (screen_x - glow_radius + portal.width // 2, screen_y - glow_radius + portal.height // 2),
    )

    # Draw main portal circle
    portal_radius = int(portal.width / 2)
    portal_center = (screen_x + portal_radius, screen_y + portal_radius)
    pygame.draw.circle(surface, color_with_alpha[:3], portal_center, portal_radius)

    # Draw inner highlight (smaller, brighter)
    highlight_radius = int(portal_radius * 0.6)
    highlight_alpha = int(color_with_alpha[3] * 1.2)
    highlight_color = tuple(min(c + 50, 255) for c in portal.color) + (highlight_alpha,)
    pygame.draw.circle(surface, highlight_color[:3], portal_center, highlight_radius)

    # Draw locked indicator
    if portal.is_locked:
        # Draw lock icon (simple representation)
        lock_color = (255, 50, 50)  # Red
        lock_size = portal_radius // 2
        lock_rect = pygame.Rect(
            screen_x + portal_radius - lock_size // 2,
            screen_y + portal_radius - lock_size // 2,
            lock_size,
            lock_size,
        )
        pygame.draw.rect(surface, lock_color, lock_rect, 3)
