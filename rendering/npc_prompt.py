"""
NPC Interaction Prompt Renderer

Displays "Press E to talk" prompt above NPCs when player is in interaction range.
"""


import pygame

from entities.npc import NPCManager


class NPCPromptRenderer:
    """Renders interaction prompts above nearby NPCs."""

    def __init__(self, font_size: int = 16):
        """
        Initialize prompt renderer.

        Args:
            font_size: Font size for prompt text
        """
        self.font = pygame.font.Font(None, font_size)
        self.prompt_color = (255, 255, 255)  # White text
        self.background_color = (0, 0, 0, 180)  # Semi-transparent black
        self.border_color = (100, 100, 255)  # Light blue border
        self.padding = 6
        self.offset_y = 40  # Distance above NPC to show prompt

    def render(
        self,
        surface: pygame.Surface,
        npc_manager: NPCManager,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        camera_x: float,
        camera_y: float,
    ):
        """
        Render interaction prompts for nearby NPCs.

        Args:
            surface: Surface to render on
            npc_manager: NPC manager instance
            player_x: Player X position (world space)
            player_y: Player Y position (world space)
            player_width: Player width
            player_height: Player height
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        # Find nearby NPCs
        nearby_npcs = npc_manager.get_nearby_npcs(
            player_x=player_x,
            player_y=player_y,
            player_width=player_width,
            player_height=player_height,
        )

        # Show prompt for first nearby NPC
        if nearby_npcs:
            nearby_npc = nearby_npcs[0]
        else:
            nearby_npc = None

        if nearby_npc and nearby_npc.is_interactable:
            # Get NPC definition
            npc_def = npc_manager.get_npc_definition(nearby_npc.npc_id)
            if npc_def is None:
                return

            # Determine prompt text based on NPC type
            prompt_text = self._get_prompt_text(npc_def.npc_type)

            # Render prompt above NPC
            self._render_prompt(
                surface=surface,
                text=prompt_text,
                npc_x=nearby_npc.x,
                npc_y=nearby_npc.y,
                npc_width=nearby_npc.width,
                camera_x=camera_x,
                camera_y=camera_y,
            )

    def _get_prompt_text(self, npc_type) -> str:
        """Get appropriate prompt text for NPC type."""
        from entities.npc import NPCType

        if npc_type == NPCType.SHOP:
            return "Press E to Shop"
        elif npc_type == NPCType.MISSION_GIVER:
            return "Press E to Talk"
        elif npc_type == NPCType.LORE:
            return "Press E to Talk"
        elif npc_type == NPCType.TUTORIAL:
            return "Press E for Help"
        else:
            return "Press E to Interact"

    def _render_prompt(
        self,
        surface: pygame.Surface,
        text: str,
        npc_x: float,
        npc_y: float,
        npc_width: int,
        camera_x: float,
        camera_y: float,
    ):
        """Render prompt box above NPC."""
        # Render text
        text_surface = self.font.render(text, True, self.prompt_color)
        text_rect = text_surface.get_rect()

        # Calculate screen position (centered above NPC)
        npc_center_x = npc_x + npc_width / 2
        screen_x = npc_center_x - camera_x - text_rect.width / 2
        screen_y = npc_y - camera_y - self.offset_y

        # Background box dimensions
        box_width = text_rect.width + self.padding * 2
        box_height = text_rect.height + self.padding * 2
        box_x = screen_x - self.padding
        box_y = screen_y - self.padding

        # Create background surface with alpha
        background = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        background.fill(self.background_color)

        # Draw border
        pygame.draw.rect(background, self.border_color, (0, 0, box_width, box_height), 2)

        # Blit background and text
        surface.blit(background, (box_x, box_y))
        surface.blit(text_surface, (screen_x, screen_y))


class NPCIndicatorRenderer:
    """Renders visual indicators above NPCs (e.g., '!' for mission givers)."""

    def __init__(self, font_size: int = 24):
        """
        Initialize indicator renderer.

        Args:
            font_size: Font size for indicator icons
        """
        self.font = pygame.font.Font(None, font_size)
        self.offset_y = 60  # Distance above NPC to show indicator

    def render(
        self, surface: pygame.Surface, npc_manager: NPCManager, camera_x: float, camera_y: float
    ):
        """
        Render indicators above all NPCs.

        Args:
            surface: Surface to render on
            npc_manager: NPC manager instance
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        for npc in npc_manager.npcs:
            if not npc.is_interactable:
                continue

            # Get NPC definition
            npc_def = npc_manager.get_npc_definition(npc.npc_id)
            if npc_def is None:
                continue

            # Get indicator icon and color
            icon, color = self._get_indicator(npc_def.npc_type)

            if icon:
                # Render indicator above NPC
                self._render_indicator(
                    surface=surface,
                    icon=icon,
                    color=color,
                    npc_x=npc.x,
                    npc_y=npc.y,
                    npc_width=npc.width,
                    camera_x=camera_x,
                    camera_y=camera_y,
                )

    def _get_indicator(self, npc_type) -> tuple[str | None, tuple[int, int, int]]:
        """Get indicator icon and color for NPC type."""
        from entities.npc import NPCType

        if npc_type == NPCType.MISSION_GIVER:
            return "!", (255, 255, 0)  # Yellow exclamation mark
        elif npc_type == NPCType.SHOP:
            return "$", (50, 255, 50)  # Green dollar sign
        elif npc_type == NPCType.TUTORIAL:
            return "?", (100, 200, 255)  # Blue question mark
        else:
            return None, (255, 255, 255)

    def _render_indicator(
        self,
        surface: pygame.Surface,
        icon: str,
        color: tuple[int, int, int],
        npc_x: float,
        npc_y: float,
        npc_width: int,
        camera_x: float,
        camera_y: float,
    ):
        """Render indicator icon above NPC."""
        # Render icon
        icon_surface = self.font.render(icon, True, color)
        icon_rect = icon_surface.get_rect()

        # Calculate screen position (centered above NPC)
        npc_center_x = npc_x + npc_width / 2
        screen_x = npc_center_x - camera_x - icon_rect.width / 2
        screen_y = npc_y - camera_y - self.offset_y

        # Blit icon
        surface.blit(icon_surface, (screen_x, screen_y))
