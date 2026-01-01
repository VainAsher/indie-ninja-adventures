"""
Objective HUD - Displays mission objectives and progress

Shows current mission objectives with completion status.
Displays in top-right corner below navigation compass.

Version: v0.6.0 (Phase 6)
"""

from dataclasses import dataclass

import pygame

# ============================================================
# Objective Data
# ============================================================


@dataclass
class ObjectiveDisplay:
    """Objective display data"""

    description: str
    current: int = 0
    target: int = 0
    completed: bool = False
    objective_type: str = "generic"


# ============================================================
# Objective HUD Renderer
# ============================================================


class ObjectiveHUDRenderer:
    """
    Renders mission objectives on screen.

    Display format:
        Objectives:
          ✓ Collect 3 keys (3/3)
          ○ Kill all enemies (5/8)
          ○ Reach the shrine

    Features:
    - Color-coded objectives (yellow active, green complete)
    - Progress indicators for countable objectives
    - Checkmarks for completed objectives
    - Auto-fade when no objectives
    """

    def __init__(self, font_name: str = "consolas", font_size: int = 16):
        """
        Initialize objective HUD renderer.

        Args:
            font_name: Font name
            font_size: Font size
        """
        self.font = pygame.font.SysFont(font_name, font_size)
        self.small_font = pygame.font.SysFont(font_name, 14)
        self.title_font = pygame.font.SysFont(font_name, 18, bold=True)

        # Colors
        self.color_title = (200, 200, 220)
        self.color_active = (255, 215, 0)  # Gold
        self.color_complete = (80, 255, 80)  # Green
        self.color_locked = (150, 150, 150)  # Gray
        self.color_bg = (20, 20, 30, 200)  # Dark transparent
        self.color_border = (80, 80, 100)

        # Icons
        self.icon_complete = "✓"
        self.icon_active = "○"
        self.icon_locked = "🔒"

    def draw_objectives(
        self, surface: pygame.Surface, objectives: list[ObjectiveDisplay], show_title: bool = True
    ):
        """
        Draw objectives HUD.

        Args:
            surface: Surface to draw on
            objectives: List of objectives to display
            show_title: Show "Objectives" title
        """
        if not objectives:
            return

        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Position near top-center to avoid overlapping navigation UI
        panel_w = 260
        x = (screen_w - panel_w) // 2
        y = 20

        # Calculate panel height
        title_height = 25 if show_title else 0
        objective_height = 22
        total_height = title_height + len(objectives) * objective_height + 20

        # Draw background panel
        panel_h = total_height
        pygame.draw.rect(
            surface, self.color_bg, pygame.Rect(x - 10, y - 10, panel_w, panel_h), border_radius=8
        )
        pygame.draw.rect(
            surface,
            self.color_border,
            pygame.Rect(x - 10, y - 10, panel_w, panel_h),
            width=2,
            border_radius=8,
        )

        # Draw title
        if show_title:
            title_surf = self.title_font.render("Objectives", True, self.color_title)
            surface.blit(title_surf, (x, y))
            y += 25

        # Draw objectives
        for obj in objectives:
            self._draw_objective(surface, obj, x, y)
            y += objective_height

    def _draw_objective(self, surface: pygame.Surface, objective: ObjectiveDisplay, x: int, y: int):
        """Draw a single objective"""
        # Choose color and icon based on status
        if objective.completed:
            color = self.color_complete
            icon = self.icon_complete
        else:
            color = self.color_active
            icon = self.icon_active

        # Draw icon
        icon_surf = self.font.render(icon, True, color)
        surface.blit(icon_surf, (x, y))

        # Build objective text
        obj_text = objective.description

        # Add progress if applicable
        if objective.target > 0:
            progress_str = f" ({objective.current}/{objective.target})"
            obj_text += progress_str

        # Draw objective text
        text_surf = self.small_font.render(obj_text, True, color)
        surface.blit(text_surf, (x + 20, y + 2))

    def draw_objective_complete_popup(
        self, surface: pygame.Surface, objective_text: str, alpha: int = 255
    ):
        """
        Draw objective completion popup (center screen).

        Args:
            surface: Surface to draw on
            objective_text: Objective that was completed
            alpha: Alpha transparency (0-255)
        """
        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Center position
        x = screen_w // 2
        y = screen_h // 3

        # Draw text with gold color
        text = f"✓ {objective_text} Complete!"
        text_surf = self.title_font.render(text, True, self.color_complete)
        text_surf.set_alpha(alpha)

        # Draw background
        text_w = text_surf.get_width()
        text_h = text_surf.get_height()
        bg_rect = pygame.Rect(x - text_w // 2 - 20, y - text_h // 2 - 10, text_w + 40, text_h + 20)

        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(min(200, alpha))
        bg_surface.fill((20, 20, 30))
        surface.blit(bg_surface, bg_rect.topleft)

        # Draw border
        pygame.draw.rect(surface, self.color_complete, bg_rect, width=3, border_radius=8)

        # Draw text
        surface.blit(text_surf, (x - text_w // 2, y - text_h // 2))

    def draw_mission_complete(self, surface: pygame.Surface, alpha: int = 255):
        """
        Draw mission complete screen.

        Args:
            surface: Surface to draw on
            alpha: Alpha transparency
        """
        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Center position
        x = screen_w // 2
        y = screen_h // 2

        # Draw "Mission Complete!" text
        title = "MISSION COMPLETE!"
        title_surf = self.title_font.render(title, True, self.color_complete)
        title_surf.set_alpha(alpha)

        title_w = title_surf.get_width()
        title_h = title_surf.get_height()

        # Draw background
        bg_w = title_w + 60
        bg_h = title_h + 80
        bg_rect = pygame.Rect(x - bg_w // 2, y - bg_h // 2, bg_w, bg_h)

        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(min(220, alpha))
        bg_surface.fill((20, 20, 30))
        surface.blit(bg_surface, bg_rect.topleft)

        # Draw border
        pygame.draw.rect(surface, self.color_complete, bg_rect, width=4, border_radius=12)

        # Draw title
        surface.blit(title_surf, (x - title_w // 2, y - 30))

        # Draw "Press SPACE to continue" hint
        hint = "Press SPACE to continue"
        hint_surf = self.small_font.render(hint, True, self.color_title)
        hint_surf.set_alpha(alpha)
        hint_w = hint_surf.get_width()
        surface.blit(hint_surf, (x - hint_w // 2, y + 15))


# ============================================================
# Helper Functions
# ============================================================


def create_objective(
    description: str,
    current: int = 0,
    target: int = 0,
    completed: bool = False,
    objective_type: str = "generic",
) -> ObjectiveDisplay:
    """
    Create an objective display.

    Args:
        description: Objective description
        current: Current progress
        target: Target progress (0 for non-countable)
        completed: Whether completed
        objective_type: Type of objective

    Returns:
        ObjectiveDisplay
    """
    return ObjectiveDisplay(
        description=description,
        current=current,
        target=target,
        completed=completed,
        objective_type=objective_type,
    )


def create_kill_objective(enemy_count: int, killed: int = 0) -> ObjectiveDisplay:
    """Create kill enemies objective"""
    return ObjectiveDisplay(
        description="Defeat all enemies",
        current=killed,
        target=enemy_count,
        completed=(killed >= enemy_count),
        objective_type="kill_enemies",
    )


def create_collect_objective(item_name: str, count: int, collected: int = 0) -> ObjectiveDisplay:
    """Create collect items objective"""
    return ObjectiveDisplay(
        description=f"Collect {item_name}",
        current=collected,
        target=count,
        completed=(collected >= count),
        objective_type="collect",
    )


def create_reach_objective(location: str, reached: bool = False) -> ObjectiveDisplay:
    """Create reach location objective"""
    return ObjectiveDisplay(
        description=f"Reach {location}",
        current=1 if reached else 0,
        target=1,
        completed=reached,
        objective_type="reach",
    )


def create_boss_objective(boss_name: str, defeated: bool = False) -> ObjectiveDisplay:
    """Create defeat boss objective"""
    return ObjectiveDisplay(
        description=f"Defeat {boss_name}",
        current=1 if defeated else 0,
        target=1,
        completed=defeated,
        objective_type="boss",
    )
