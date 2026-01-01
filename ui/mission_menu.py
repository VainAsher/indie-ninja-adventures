"""
Mission Selection UI - Choose missions from NPC

Shows available missions with status, requirements, and rewards.
Displays when talking to mission giver NPCs in hub.

Version: v0.6.0 (Phase 6) - Simplified
"""

from dataclasses import dataclass

import pygame

# ============================================================
# Mission Status
# ============================================================


class MissionStatus:
    """Mission status indicators"""

    NOT_STARTED = "not_started"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LOCKED = "locked"


# ============================================================
# Mission Display Data
# ============================================================


@dataclass
class MissionDisplay:
    """Mission display information"""

    mission_id: str
    mission_name: str
    region: str
    status: str
    difficulty: int  # 1-5 stars
    objectives: list[str]
    requirements: list[str]
    rewards: list[str]
    best_time: float | None = None


# ============================================================
# Mission Menu UI
# ============================================================


class MissionMenuUI:
    """
    Mission selection menu UI.

    Features:
    - List of missions with status icons
    - Mission details panel
    - Requirements/rewards display
    - Accept/cancel buttons
    """

    def __init__(self, font_name: str = "consolas", font_size: int = 16):
        """Initialize mission menu UI"""
        self.font = pygame.font.SysFont(font_name, font_size)
        self.small_font = pygame.font.SysFont(font_name, 14)
        self.title_font = pygame.font.SysFont(font_name, 20, bold=True)
        self.large_font = pygame.font.SysFont(font_name, 24, bold=True)

        # Colors
        self.color_bg = (30, 30, 40, 230)
        self.color_panel = (40, 40, 50)
        self.color_selected = (110, 130, 170)
        self.color_border = (100, 100, 120)
        self.color_text = (220, 220, 230)
        self.color_available = (255, 215, 0)  # Gold
        self.color_completed = (80, 255, 80)  # Green
        self.color_locked = (150, 150, 150)  # Gray

        # Status icons
        self.status_icons = {
            MissionStatus.COMPLETED: "✓",
            MissionStatus.AVAILABLE: "!",
            MissionStatus.LOCKED: "🔒",
            MissionStatus.IN_PROGRESS: "⚡",
            MissionStatus.NOT_STARTED: " ",
        }

        # State
        self.open = False
        self.selected_index = 0
        self.missions: list[MissionDisplay] = []
        # Track previous command states to edge-detect during replay
        self._prev_up = False
        self._prev_down = False
        self._prev_confirm = False
        self._prev_back = False

    def show(self, missions: list[MissionDisplay]):
        """Show mission menu with missions"""
        self.open = True
        self.missions = missions
        self.selected_index = 0
        # Reset edge trackers on open
        self._prev_up = False
        self._prev_down = False
        self._prev_confirm = False
        self._prev_back = False

    def hide(self):
        """Hide mission menu"""
        self.open = False

    def is_open(self) -> bool:
        """Check if menu is open"""
        return self.open

    def draw(self, surface: pygame.Surface):
        """Draw mission menu"""
        if not self.open or not self.missions:
            return

        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Center panel
        panel_w = 800
        panel_h = 550
        panel_x = (screen_w - panel_w) // 2
        panel_y = (screen_h - panel_h) // 2

        # Draw background
        bg_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg_surf.fill(self.color_bg)
        surface.blit(bg_surf, (panel_x, panel_y))

        # Draw border
        pygame.draw.rect(
            surface,
            self.color_border,
            pygame.Rect(panel_x, panel_y, panel_w, panel_h),
            width=3,
            border_radius=8,
        )

        # Draw title
        title = "Select Mission"
        title_surf = self.title_font.render(title, True, self.color_text)
        surface.blit(title_surf, (panel_x + 20, panel_y + 15))

        # Split view: mission list (left) | details (right)
        list_w = 320
        list_x = panel_x + 20
        list_y = panel_y + 60

        details_x = panel_x + list_w + 40
        details_y = panel_y + 60

        # Draw mission list
        self._draw_mission_list(surface, list_x, list_y, list_w)

        # Draw mission details
        if 0 <= self.selected_index < len(self.missions):
            selected_mission = self.missions[self.selected_index]
            self._draw_mission_details(surface, details_x, details_y, selected_mission)

        # Draw action buttons
        self._draw_action_buttons(surface, panel_x, panel_y + panel_h - 60, panel_w)

        # Draw controls hint
        hint = "Arrow/WASD to select | Enter to accept | ESC to cancel"
        hint_surf = self.small_font.render(hint, True, (150, 150, 160))
        surface.blit(hint_surf, (panel_x + 20, panel_y + panel_h - 30))

    def _draw_mission_list(self, surface, x, y, width):
        """Draw scrollable mission list"""
        max_visible = 8
        item_height = 45
        total = len(self.missions)
        if total <= max_visible:
            start_index = 0
        else:
            start_index = max(0, min(self.selected_index - max_visible + 1, total - max_visible))
        visible = self.missions[start_index : start_index + max_visible]

        for i, mission in enumerate(visible):
            actual_index = start_index + i
            item_y = y + i * item_height

            # Highlight selected
            if actual_index == self.selected_index:
                highlight_rect = pygame.Rect(x - 5, item_y - 5, width + 10, item_height - 5)
                pygame.draw.rect(surface, self.color_selected, highlight_rect, border_radius=4)
                pygame.draw.rect(
                    surface, self.color_border, highlight_rect, width=2, border_radius=4
                )
                indicator = self.font.render(">", True, (255, 255, 210))
                surface.blit(indicator, (x - 18, item_y))

            # Status icon
            icon = self.status_icons.get(mission.status, " ")
            icon_color = self._get_status_color(mission.status)
            icon_surf = self.font.render(icon, True, icon_color)
            surface.blit(icon_surf, (x, item_y))

            # Mission name
            name_color = (255, 255, 255) if actual_index == self.selected_index else self.color_text
            name_surf = self.font.render(mission.mission_name, True, name_color)
            surface.blit(name_surf, (x + 30, item_y))

            # Difficulty stars
            stars = "★" * mission.difficulty
            stars_surf = self.small_font.render(stars, True, (255, 215, 0))
            surface.blit(stars_surf, (x + 30, item_y + 20))

    def _draw_mission_details(self, surface, x, y, mission: MissionDisplay):
        """Draw mission details panel"""
        panel_w = 420

        # Mission name
        name_surf = self.large_font.render(mission.mission_name, True, self.color_text)
        surface.blit(name_surf, (x, y))
        y += 35

        # Region
        region_text = f"Region: {mission.region.title()}"
        region_surf = self.font.render(region_text, True, (150, 200, 255))
        surface.blit(region_surf, (x, y))
        y += 30

        # Objectives
        obj_title = self.font.render("Objectives:", True, self.color_text)
        surface.blit(obj_title, (x, y))
        y += 25

        for objective in mission.objectives[:3]:  # Show max 3
            obj_text = f"  • {objective}"
            obj_surf = self.small_font.render(obj_text, True, (200, 200, 210))
            surface.blit(obj_surf, (x, y))
            y += 20

        y += 10

        # Requirements
        if mission.requirements:
            req_title = self.font.render("Requirements:", True, self.color_text)
            surface.blit(req_title, (x, y))
            y += 25

            for req in mission.requirements[:2]:  # Show max 2
                req_text = f"  • {req}"
                req_color = (
                    (255, 200, 100) if mission.status == MissionStatus.LOCKED else (200, 200, 210)
                )
                req_surf = self.small_font.render(req_text, True, req_color)
                surface.blit(req_surf, (x, y))
                y += 20

            y += 10

        # Rewards
        if mission.rewards:
            reward_title = self.font.render("Rewards:", True, self.color_text)
            surface.blit(reward_title, (x, y))
            y += 25

            for reward in mission.rewards[:3]:  # Show max 3
                reward_text = f"  • {reward}"
                reward_surf = self.small_font.render(reward_text, True, (100, 255, 150))
                surface.blit(reward_surf, (x, y))
                y += 20

        # Best time (if completed)
        if mission.best_time:
            y += 10
            time_text = f"Best Time: {mission.best_time:.1f}s"
            time_surf = self.font.render(time_text, True, self.color_completed)
            surface.blit(time_surf, (x, y))

    def _draw_action_buttons(self, surface, x, y, width):
        """Draw Accept/Cancel buttons"""
        button_w = 120
        button_h = 40
        button_spacing = 20

        # Calculate center position
        total_w = button_w * 2 + button_spacing
        start_x = x + (width - total_w) // 2

        # Accept button
        accept_rect = pygame.Rect(start_x, y, button_w, button_h)
        accept_enabled = (
            0 <= self.selected_index < len(self.missions)
            and self.missions[self.selected_index].status != MissionStatus.LOCKED
        )
        accept_color = (80, 120, 80) if accept_enabled else (50, 50, 60)

        pygame.draw.rect(surface, accept_color, accept_rect, border_radius=6)
        pygame.draw.rect(surface, self.color_border, accept_rect, width=2, border_radius=6)

        accept_text = self.font.render("Accept", True, self.color_text)
        surface.blit(
            accept_text,
            (
                accept_rect.centerx - accept_text.get_width() // 2,
                accept_rect.centery - accept_text.get_height() // 2,
            ),
        )

        # Cancel button
        cancel_rect = pygame.Rect(start_x + button_w + button_spacing, y, button_w, button_h)
        pygame.draw.rect(surface, (60, 60, 70), cancel_rect, border_radius=6)
        pygame.draw.rect(surface, self.color_border, cancel_rect, width=2, border_radius=6)

        cancel_text = self.font.render("Cancel", True, self.color_text)
        surface.blit(
            cancel_text,
            (
                cancel_rect.centerx - cancel_text.get_width() // 2,
                cancel_rect.centery - cancel_text.get_height() // 2,
            ),
        )

    def _get_status_color(self, status: str) -> tuple[int, int, int]:
        """Get color for mission status"""
        if status == MissionStatus.COMPLETED:
            return self.color_completed
        elif status == MissionStatus.AVAILABLE or status == MissionStatus.IN_PROGRESS:
            return self.color_available
        elif status == MissionStatus.LOCKED:
            return self.color_locked
        else:
            return self.color_text

    def handle_input(self, event: pygame.event.Event) -> str | None:
        """
        Handle input events.

        Args:
            event: Pygame event

        Returns:
            "accept" if mission accepted, "cancel" if cancelled, None otherwise
        """
        if not self.open:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = max(0, self.selected_index - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_index = min(len(self.missions) - 1, self.selected_index + 1)
            elif event.key == pygame.K_RETURN:
                # Accept mission (if available)
                if (
                    0 <= self.selected_index < len(self.missions)
                    and self.missions[self.selected_index].status != MissionStatus.LOCKED
                ):
                    return "accept"
            elif event.key == pygame.K_ESCAPE:
                return "cancel"

        return None

    def handle_command(self, command, pressed_once: list[int]) -> str | None:
        """
        Handle input from command-based replay pipeline.

        Args:
            command: InputCommand-like object with up/down/menu_confirm/menu_back
            pressed_once: List of key codes pressed this frame (debounced)

        Returns:
            "accept" if mission accepted, "cancel" if cancelled, None otherwise
        """
        if not self.open:
            return None

        # Edge-detect navigation/confirm/back for deterministic replay
        up_edge = (
            pygame.K_UP in pressed_once
            or pygame.K_w in pressed_once
            or (getattr(command, "up", False) and not self._prev_up)
        )
        down_edge = (
            pygame.K_DOWN in pressed_once
            or pygame.K_s in pressed_once
            or (getattr(command, "down", False) and not self._prev_down)
        )
        confirm_edge = pygame.K_RETURN in pressed_once or (
            getattr(command, "menu_confirm", False) and not self._prev_confirm
        )
        back_edge = pygame.K_ESCAPE in pressed_once or (
            getattr(command, "menu_back", False) and not self._prev_back
        )

        # Navigation (debounced)
        if up_edge:
            self.selected_index = max(0, self.selected_index - 1)
        elif down_edge:
            self.selected_index = min(len(self.missions) - 1, self.selected_index + 1)

        # Accept / cancel
        result = None
        if confirm_edge:
            if (
                0 <= self.selected_index < len(self.missions)
                and self.missions[self.selected_index].status != MissionStatus.LOCKED
            ):
                result = "accept"
        elif back_edge:
            result = "cancel"

        # Update edge trackers
        self._prev_up = getattr(command, "up", False)
        self._prev_down = getattr(command, "down", False)
        self._prev_confirm = getattr(command, "menu_confirm", False)
        self._prev_back = getattr(command, "menu_back", False)

        return result

    def get_selected_mission(self) -> MissionDisplay | None:
        """Get currently selected mission"""
        if 0 <= self.selected_index < len(self.missions):
            return self.missions[self.selected_index]
        return None


# ============================================================
# Helper Functions
# ============================================================


def create_mission_menu() -> MissionMenuUI:
    """Create a mission menu UI instance"""
    return MissionMenuUI()


def create_sample_missions() -> list[MissionDisplay]:
    """Create sample missions for testing"""
    return [
        MissionDisplay(
            mission_id="forest_1",
            mission_name="Forest Patrol",
            region="forest",
            status=MissionStatus.AVAILABLE,
            difficulty=1,
            objectives=["Defeat 5 goblins", "Collect 3 keys"],
            requirements=[],
            rewards=["50 Gold", "Double Jump Unlock"],
        ),
        MissionDisplay(
            mission_id="forest_2",
            mission_name="Ancient Ruins",
            region="forest",
            status=MissionStatus.LOCKED,
            difficulty=3,
            objectives=["Explore the ruins", "Defeat boss"],
            requirements=["Double Jump", "Forest Patrol complete"],
            rewards=["100 Gold", "Rare Sword"],
        ),
        MissionDisplay(
            mission_id="town_1",
            mission_name="Town Defense",
            region="town",
            status=MissionStatus.COMPLETED,
            difficulty=2,
            objectives=["Defeat enemy waves"],
            requirements=[],
            rewards=["75 Gold"],
            best_time=245.3,
        ),
    ]
