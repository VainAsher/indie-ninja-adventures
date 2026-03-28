"""
Menu System - UI menus for game navigation

Provides main menu, pause menu, and settings menu with keyboard navigation.

Architecture:
- BaseMenu: Abstract base for all menus
- MainMenu: Game start screen
- PauseMenu: In-game pause overlay
- SettingsMenu: Options and configuration
"""

from collections.abc import Callable
from dataclasses import dataclass
import math
from enum import Enum

import pygame

from utils.resource_path import get_resource_path

class MenuAction(Enum):
    """Menu action results"""

    NONE = "none"
    CONTINUE = "continue"
    START_GAME = "start_game"
    RESUME_GAME = "resume_game"
    QUIT_TO_MENU = "quit_to_menu"
    QUIT_GAME = "quit_game"
    OPEN_SETTINGS = "open_settings"
    BACK = "back"


@dataclass
class MenuItem:
    """Menu item with label and action"""

    label: str
    action: MenuAction
    callback: Callable | None = None
    enabled: bool = True


class BaseMenu:
    """
    Abstract base class for all menus

    Features:
    - Keyboard navigation (up/down arrows)
    - Enter to select
    - ESC to back/cancel
    - Visual highlighting
    """

    def __init__(self, title: str, screen_width: int, screen_height: int):
        """
        Initialize base menu

        Args:
            title: Menu title text
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.title = title
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.items: list[MenuItem] = []
        self.selected_index = 0

        # Fonts
        self.title_font = pygame.font.SysFont("impact", 60, bold=True)
        self.item_font = pygame.font.SysFont("consolas", 32)
        self.small_font = pygame.font.SysFont("consolas", 20)

        # Colors
        self.bg_color = (10, 10, 20, 200)  # Semi-transparent dark
        self.title_color = (255, 215, 0)  # Gold
        self.item_color = (200, 200, 220)  # Light gray
        self.selected_color = (255, 255, 100)  # Bright yellow
        self.disabled_color = (100, 100, 120)  # Dark gray

    def add_item(
        self,
        label: str,
        action: MenuAction,
        callback: Callable | None = None,
        enabled: bool = True,
    ):
        """Add menu item"""
        self.items.append(MenuItem(label, action, callback, enabled))

    def handle_input(self, keys_pressed: dict[int, bool]) -> MenuAction:
        """
        Handle keyboard input for menu navigation

        Args:
            keys_pressed: Dict of key states (from pygame.key.get_pressed())

        Returns:
            MenuAction if item selected, MenuAction.NONE otherwise
        """
        # Check for key presses (debounced via external logic)
        # This should be called once per frame with actual key press events

        return MenuAction.NONE

    def navigate_up(self):
        """Move selection up"""
        if len(self.items) == 0:
            return

        # Find previous enabled item
        for _ in range(len(self.items)):
            self.selected_index = (self.selected_index - 1) % len(self.items)
            if self.items[self.selected_index].enabled:
                break

    def navigate_down(self):
        """Move selection down"""
        if len(self.items) == 0:
            return

        # Find next enabled item
        for _ in range(len(self.items)):
            self.selected_index = (self.selected_index + 1) % len(self.items)
            if self.items[self.selected_index].enabled:
                break

    def select_current(self) -> MenuAction:
        """
        Select current menu item

        Returns:
            MenuAction from selected item
        """
        if len(self.items) == 0:
            return MenuAction.NONE

        item = self.items[self.selected_index]
        if not item.enabled:
            return MenuAction.NONE

        # Call callback if provided
        if item.callback:
            item.callback()

        return item.action

    def render(self, surface: pygame.Surface):
        """
        Render menu to surface

        Args:
            surface: Surface to render on
        """
        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill(self.bg_color)
        surface.blit(overlay, (0, 0))

        # Title
        title_color = (255, 215, 0)  # Gold
        title_surf = self.title_font.render(self.title, True, self.title_color)
        title_rect = title_surf.get_rect(centerx=self.screen_width // 2, y=100)

        # Add a black shadow to the text
        shadow_color = (0, 0, 0)  # Black
        shadow_offset = (2, 2)  # Offset for the shadow
        shadow_rect = title_surf.get_rect(centerx=self.screen_width // 2 + shadow_offset[0], y=100 + shadow_offset[1])
        surface.blit(self.title_font.render(self.title, True, shadow_color), shadow_rect)
        surface.blit(title_surf, title_rect)

        # Menu items
        start_y = 250
        item_spacing = 60

        for i, item in enumerate(self.items):
            # Determine color
            if not item.enabled:
                color = self.disabled_color
            elif i == self.selected_index:
                color = self.selected_color
            else:
                color = self.item_color

            # Render item
            item_surf = self.item_font.render(item.label, True, color)
            item_rect = item_surf.get_rect(
                centerx=self.screen_width // 2, y=start_y + i * item_spacing
            )

            # Selection indicator
            if i == self.selected_index and item.enabled:
                indicator = self.item_font.render(">", True, self.selected_color)
                indicator_rect = indicator.get_rect(
                    right=item_rect.left - 20, centery=item_rect.centery
                )
                surface.blit(indicator, indicator_rect)

            surface.blit(item_surf, item_rect)


class MainMenu(BaseMenu):
    """
    Main menu shown at game start

    Options:
    - Start Game
    - Settings
    - Quit
    """

    def __init__(self, screen_width: int, screen_height: int):
        super().__init__("NINJA DASH", screen_width, screen_height)

        # Fully opaque background for launch menu (obscures gameplay)
        self.bg_color = (10, 10, 20, 255)

        self.add_item("Start Game", MenuAction.START_GAME)
        self.add_item("Settings", MenuAction.OPEN_SETTINGS)
        self.add_item("Quit", MenuAction.QUIT_GAME)

    def render(self, surface: pygame.Surface):
        """Render main menu with subtitle"""
        super().render(surface)

        # Subtitle
        subtitle = "Vain Asher Gaming's: Indie Ninja Adventures"
        subtitle_surf = self.small_font.render(subtitle, True, (150, 150, 170))
        subtitle_rect = subtitle_surf.get_rect(centerx=self.screen_width // 2, y=160)
        surface.blit(subtitle_surf, subtitle_rect)

        # Version
        version = "v0.7.0"
        version_surf = self.small_font.render(version, True, (100, 100, 120))
        version_rect = version_surf.get_rect(
            right=self.screen_width - 20, bottom=self.screen_height - 20
        )
        surface.blit(version_surf, version_rect)

        # Controls hint
        hint = "Use Arrow Keys to navigate, Enter to select"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_width // 2, bottom=self.screen_height - 20
        )
        surface.blit(hint_surf, hint_rect)


class LandingMenu(BaseMenu):
    """
    Featured landing page shown on launch before the main menu.
    """

    def __init__(self, screen_width: int, screen_height: int):
        super().__init__("INDIE NINJA ADVENTURES", screen_width, screen_height)

        self.add_item("Continue", MenuAction.CONTINUE)
        self._start_ms = pygame.time.get_ticks()

        self.title_font = pygame.font.SysFont("impact", 70, bold=True)
        self.subtitle_font = pygame.font.SysFont("consolas", 22)
        self.prompt_font = pygame.font.SysFont("consolas", 26, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 18)

        self._bg_image = None
        bg_path = get_resource_path("assets", "splash", "landing.png")
        if bg_path.exists():
            self._bg_image = pygame.image.load(str(bg_path)).convert()

    def render(self, surface: pygame.Surface):
        # Background image or solid fallback
        if self._bg_image:
            bg = pygame.transform.smoothscale(
                self._bg_image, (self.screen_width, self.screen_height)
            )
            surface.blit(bg, (0, 0))
        else:
            surface.fill((8, 10, 18))

        # Subtle dark overlay for text contrast
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        elapsed = (pygame.time.get_ticks() - self._start_ms) / 1000.0
        fade = min(1.0, elapsed / 1.2)

        # Title backing panel for readability
        panel_height = 180
        panel_y = 90
        panel = pygame.Surface((self.screen_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        surface.blit(panel, (0, panel_y))

        # Title block — per-character rendering with extra spacing for readability
        title_text = "INDIE NINJA ADVENTURES"
        title_color = (255, 235, 180)
        outline_color = (0, 0, 0)
        char_spacing = 3  # extra pixels between characters

        # Pre-render each character
        chars = [
            (self.title_font.render(ch, True, title_color),
             self.title_font.render(ch, True, outline_color))
            for ch in title_text
        ]
        total_w = sum(cs.get_width() for cs, _ in chars) + char_spacing * (len(chars) - 1)
        title_h = self.title_font.get_height()

        # Compose onto intermediate surface so fade works as one alpha op
        title_surf = pygame.Surface((total_w, title_h), pygame.SRCALPHA)
        cx = 0
        for cs, os_ in chars:
            w = cs.get_width()
            for odx, ody in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                title_surf.blit(os_, (cx + odx, ody))
            title_surf.blit(cs, (cx, 0))
            cx += w + char_spacing

        title_surf.set_alpha(int(255 * fade))
        title_rect = title_surf.get_rect(centerx=self.screen_width // 2, y=125)
        surface.blit(title_surf, title_rect)

        subtitle_text = "Vain Asher Gaming Presents"
        subtitle_shadow = self.subtitle_font.render(subtitle_text, True, (0, 0, 0))
        subtitle = self.subtitle_font.render(subtitle_text, True, (210, 210, 230))
        subtitle_shadow.set_alpha(int(160 * fade))
        subtitle.set_alpha(int(230 * fade))
        subtitle_rect = subtitle.get_rect(centerx=self.screen_width // 2, y=210)
        surface.blit(subtitle_shadow, (subtitle_rect.x + 1, subtitle_rect.y + 1))
        surface.blit(subtitle, subtitle_rect)

        tagline_text = "A fast, skill-based ninja platformer"
        tagline_shadow = self.small_font.render(tagline_text, True, (0, 0, 0))
        tagline = self.small_font.render(tagline_text, True, (170, 170, 190))
        tagline_shadow.set_alpha(int(120 * fade))
        tagline.set_alpha(int(210 * fade))
        tagline_rect = tagline.get_rect(centerx=self.screen_width // 2, y=250)
        surface.blit(tagline_shadow, (tagline_rect.x + 1, tagline_rect.y + 1))
        surface.blit(tagline, tagline_rect)

        # Press enter prompt (pulsing)
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() / 280.0)
        prompt_color = (200, 200, 220)
        prompt = self.prompt_font.render("Press Enter to Continue", True, prompt_color)
        prompt.set_alpha(int(255 * pulse))
        prompt_rect = prompt.get_rect(centerx=self.screen_width // 2, y=520)
        surface.blit(prompt, prompt_rect)

        # Footer hint
        hint = self.small_font.render("Menu navigation begins after continue", True, (120, 120, 140))
        hint_rect = hint.get_rect(centerx=self.screen_width // 2, y=560)
        surface.blit(hint, hint_rect)


class PauseMenu(BaseMenu):
    """
    Pause menu shown during gameplay

    Options:
    - Resume
    - Settings
    - Quit to Menu
    """

    def __init__(self, screen_width: int, screen_height: int):
        super().__init__("PAUSED", screen_width, screen_height)

        self.add_item("Resume", MenuAction.RESUME_GAME)
        self.add_item("Settings", MenuAction.OPEN_SETTINGS)
        self.add_item("Quit to Menu", MenuAction.QUIT_TO_MENU)

    def render(self, surface: pygame.Surface):
        """Render pause menu with hint"""
        super().render(surface)

        # Controls hint
        hint = "Press ESC to resume"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_width // 2, bottom=self.screen_height - 20
        )
        surface.blit(hint_surf, hint_rect)


class SettingsMenu(BaseMenu):
    """
    Settings menu for game configuration.

    Supports live toggles that apply immediately.
    """

    def __init__(self, screen_width: int, screen_height: int, settings=None, on_change=None):
        super().__init__("SETTINGS", screen_width, screen_height)

        self.settings = settings
        self.on_change = on_change

        self._smoothing_options = [
            (0.05, "Low"),
            (0.1, "Normal"),
            (0.2, "High"),
        ]

        self._build_items()

    def _get(self, key: str, default):
        if self.settings is None:
            return default
        return self.settings.get(key, default)

    def _set(self, key: str, value):
        if self.settings is None:
            return
        self.settings.set(key, value)
        self.settings.save()

    _SFX_VOL_STEPS = (0.0, 0.25, 0.5, 0.75, 1.0)
    _SFX_VOL_LABELS = ("Off", "25%", "50%", "75%", "100%")

    def _build_items(self):
        self.items = []
        self.selected_index = 0

        self._idx_shake = len(self.items)
        self.add_item(self._label_shake(), MenuAction.NONE, callback=self._toggle_shake)

        self._idx_particles = len(self.items)
        self.add_item(self._label_particles(), MenuAction.NONE, callback=self._toggle_particles)

        self._idx_smoothing = len(self.items)
        self.add_item(self._label_smoothing(), MenuAction.NONE, callback=self._cycle_smoothing)

        self._idx_fps = len(self.items)
        self.add_item(self._label_fps(), MenuAction.NONE, callback=self._toggle_fps)

        self._idx_sfx_vol = len(self.items)
        self.add_item(self._label_sfx_vol(), MenuAction.NONE, callback=self._cycle_sfx_vol)

        self._idx_fullscreen = len(self.items)
        self.add_item(self._label_fullscreen(), MenuAction.NONE, callback=self._toggle_fullscreen)

        self.add_item("Back", MenuAction.BACK)

    def _label_bool(self, label: str, value: bool) -> str:
        return f"{label}: {'On' if value else 'Off'}"

    def _label_shake(self) -> str:
        return self._label_bool("Screen Shake", bool(self._get("screenshake", True)))

    def _label_particles(self) -> str:
        return self._label_bool("Particles", bool(self._get("particles", True)))

    def _label_fps(self) -> str:
        return self._label_bool("Show FPS", bool(self._get("show_fps", False)))

    def _label_smoothing(self) -> str:
        value = float(self._get("camera_smoothing", 0.1))
        label = "Custom"
        for opt_value, opt_label in self._smoothing_options:
            if abs(opt_value - value) < 1e-6:
                label = opt_label
                break
        return f"Camera Smoothing: {label}"

    def _label_sfx_vol(self) -> str:
        val = float(self._get("volume_sfx", 0.8))
        closest = min(self._SFX_VOL_STEPS, key=lambda v: abs(v - val))
        label = self._SFX_VOL_LABELS[self._SFX_VOL_STEPS.index(closest)]
        return f"SFX Volume: {label}"

    def _cycle_sfx_vol(self):
        val = float(self._get("volume_sfx", 0.8))
        closest_idx = min(
            range(len(self._SFX_VOL_STEPS)),
            key=lambda i: abs(self._SFX_VOL_STEPS[i] - val),
        )
        next_idx = (closest_idx + 1) % len(self._SFX_VOL_STEPS)
        self._set("volume_sfx", self._SFX_VOL_STEPS[next_idx])
        self._refresh_labels()
        self._apply_changes()

    def _label_fullscreen(self) -> str:
        return self._label_bool("Fullscreen", bool(self._get("fullscreen", False)))

    def _toggle_fullscreen(self):
        current = bool(self._get("fullscreen", False))
        self._set("fullscreen", not current)
        self._refresh_labels()
        self._apply_changes()

    def _refresh_labels(self):
        self.items[self._idx_shake].label = self._label_shake()
        self.items[self._idx_particles].label = self._label_particles()
        self.items[self._idx_smoothing].label = self._label_smoothing()
        self.items[self._idx_fps].label = self._label_fps()
        self.items[self._idx_sfx_vol].label = self._label_sfx_vol()
        self.items[self._idx_fullscreen].label = self._label_fullscreen()

    def _apply_changes(self):
        if self.on_change:
            self.on_change()

    def _toggle_shake(self):
        current = bool(self._get("screenshake", True))
        self._set("screenshake", not current)
        self._refresh_labels()
        self._apply_changes()

    def _toggle_particles(self):
        current = bool(self._get("particles", True))
        self._set("particles", not current)
        self._refresh_labels()
        self._apply_changes()

    def _toggle_fps(self):
        current = bool(self._get("show_fps", False))
        self._set("show_fps", not current)
        self._refresh_labels()
        self._apply_changes()

    def _cycle_smoothing(self):
        current = float(self._get("camera_smoothing", 0.1))
        values = [v for v, _ in self._smoothing_options]
        try:
            idx = values.index(current)
        except ValueError:
            idx = 0
        next_idx = (idx + 1) % len(values)
        self._set("camera_smoothing", values[next_idx])
        self._refresh_labels()
        self._apply_changes()

    def render(self, surface: pygame.Surface):
        """Render settings menu with hint"""
        super().render(surface)

        hint = "Enter: Toggle | ESC: Back"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_width // 2, bottom=self.screen_height - 20
        )
        surface.blit(hint_surf, hint_rect)


class MenuManager:
    """
    Manages menu stack and transitions

    Features:
    - Menu stack (push/pop)
    - Input handling with debouncing
    - Rendering current menu
    """

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize menu manager

        Args:
            screen_width: Screen width
            screen_height: Screen height
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.menu_stack: list[BaseMenu] = []

        # Input debouncing
        self.last_up_press = 0
        self.last_down_press = 0
        self.last_enter_press = 0
        self.last_esc_press = 0
        self.debounce_delay = 200  # ms

    def push_menu(self, menu: BaseMenu):
        """Push menu onto stack"""
        self.menu_stack.append(menu)

    def pop_menu(self) -> BaseMenu | None:
        """Pop menu from stack"""
        if self.menu_stack:
            return self.menu_stack.pop()
        return None

    def clear_menus(self):
        """Clear all menus from stack"""
        self.menu_stack.clear()

    def get_current_menu(self) -> BaseMenu | None:
        """Get current (top) menu"""
        if self.menu_stack:
            return self.menu_stack[-1]
        return None

    def has_menu(self) -> bool:
        """Check if any menu is active"""
        return len(self.menu_stack) > 0

    def handle_input(
        self, keys: dict[int, bool], pressed_once: list[int] | None = None
    ) -> MenuAction:
        """
        Handle input for current menu with debouncing

        Args:
            keys: Key states from pygame.key.get_pressed() or CommandKeyView
            pressed_once: Optional list of key codes pressed this frame

        Returns:
            MenuAction from menu selection
        """
        menu = self.get_current_menu()
        if not menu:
            return MenuAction.NONE

        if pressed_once is not None:
            if pygame.K_UP in pressed_once or pygame.K_w in pressed_once:
                menu.navigate_up()
            if pygame.K_DOWN in pressed_once or pygame.K_s in pressed_once:
                menu.navigate_down()
            if pygame.K_RETURN in pressed_once:
                return menu.select_current()
            if pygame.K_ESCAPE in pressed_once:
                if isinstance(menu, PauseMenu):
                    return MenuAction.RESUME_GAME
                return MenuAction.BACK
            return MenuAction.NONE

        current_time = pygame.time.get_ticks()

        # Up arrow
        if keys[pygame.K_UP] and (current_time - self.last_up_press) > self.debounce_delay:
            menu.navigate_up()
            self.last_up_press = current_time

        # Down arrow
        if keys[pygame.K_DOWN] and (current_time - self.last_down_press) > self.debounce_delay:
            menu.navigate_down()
            self.last_down_press = current_time

        # Enter key
        if keys[pygame.K_RETURN] and (current_time - self.last_enter_press) > self.debounce_delay:
            self.last_enter_press = current_time
            return menu.select_current()

        # ESC key (back/cancel)
        if keys[pygame.K_ESCAPE] and (current_time - self.last_esc_press) > self.debounce_delay:
            self.last_esc_press = current_time

            # Special handling for pause menu - ESC resumes
            if isinstance(menu, PauseMenu):
                return MenuAction.RESUME_GAME
            # Other menus - ESC goes back
            else:
                return MenuAction.BACK

        return MenuAction.NONE

    def render(self, surface: pygame.Surface):
        """Render current menu"""
        menu = self.get_current_menu()
        if menu:
            menu.render(surface)
