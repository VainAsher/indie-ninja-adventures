"""
Interactive developer console for DEV builds.

Provides in-game Python console overlay for live debugging and tweaking.
Toggle with backtick (`) key.
"""

from typing import Any

import pygame


class DevConsole:
    """
    In-game developer console with Python interpreter.

    Features:
    - Execute Python code in game context
    - Access to game objects (player, camera, etc.)
    - Command history
    - Visual overlay
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.visible = False
        self.input_text = ""
        self.command_history: list[str] = []
        self.history_index = -1
        self.output_lines: list[str] = []
        self.max_output_lines = 20

        # Context for code execution (populated by game)
        self.context: dict[str, Any] = {}

        # Font
        self.font: pygame.font.Font | None = None

    def toggle(self):
        """Toggle console visibility"""
        if not self.enabled:
            return
        self.visible = not self.visible
        if self.visible:
            self.input_text = ""

    def initialize_font(self):
        """Initialize font (call after pygame.init())"""
        if self.font is None:
            try:
                self.font = pygame.font.SysFont("consolas", 14)
            except Exception:
                # Fallback to default font if Consolas not available
                self.font = pygame.font.Font(None, 16)

    def set_context(self, **kwargs):
        """Set context variables for console execution"""
        self.context.update(kwargs)

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        """
        Handle keyboard input for console

        Returns:
            True if event was consumed, False otherwise
        """
        if not self.enabled or not self.visible:
            return False

        if event.key == pygame.K_RETURN:
            self._execute_command()
            return True
        elif event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
            return True
        elif event.key == pygame.K_UP:
            self._history_up()
            return True
        elif event.key == pygame.K_DOWN:
            self._history_down()
            return True
        elif event.key == pygame.K_ESCAPE:
            self.visible = False
            return True
        elif event.key == pygame.K_BACKQUOTE:
            # Don't consume the backtick that opened the console
            return False
        else:
            # Add character to input
            if event.unicode and event.unicode.isprintable() and event.unicode != "`":
                self.input_text += event.unicode
                return True

        return False

    def _execute_command(self):
        """Execute the current input as Python code"""
        if not self.input_text.strip():
            return

        # Add to history
        self.command_history.append(self.input_text)
        self.history_index = -1

        # Add input to output
        self.output_lines.append(f"> {self.input_text}")

        # Execute
        try:
            # Try eval first (for expressions)
            result = eval(self.input_text, {"__builtins__": __builtins__}, self.context)
            if result is not None:
                self.output_lines.append(str(result))
        except SyntaxError:
            # If eval fails, try exec (for statements)
            try:
                exec(self.input_text, {"__builtins__": __builtins__}, self.context)
                self.output_lines.append("OK")
            except Exception as e:
                self.output_lines.append(f"Error: {e}")
        except Exception as e:
            self.output_lines.append(f"Error: {e}")

        # Trim output lines
        if len(self.output_lines) > self.max_output_lines:
            self.output_lines = self.output_lines[-self.max_output_lines :]

        # Clear input
        self.input_text = ""

    def _history_up(self):
        """Navigate up in command history"""
        if not self.command_history:
            return
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_text = self.command_history[-(self.history_index + 1)]

    def _history_down(self):
        """Navigate down in command history"""
        if self.history_index > 0:
            self.history_index -= 1
            self.input_text = self.command_history[-(self.history_index + 1)]
        elif self.history_index == 0:
            self.history_index = -1
            self.input_text = ""

    def render(self, surface: pygame.Surface):
        """Render console overlay"""
        if not self.enabled or not self.visible:
            return

        if self.font is None:
            self.initialize_font()

        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Console dimensions
        console_h = 300
        console_w = screen_w - 40
        console_x = 20
        console_y = screen_h - console_h - 20

        # Background
        overlay = pygame.Surface((console_w, console_h))
        overlay.set_alpha(230)
        overlay.fill((20, 20, 30))
        surface.blit(overlay, (console_x, console_y))

        # Border
        pygame.draw.rect(
            surface, (100, 100, 150), pygame.Rect(console_x, console_y, console_w, console_h), 2
        )

        # Title
        title = self.font.render("Developer Console (ESC to close)", True, (150, 150, 200))
        surface.blit(title, (console_x + 10, console_y + 5))

        # Output lines
        output_y = console_y + 30
        for line in self.output_lines[-15:]:  # Show last 15 lines
            text_surf = self.font.render(line[:100], True, (200, 200, 220))  # Truncate long lines
            surface.blit(text_surf, (console_x + 10, output_y))
            output_y += 16

        # Input line
        input_y = console_y + console_h - 30
        pygame.draw.rect(
            surface, (40, 40, 50), pygame.Rect(console_x + 5, input_y, console_w - 10, 25)
        )

        # Input text with cursor
        input_display = f"> {self.input_text}_"
        input_surf = self.font.render(input_display, True, (255, 255, 255))
        surface.blit(input_surf, (console_x + 10, input_y + 5))

        # Help text
        help_y = console_y + console_h - 50
        help_text = "Available: player, camera, entities, physics, collision (type 'dir(player)' for attributes)"
        help_surf = self.font.render(help_text[:95], True, (120, 120, 140))
        surface.blit(help_surf, (console_x + 10, help_y))
