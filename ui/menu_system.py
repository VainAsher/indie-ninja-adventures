"""
Menu System - UI menus for game navigation

Provides main menu, pause menu, and settings menu with keyboard navigation.

Architecture:
- BaseMenu: Abstract base for all menus
- MainMenu: Game start screen
- PauseMenu: In-game pause overlay
- SettingsMenu: Options and configuration
"""

import pygame
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class MenuAction(Enum):
    """Menu action results"""
    NONE = "none"
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
    callback: Optional[Callable] = None
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
        self.items: List[MenuItem] = []
        self.selected_index = 0

        # Fonts
        self.title_font = pygame.font.SysFont("consolas", 48, bold=True)
        self.item_font = pygame.font.SysFont("consolas", 32)
        self.small_font = pygame.font.SysFont("consolas", 20)

        # Colors
        self.bg_color = (10, 10, 20, 200)  # Semi-transparent dark
        self.title_color = (255, 215, 0)  # Gold
        self.item_color = (200, 200, 220)  # Light gray
        self.selected_color = (255, 255, 100)  # Bright yellow
        self.disabled_color = (100, 100, 120)  # Dark gray

    def add_item(self, label: str, action: MenuAction, callback: Optional[Callable] = None, enabled: bool = True):
        """Add menu item"""
        self.items.append(MenuItem(label, action, callback, enabled))

    def handle_input(self, keys_pressed: Dict[int, bool]) -> MenuAction:
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
        title_surf = self.title_font.render(self.title, True, self.title_color)
        title_rect = title_surf.get_rect(centerx=self.screen_width // 2, y=100)
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
            item_rect = item_surf.get_rect(centerx=self.screen_width // 2, y=start_y + i * item_spacing)

            # Selection indicator
            if i == self.selected_index and item.enabled:
                indicator = self.item_font.render(">", True, self.selected_color)
                indicator_rect = indicator.get_rect(right=item_rect.left - 20, centery=item_rect.centery)
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
        version = "v0.5.0-dev"
        version_surf = self.small_font.render(version, True, (100, 100, 120))
        version_rect = version_surf.get_rect(right=self.screen_width - 20, bottom=self.screen_height - 20)
        surface.blit(version_surf, version_rect)

        # Controls hint
        hint = "Use Arrow Keys to navigate, Enter to select"
        hint_surf = self.small_font.render(hint, True, (120, 120, 140))
        hint_rect = hint_surf.get_rect(centerx=self.screen_width // 2, bottom=self.screen_height - 20)
        surface.blit(hint_surf, hint_rect)


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
        hint_rect = hint_surf.get_rect(centerx=self.screen_width // 2, bottom=self.screen_height - 20)
        surface.blit(hint_surf, hint_rect)


class SettingsMenu(BaseMenu):
    """
    Settings menu for game configuration

    Options:
    - Volume settings (placeholder)
    - Controls (placeholder)
    - Graphics (placeholder)
    - Back
    """

    def __init__(self, screen_width: int, screen_height: int):
        super().__init__("SETTINGS", screen_width, screen_height)

        # Placeholder items for future implementation
        self.add_item("Volume: 100%", MenuAction.NONE, enabled=False)
        self.add_item("Controls: Keyboard", MenuAction.NONE, enabled=False)
        self.add_item("Graphics: Normal", MenuAction.NONE, enabled=False)
        self.add_item("Back", MenuAction.BACK)

    def render(self, surface: pygame.Surface):
        """Render settings menu with note"""
        super().render(surface)

        # Note about placeholder
        note = "(Settings will be implemented in future update)"
        note_surf = self.small_font.render(note, True, (120, 120, 140))
        note_rect = note_surf.get_rect(centerx=self.screen_width // 2, y=200)
        surface.blit(note_surf, note_rect)


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
        self.menu_stack: List[BaseMenu] = []

        # Input debouncing
        self.last_up_press = 0
        self.last_down_press = 0
        self.last_enter_press = 0
        self.last_esc_press = 0
        self.debounce_delay = 200  # ms

    def push_menu(self, menu: BaseMenu):
        """Push menu onto stack"""
        self.menu_stack.append(menu)

    def pop_menu(self) -> Optional[BaseMenu]:
        """Pop menu from stack"""
        if self.menu_stack:
            return self.menu_stack.pop()
        return None

    def clear_menus(self):
        """Clear all menus from stack"""
        self.menu_stack.clear()

    def get_current_menu(self) -> Optional[BaseMenu]:
        """Get current (top) menu"""
        if self.menu_stack:
            return self.menu_stack[-1]
        return None

    def has_menu(self) -> bool:
        """Check if any menu is active"""
        return len(self.menu_stack) > 0

    def handle_input(self, keys: Dict[int, bool], pressed_once: Optional[List[int]] = None) -> MenuAction:
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
