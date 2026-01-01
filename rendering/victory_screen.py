"""
Victory Screen - Level Completion UI

Displays victory message and level statistics when player completes a level.
"""

from typing import Any

import pygame


class VictoryScreen:
    """
    Renders the victory screen when level is completed.

    Features:
    - Victory message
    - Completion time
    - Collectibles found
    - Deaths counter
    - Continue prompt
    """

    def __init__(self, screen_width: int = 1280, screen_height: int = 720):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Colors
        self.bg_color = (0, 0, 0, 180)  # Semi-transparent black
        self.title_color = (255, 215, 0)  # Gold
        self.text_color = (230, 230, 255)  # Light blue-white
        self.highlight_color = (80, 255, 80)  # Green

        # Fonts (will be created when first needed)
        self.title_font: pygame.font.Font | None = None
        self.stat_font: pygame.font.Font | None = None
        self.prompt_font: pygame.font.Font | None = None

        # Animation
        self.show_time = 0.0
        self.fade_in_duration = 0.5  # seconds

    def _ensure_fonts(self):
        """Create fonts if not already created"""
        if self.title_font is None:
            try:
                self.title_font = pygame.font.Font(None, 72)  # Large title
                self.stat_font = pygame.font.Font(None, 36)  # Stats
                self.prompt_font = pygame.font.Font(None, 28)  # Prompt
            except Exception:
                # Fallback if font loading fails
                self.title_font = pygame.font.SysFont("arial", 72, bold=True)
                self.stat_font = pygame.font.SysFont("arial", 36)
                self.prompt_font = pygame.font.SysFont("arial", 28)

    def render(self, surface: pygame.Surface, stats: dict[str, Any], dt: float):
        """
        Render the victory screen.

        Args:
            surface: Surface to render on
            stats: Level statistics dict with keys:
                   - "time": completion time in seconds
                   - "collectibles": "found/total" string
                   - "deaths": death count
            dt: Delta time for animation
        """
        self._ensure_fonts()

        # Update animation
        self.show_time += dt
        alpha = min(255, int((self.show_time / self.fade_in_duration) * 180))

        # Create semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(alpha)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))

        # Only show text after fade-in starts
        if self.show_time < 0.2:
            return

        # Calculate center positions
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2

        # Title: "LEVEL COMPLETE!"
        title_text = self.title_font.render("LEVEL COMPLETE!", True, self.title_color)
        title_rect = title_text.get_rect(center=(center_x, center_y - 150))
        surface.blit(title_text, title_rect)

        # Stats
        y_offset = center_y - 50

        # Completion time
        time_val = stats.get("time", 0.0)
        minutes = int(time_val // 60)
        seconds = time_val % 60
        time_str = f"Time: {minutes:02d}:{seconds:05.2f}"
        time_text = self.stat_font.render(time_str, True, self.text_color)
        time_rect = time_text.get_rect(center=(center_x, y_offset))
        surface.blit(time_text, time_rect)

        y_offset += 50

        # Collectibles
        collectibles_str = f"Collectibles: {stats.get('collectibles', '0/0')}"
        collectibles_text = self.stat_font.render(collectibles_str, True, self.text_color)
        collectibles_rect = collectibles_text.get_rect(center=(center_x, y_offset))
        surface.blit(collectibles_text, collectibles_rect)

        y_offset += 50

        # Deaths
        deaths_val = stats.get("deaths", 0)
        deaths_str = f"Deaths: {deaths_val}"
        deaths_color = self.highlight_color if deaths_val == 0 else self.text_color
        deaths_text = self.stat_font.render(deaths_str, True, deaths_color)
        deaths_rect = deaths_text.get_rect(center=(center_x, y_offset))
        surface.blit(deaths_text, deaths_rect)

        # Perfect run message
        if deaths_val == 0 and stats.get("collectibles", "0/0") != "0/0":
            collectibles_parts = stats.get("collectibles", "0/0").split("/")
            if len(collectibles_parts) == 2 and collectibles_parts[0] == collectibles_parts[1]:
                y_offset += 50
                perfect_text = self.stat_font.render("PERFECT RUN!", True, self.highlight_color)
                perfect_rect = perfect_text.get_rect(center=(center_x, y_offset))
                surface.blit(perfect_text, perfect_rect)

        # Continue prompt (blinking)
        if self.show_time % 1.0 < 0.5:  # Blink every second
            y_offset += 80
            prompt_text = self.prompt_font.render(
                "Press SPACE for next level or ESC to quit", True, self.text_color
            )
            prompt_rect = prompt_text.get_rect(center=(center_x, y_offset))
            surface.blit(prompt_text, prompt_rect)

    def reset(self):
        """Reset animation state"""
        self.show_time = 0.0
