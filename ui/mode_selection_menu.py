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

    _ITEM_SPACING = 36
    _START_Y = 190
    _BOTTOM_RESERVED = 100

    def __init__(self, screen_width: int, screen_height: int, mission_registry):
        super().__init__("SELECT MISSION (PLAYTEST)", screen_width, screen_height)

        self.mission_registry = mission_registry
        self.selected_mission: str | None = None
        self.scroll_offset = 0

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

    def _visible_count(self) -> int:
        available = self.screen_height - self._START_Y - self._BOTTOM_RESERVED
        return max(1, available // self._ITEM_SPACING)

    def _clamp_scroll(self):
        visible = self._visible_count()
        max_offset = max(0, len(self.items) - visible)
        self.scroll_offset = max(0, min(self.scroll_offset, max_offset))
        # Keep selected item in view
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible:
            self.scroll_offset = self.selected_index - visible + 1

    def navigate_up(self):
        super().navigate_up()
        self._clamp_scroll()

    def navigate_down(self):
        super().navigate_down()
        self._clamp_scroll()

    def render(self, surface: pygame.Surface):
        """Render mission selector with scrolling."""
        import pygame as _pg

        # Background overlay
        overlay = _pg.Surface((self.screen_width, self.screen_height), _pg.SRCALPHA)
        overlay.fill(self.bg_color)
        surface.blit(overlay, (0, 0))

        # Title
        shadow_surf = self.title_font.render(self.title, True, (0, 0, 0))
        title_surf = self.title_font.render(self.title, True, self.title_color)
        surface.blit(shadow_surf, shadow_surf.get_rect(centerx=self.screen_width // 2 + 2, y=102))
        surface.blit(title_surf, title_surf.get_rect(centerx=self.screen_width // 2, y=100))

        visible = self._visible_count()
        end = min(self.scroll_offset + visible, len(self.items))

        for i in range(self.scroll_offset, end):
            item = self.items[i]
            screen_row = i - self.scroll_offset
            item_y = self._START_Y + screen_row * self._ITEM_SPACING

            if not item.enabled:
                color = self.disabled_color
            elif i == self.selected_index:
                color = self.selected_color
            else:
                color = self.item_color

            item_surf = self.item_font.render(item.label, True, color)
            item_rect = item_surf.get_rect(centerx=self.screen_width // 2, y=item_y)

            if i == self.selected_index and item.enabled:
                indicator = self.item_font.render(">", True, self.selected_color)
                surface.blit(indicator, indicator.get_rect(
                    right=item_rect.left - 12, centery=item_rect.centery
                ))

            surface.blit(item_surf, item_rect)

        # Scroll indicators
        if self.scroll_offset > 0:
            up_surf = self.small_font.render("▲ more above", True, (180, 180, 200))
            surface.blit(up_surf, up_surf.get_rect(centerx=self.screen_width // 2, y=self._START_Y - 22))
        if self.scroll_offset + visible < len(self.items):
            down_surf = self.small_font.render("▼ more below", True, (180, 180, 200))
            surface.blit(down_surf, down_surf.get_rect(
                centerx=self.screen_width // 2,
                y=self._START_Y + visible * self._ITEM_SPACING + 4,
            ))

        # Mission detail line for currently highlighted item
        if self.selected_index < len(self.items):
            item = self.items[self.selected_index]
            if item.enabled and ":" in item.label:
                mission_id = item.label.strip().split(":")[0]
                mission = self.mission_registry.get_mission(mission_id)
                if mission:
                    info = f"Difficulty: {mission.difficulty} | Rooms: {mission.room_count} | Shape: {mission.shape}"
                    info_surf = self.small_font.render(info, True, (150, 150, 170))
                    surface.blit(info_surf, info_surf.get_rect(
                        centerx=self.screen_width // 2, bottom=self.screen_height - 50
                    ))

        hint = "Arrow Keys: Navigate | Enter: Select | ESC: Back"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        surface.blit(hint_surf, hint_surf.get_rect(
            centerx=self.screen_width // 2, bottom=self.screen_height - 20
        ))
