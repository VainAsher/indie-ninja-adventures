"""
Dialogue UI - NPC Conversation Interface

Renders dialogue box at bottom of screen with:
- Speaker name
- Dialogue text (wrapped)
- Choice options (if available)
- Navigation hints

Version: v0.6.0
"""

import pygame

from game.dialogue_system import DialogueChoice, DialogueNode


class DialogueUI:
    """
    Renders dialogue interface at bottom of screen.

    Displays speaker, text, and choices with keyboard navigation.
    """

    def __init__(self, screen_width: int = 1280, screen_height: int = 720):
        """
        Initialize dialogue UI.

        Args:
            screen_width: Game screen width
            screen_height: Game screen height
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Panel dimensions
        self.panel_width = 900
        self.panel_height = 280
        self.padding = 20

        # Fonts
        try:
            self.title_font = pygame.font.SysFont("consolas", 20, bold=True)
            self.text_font = pygame.font.SysFont("consolas", 16)
            self.choice_font = pygame.font.SysFont("consolas", 15)
            self.hint_font = pygame.font.SysFont("consolas", 14)
        except Exception:
            # Fallback to default font
            self.title_font = pygame.font.Font(None, 24)
            self.text_font = pygame.font.Font(None, 20)
            self.choice_font = pygame.font.Font(None, 18)
            self.hint_font = pygame.font.Font(None, 16)

        # Colors
        self.panel_bg_color = (20, 20, 30, 230)  # Dark blue, semi-transparent
        self.panel_border_color = (80, 120, 180)  # Light blue
        self.speaker_color = (255, 215, 0)  # Gold
        self.text_color = (255, 255, 255)  # White
        self.choice_normal_color = (200, 200, 200)  # Light gray
        self.choice_selected_color = (255, 255, 255)  # White
        self.choice_bg_selected_color = (60, 100, 140)  # Blue highlight
        self.hint_color = (150, 150, 150)  # Gray

        # State
        self.selected_choice_index = 0

    def render(
        self, surface: pygame.Surface, node: DialogueNode, available_choices: list[DialogueChoice]
    ):
        """
        Render dialogue UI.

        Args:
            surface: Surface to render on
            node: Current dialogue node
            available_choices: Available choices for this node
        """
        # Calculate panel position (centered horizontally, near bottom)
        panel_x = (self.screen_width - self.panel_width) // 2
        panel_y = self.screen_height - self.panel_height - 40

        # Create panel surface with alpha
        panel_surface = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        panel_surface.fill(self.panel_bg_color)

        # Draw border
        pygame.draw.rect(
            panel_surface, self.panel_border_color, (0, 0, self.panel_width, self.panel_height), 3
        )

        # Render speaker name (top-left)
        speaker_surface = self.title_font.render(node.speaker, True, self.speaker_color)
        panel_surface.blit(speaker_surface, (self.padding, self.padding))

        # Render dialogue text (wrapped, below speaker)
        text_y = self.padding + speaker_surface.get_height() + 10
        wrapped_lines = self._wrap_text(node.text, self.panel_width - self.padding * 2)

        for i, line in enumerate(wrapped_lines[:3]):  # Max 3 lines
            line_surface = self.text_font.render(line, True, self.text_color)
            panel_surface.blit(line_surface, (self.padding, text_y + i * 22))

        # Render choices (if any)
        if available_choices:
            choices_y = text_y + len(wrapped_lines[:3]) * 22 + 20

            for i, choice in enumerate(available_choices):
                choice_y = choices_y + i * 30

                # Highlight selected choice
                if i == self.selected_choice_index:
                    # Draw selection background
                    choice_bg = pygame.Surface(
                        (self.panel_width - self.padding * 2, 26), pygame.SRCALPHA
                    )
                    choice_bg.fill(self.choice_bg_selected_color)
                    panel_surface.blit(choice_bg, (self.padding, choice_y - 2))

                    # Render choice text (selected)
                    choice_text = f"> {choice.choice_text}"
                    choice_surface = self.choice_font.render(
                        choice_text, True, self.choice_selected_color
                    )
                else:
                    # Render choice text (normal)
                    choice_text = f"  {choice.choice_text}"
                    choice_surface = self.choice_font.render(
                        choice_text, True, self.choice_normal_color
                    )

                panel_surface.blit(choice_surface, (self.padding + 5, choice_y))

            # Render navigation hint
            hint_text = "UP/DOWN: Navigate  |  ENTER: Select"
            hint_surface = self.hint_font.render(hint_text, True, self.hint_color)
            hint_x = (self.panel_width - hint_surface.get_width()) // 2
            hint_y = self.panel_height - self.padding - hint_surface.get_height()
            panel_surface.blit(hint_surface, (hint_x, hint_y))

        else:
            # No choices, show continue hint
            hint_text = "ENTER: Continue"
            hint_surface = self.hint_font.render(hint_text, True, self.hint_color)
            hint_x = (self.panel_width - hint_surface.get_width()) // 2
            hint_y = self.panel_height - self.padding - hint_surface.get_height()
            panel_surface.blit(hint_surface, (hint_x, hint_y))

        # Blit panel to screen
        surface.blit(panel_surface, (panel_x, panel_y))

    def handle_input(
        self, keys_pressed: list[int], available_choices: list[DialogueChoice]
    ) -> str | None:
        """
        Handle keyboard input for dialogue navigation.

        Args:
            keys_pressed: List of pygame key codes pressed this frame
            available_choices: Available choices for current node

        Returns:
            "advance" if should auto-advance
            "select_X" where X is choice index if choice selected
            None otherwise
        """
        if pygame.K_RETURN in keys_pressed:
            if available_choices:
                # Select current choice
                return f"select_{self.selected_choice_index}"
            else:
                # Auto-advance
                return "advance"

        if pygame.K_UP in keys_pressed:
            if available_choices and self.selected_choice_index > 0:
                self.selected_choice_index -= 1

        if pygame.K_DOWN in keys_pressed:
            if available_choices and self.selected_choice_index < len(available_choices) - 1:
                self.selected_choice_index += 1

        return None

    def reset_selection(self):
        """Reset choice selection to first option."""
        self.selected_choice_index = 0

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        """
        Wrap text to fit within max width.

        Args:
            text: Text to wrap
            max_width: Maximum width in pixels

        Returns:
            List of wrapped lines
        """
        words = text.split(" ")
        lines = []
        current_line = ""

        for word in words:
            # Try adding word to current line
            test_line = current_line + (" " if current_line else "") + word
            test_surface = self.text_font.render(test_line, True, (255, 255, 255))

            if test_surface.get_width() <= max_width:
                current_line = test_line
            else:
                # Word doesn't fit, start new line
                if current_line:
                    lines.append(current_line)
                current_line = word

        # Add last line
        if current_line:
            lines.append(current_line)

        return lines
