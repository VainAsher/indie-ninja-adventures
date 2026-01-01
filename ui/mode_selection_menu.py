"""
Game Mode Selection Menu - Choose between Campaign, Arcade, and Playtest

Displayed after clicking "Start Game" on main menu.

Version: v0.6.0
"""

import pygame

from ui.menu_system import BaseMenu, MenuAction


class GameModeSelectionMenu(BaseMenu):
    """
    Game mode selection menu

    Options:
    - Campaign Mode: Story progression with hub world and missions
    - Arcade Mode: Infinite procedural generation
    - Playtest Mode: Mission selector for testing
    - Back: Return to main menu
    """

    def __init__(self, screen_width: int, screen_height: int):
        super().__init__("SELECT GAME MODE", screen_width, screen_height)

        # Custom menu actions for each mode
        self.selected_mode: str | None = None

        # Add menu items
        self.add_item(
            "Campaign Mode", MenuAction.NONE, callback=lambda: self._select_mode("campaign")
        )
        self.add_item("Arcade Mode", MenuAction.NONE, callback=lambda: self._select_mode("arcade"))
        self.add_item(
            "Playtest Mode", MenuAction.NONE, callback=lambda: self._select_mode("playtest")
        )
        self.add_item("Back", MenuAction.BACK)

    def _select_mode(self, mode: str):
        """Store selected mode"""
        self.selected_mode = mode

    def get_selected_mode(self) -> str | None:
        """Get and clear selected mode"""
        mode = self.selected_mode
        self.selected_mode = None
        return mode

    def render(self, surface: pygame.Surface):
        """Render mode selection menu with descriptions"""
        super().render(surface)

        # Mode descriptions
        descriptions = {
            0: "Story progression • Hub world • Mission-based gameplay",
            1: "Infinite procedural levels • Classic mode • No story",
            2: "Mission selector • Testing mode • Developer access",
        }

        # Draw description for selected mode
        if self.selected_index in descriptions:
            desc = descriptions[self.selected_index]
            desc_surf = self.small_font.render(desc, True, (150, 150, 170))
            desc_rect = desc_surf.get_rect(centerx=self.screen_width // 2, y=500)
            surface.blit(desc_surf, desc_rect)

        # Controls hint
        hint = "Use Arrow Keys to navigate, Enter to select"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_width // 2, bottom=self.screen_height - 20
        )
        surface.blit(hint_surf, hint_rect)


class MissionSelectorMenu(BaseMenu):
    """
    Mission selector menu for playtest mode

    Shows all 25 missions organized by region for quick testing access.
    """

    def __init__(self, screen_width: int, screen_height: int, mission_registry):
        super().__init__("SELECT MISSION (PLAYTEST)", screen_width, screen_height)

        self.mission_registry = mission_registry
        self.selected_mission: str | None = None

        # Build mission list organized by region
        self._build_mission_list()

    def _build_mission_list(self):
        """Build mission list from registry"""
        regions = self.mission_registry.get_all_regions()

        for region in sorted(regions):
            missions = self.mission_registry.get_missions_in_region(region)

            # Add region header (disabled item)
            region_label = f"--- {region.upper()} ---"
            self.add_item(region_label, MenuAction.NONE, enabled=False)

            # Add missions for this region
            for mission in sorted(missions, key=lambda m: m.mission_id):
                mission_label = f"  {mission.mission_id}: {mission.mission_name}"
                self.add_item(
                    mission_label,
                    MenuAction.NONE,
                    callback=lambda m=mission.mission_id: self._select_mission(m),
                )

        # Add back button
        self.add_item("", MenuAction.NONE, enabled=False)  # Spacer
        self.add_item("Back", MenuAction.BACK)

    def _select_mission(self, mission_id: str):
        """Store selected mission"""
        self.selected_mission = mission_id

    def get_selected_mission(self) -> str | None:
        """Get and clear selected mission"""
        mission = self.selected_mission
        self.selected_mission = None
        return mission

    def render(self, surface: pygame.Surface):
        """Render mission selector with scrolling support"""
        super().render(surface)

        # Show selected mission details if hovering over a mission
        if self.selected_index < len(self.items):
            item = self.items[self.selected_index]
            if item.enabled and ":" in item.label:
                # Extract mission_id from label
                mission_id = item.label.strip().split(":")[0]
                mission = self.mission_registry.get_mission(mission_id)

                if mission:
                    # Show mission info at bottom
                    info = f"Difficulty: {mission.difficulty} | Rooms: {mission.room_count} | Shape: {mission.shape}"
                    info_surf = self.small_font.render(info, True, (150, 150, 170))
                    info_rect = info_surf.get_rect(
                        centerx=self.screen_width // 2, bottom=self.screen_height - 50
                    )
                    surface.blit(info_surf, info_rect)

        # Controls hint
        hint = "Arrow Keys: Navigate | Enter: Select | ESC: Back"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_width // 2, bottom=self.screen_height - 20
        )
        surface.blit(hint_surf, hint_rect)
