"""
Tutorial System - Contextual hints and guidance for new players

Provides non-intrusive tutorial messages that trigger based on player actions.
Messages are shown once and tracked in save data.

Architecture:
- TutorialTrigger: Defines when/what to show
- TutorialMessage: Visual message display
- TutorialManager: Coordinates triggers and display
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import pygame


class TutorialTriggerType(Enum):
    """Types of tutorial triggers"""

    IMMEDIATE = "immediate"  # Show immediately
    ON_EVENT = "on_event"  # Show when event occurs
    ON_CONDITION = "on_condition"  # Show when condition met
    TIMED = "timed"  # Show after time elapsed


@dataclass
class TutorialTrigger:
    """
    Defines a tutorial trigger condition

    Attributes:
        trigger_id: Unique identifier for this trigger
        trigger_type: How this trigger activates
        message: Text to display
        condition: Optional condition function (returns bool)
        duration: How long to show message (seconds, 0 = until dismissed)
        priority: Display priority (higher = more important)
    """

    trigger_id: str
    trigger_type: TutorialTriggerType
    message: str
    condition: Callable[[], bool] | None = None
    duration: float = 5.0
    priority: int = 0


class TutorialMessage:
    """
    Visual tutorial message display

    Features:
    - Animated slide-in/out
    - Semi-transparent background
    - Dismiss on key press
    - Auto-fade after duration
    """

    def __init__(self, message: str, duration: float, screen_width: int, screen_height: int):
        """
        Initialize tutorial message

        Args:
            message: Text to display
            duration: Display duration (0 = until dismissed)
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.message = message
        self.duration = duration
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Message state
        self.active = True
        self.elapsed_time = 0.0
        self.dismissed = False

        # Animation
        self.slide_in_time = 0.3  # Seconds
        self.slide_out_time = 0.3
        self.slide_offset = 0.0  # 0.0 = fully visible, 1.0 = hidden

        # Fonts
        self.message_font = pygame.font.SysFont("consolas", 24)
        self.hint_font = pygame.font.SysFont("consolas", 16)

        # Colors
        self.bg_color = (20, 20, 40, 220)  # Semi-transparent dark blue
        self.text_color = (255, 255, 200)  # Light yellow
        self.hint_color = (180, 180, 180)  # Gray
        self.border_color = (100, 100, 150)

        # Layout
        self.padding = 20
        self.border_width = 2
        self.position = "bottom"  # Can be: top, bottom, center

    def update(self, dt: float):
        """
        Update message animation and lifetime

        Args:
            dt: Delta time in seconds
        """
        if not self.active:
            return

        self.elapsed_time += dt

        # Slide-in animation
        if self.elapsed_time < self.slide_in_time:
            # Ease-out cubic
            t = self.elapsed_time / self.slide_in_time
            self.slide_offset = 1.0 - (t * t * (3.0 - 2.0 * t))

        # Check if duration expired
        elif self.duration > 0 and self.elapsed_time >= self.duration:
            self.dismiss()
        else:
            self.slide_offset = 0.0

        # Slide-out animation when dismissed
        if self.dismissed:
            slide_out_elapsed = self.elapsed_time - self.duration if self.duration > 0 else 0
            if slide_out_elapsed < self.slide_out_time:
                # Ease-in cubic
                t = slide_out_elapsed / self.slide_out_time
                self.slide_offset = t * t * (3.0 - 2.0 * t)
            else:
                self.active = False

    def dismiss(self):
        """Dismiss the message (starts slide-out animation)"""
        if not self.dismissed:
            self.dismissed = True
            # Reset duration to trigger slide-out
            self.duration = self.elapsed_time

    def handle_input(self, keys) -> bool:
        """
        Handle input for dismissing message

        Args:
            keys: Key states from pygame.key.get_pressed()

        Returns:
            True if message was dismissed
        """
        if not self.active or self.dismissed:
            return False

        # Dismiss on any key (except modifiers)
        dismissable_keys = [
            pygame.K_SPACE,
            pygame.K_RETURN,
            pygame.K_ESCAPE,
            pygame.K_e,
            pygame.K_f,
            pygame.K_LSHIFT,
            pygame.K_RSHIFT,
        ]

        for key in dismissable_keys:
            if keys[key]:
                self.dismiss()
                return True

        return False

    def render(self, surface: pygame.Surface):
        """
        Render message to surface

        Args:
            surface: Surface to render on
        """
        if not self.active:
            return

        # Render message text
        message_lines = self.message.split("\n")
        line_surfaces = [
            self.message_font.render(line, True, self.text_color) for line in message_lines
        ]

        # Calculate total height
        line_height = self.message_font.get_height()
        total_text_height = len(message_lines) * line_height

        # Add hint text
        hint_text = "[Press any key to dismiss]" if self.duration == 0 else "[Press any key]"
        hint_surf = self.hint_font.render(hint_text, True, self.hint_color)

        # Calculate box dimensions
        max_line_width = max(surf.get_width() for surf in line_surfaces)
        box_width = max(max_line_width, hint_surf.get_width()) + self.padding * 2
        box_height = total_text_height + hint_surf.get_height() + self.padding * 3

        # Position based on setting
        if self.position == "top":
            box_y = 80
        elif self.position == "center":
            box_y = (self.screen_height - box_height) // 2
        else:  # bottom
            box_y = self.screen_height - box_height - 80

        # Apply slide animation (slide from bottom)
        slide_pixels = int((box_height + 100) * self.slide_offset)
        if self.position == "bottom":
            box_y += slide_pixels
        else:
            box_y -= slide_pixels

        box_x = (self.screen_width - box_width) // 2

        # Draw background
        bg_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        bg_surf.fill(self.bg_color)

        # Draw border
        pygame.draw.rect(
            bg_surf, self.border_color, (0, 0, box_width, box_height), self.border_width
        )

        surface.blit(bg_surf, (box_x, box_y))

        # Draw message lines
        current_y = box_y + self.padding
        for line_surf in line_surfaces:
            line_x = box_x + (box_width - line_surf.get_width()) // 2
            surface.blit(line_surf, (line_x, current_y))
            current_y += line_height

        # Draw hint
        hint_x = box_x + (box_width - hint_surf.get_width()) // 2
        hint_y = box_y + box_height - hint_surf.get_height() - self.padding
        surface.blit(hint_surf, (hint_x, hint_y))


class TutorialManager:
    """
    Manages tutorial triggers and message display

    Features:
    - Trigger registration
    - Condition checking
    - Message queue
    - Save integration (tracks shown tutorials)
    """

    def __init__(self, screen_width: int, screen_height: int, save_manager=None):
        """
        Initialize tutorial manager

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            save_manager: Optional save manager for persistence
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.save_manager = save_manager

        # Tutorial state
        self.triggers: dict[str, TutorialTrigger] = {}
        self.shown_tutorials: set[str] = set()
        self.current_message: TutorialMessage | None = None
        self.message_queue: list[TutorialTrigger] = []

        # Settings
        self.enabled = True
        self.show_all = False  # Debug: show tutorials even if already shown

        # Load shown tutorials from save
        self._load_from_save()

        # Register default tutorials
        self._register_default_tutorials()

    def _load_from_save(self):
        """Load shown tutorials from save data"""
        if not self.save_manager:
            return

        # Get tutorials from save data
        tutorials_seen = self.save_manager.data.player_progress.tutorials_seen
        if tutorials_seen:
            self.shown_tutorials = set(tutorials_seen)

    def _save_to_save(self):
        """Save shown tutorials to save data"""
        if not self.save_manager:
            return

        # Save tutorials to save data
        self.save_manager.data.player_progress.tutorials_seen = list(self.shown_tutorials)
        self.save_manager.mark_dirty()

    def _register_default_tutorials(self):
        """Register default tutorial triggers"""

        # Welcome message (first time playing)
        self.register_trigger(
            TutorialTrigger(
                trigger_id="welcome",
                trigger_type=TutorialTriggerType.IMMEDIATE,
                message="Welcome to Ninja Dash!\nUse Arrow Keys or WASD to move",
                duration=6.0,
                priority=100,
            )
        )

        # Jump tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="jump",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Press SPACE or W to jump\nYou have a double jump!",
                duration=5.0,
                priority=90,
            )
        )

        # Dash tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="dash",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Press SHIFT to dash\nDash to move quickly or avoid danger",
                duration=5.0,
                priority=80,
            )
        )

        # Wall slide tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="wall_slide",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Hold against a wall to wall slide\nJump off walls to reach high places!",
                duration=6.0,
                priority=70,
            )
        )

        # Crouch tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="crouch",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Press S or DOWN to crouch\nDuck under low obstacles",
                duration=5.0,
                priority=60,
            )
        )

        # Collectibles tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="collectibles",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Collect coins and gems!\nFind them all for a perfect score",
                duration=5.0,
                priority=50,
            )
        )

        # Hazards tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="hazards",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Avoid spikes and hazards!\nYou have 3 hearts - be careful!",
                duration=5.0,
                priority=40,
            )
        )

        # Exit tutorial
        self.register_trigger(
            TutorialTrigger(
                trigger_id="exit",
                trigger_type=TutorialTriggerType.ON_EVENT,
                message="Find the exit to complete the level!\nLook for the glowing portal",
                duration=5.0,
                priority=30,
            )
        )

    def register_trigger(self, trigger: TutorialTrigger):
        """
        Register a tutorial trigger

        Args:
            trigger: Tutorial trigger to register
        """
        self.triggers[trigger.trigger_id] = trigger

    def trigger_tutorial(self, trigger_id: str, force: bool = False):
        """
        Trigger a specific tutorial

        Args:
            trigger_id: ID of tutorial to trigger
            force: Show even if already shown
        """
        if not self.enabled and not force:
            return

        # Check if already shown
        if trigger_id in self.shown_tutorials and not self.show_all and not force:
            return

        # Get trigger
        trigger = self.triggers.get(trigger_id)
        if not trigger:
            return

        # Check condition if present
        if trigger.condition and not trigger.condition():
            return

        # Add to queue (sorted by priority)
        self.message_queue.append(trigger)
        self.message_queue.sort(key=lambda t: -t.priority)

        # Mark as shown
        self.shown_tutorials.add(trigger_id)
        self._save_to_save()

    def update(self, dt: float):
        """
        Update tutorial system

        Args:
            dt: Delta time in seconds
        """
        if not self.enabled:
            return

        # Update current message
        if self.current_message:
            self.current_message.update(dt)

            # Remove if no longer active
            if not self.current_message.active:
                self.current_message = None

        # Show next message if queue not empty and no current message
        if not self.current_message and self.message_queue:
            next_trigger = self.message_queue.pop(0)
            self.current_message = TutorialMessage(
                next_trigger.message, next_trigger.duration, self.screen_width, self.screen_height
            )

    def handle_input(self, keys):
        """
        Handle input for tutorial dismissal

        Args:
            keys: Key states from pygame.key.get_pressed()
        """
        if self.current_message:
            self.current_message.handle_input(keys)

    def render(self, surface: pygame.Surface):
        """
        Render current tutorial message

        Args:
            surface: Surface to render on
        """
        if self.current_message:
            self.current_message.render(surface)

    def has_active_message(self) -> bool:
        """Check if a tutorial message is currently displayed"""
        return self.current_message is not None

    def reset(self):
        """Reset all shown tutorials (for debugging/testing)"""
        self.shown_tutorials.clear()
        self.message_queue.clear()
        self.current_message = None
        self._save_to_save()

    def set_enabled(self, enabled: bool):
        """Enable/disable tutorial system"""
        self.enabled = enabled
        if not enabled:
            self.current_message = None
            self.message_queue.clear()


class ControlsHintOverlay:
    """
    Persistent control hints overlay

    Shows control scheme in corner of screen, fades after use.
    """

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        start_visible: bool = True,
        auto_fade: bool = True,
    ):
        """
        Initialize controls hint overlay

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            start_visible: Show overlay immediately if True
            auto_fade: Fade out after delay if True
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Overlay state
        self.visible = start_visible
        self.opacity = 255 if start_visible else 0
        self.auto_fade = auto_fade
        self.fade_start_time = 30.0  # Start fading after 30 seconds
        self.fade_duration = 5.0  # Fade over 5 seconds
        self.elapsed_time = 0.0

        # Fonts
        self.font = pygame.font.SysFont("consolas", 16)
        self.title_font = pygame.font.SysFont("consolas", 18, bold=True)

        # Colors
        self.bg_color = (10, 10, 20)
        self.text_color = (200, 200, 220)
        self.title_color = (255, 215, 0)

        # Control hints
        self.controls = [
            ("MOVE", "Arrow Keys / WASD"),
            ("JUMP", "Space / W / Up"),
            ("DASH", "Shift"),
            ("CROUCH / FALL", "S / Down"),
            ("RUN", "Alt"),
            ("ATTACK", "J"),
            ("SHURIKEN", "K (Aim Up/Down)"),
            ("TELEPORT", "F (Aim Up/Down)"),
            ("NINJUTSU", "Hold L or Q"),
            ("INTERACT", "E"),
            ("USE ITEM", "R"),
            ("INVENTORY", "I"),
            ("MAP", "Tab / M"),
            ("HINTS", "H"),
            ("PAUSE", "ESC"),
        ]

    def update(self, dt: float):
        """
        Update overlay fade

        Args:
            dt: Delta time in seconds
        """
        if not self.visible:
            return

        self.elapsed_time += dt

        if not self.auto_fade:
            return

        # Start fading after fade_start_time
        if self.elapsed_time > self.fade_start_time:
            fade_elapsed = self.elapsed_time - self.fade_start_time
            if fade_elapsed < self.fade_duration:
                # Linear fade
                self.opacity = int(255 * (1.0 - fade_elapsed / self.fade_duration))
            else:
                self.visible = False
                self.opacity = 0
                self.auto_fade = False

    def render(self, surface: pygame.Surface):
        """
        Render controls overlay

        Args:
            surface: Surface to render on
        """
        if not self.visible or self.opacity == 0:
            return

        # Create overlay surface
        padding = 10
        line_height = 20

        # Calculate dimensions
        title = "CONTROLS"
        title_surf = self.title_font.render(title, True, self.title_color)

        max_width = title_surf.get_width()
        for action, keys in self.controls:
            text = f"{action}: {keys}"
            text_surf = self.font.render(text, True, self.text_color)
            max_width = max(max_width, text_surf.get_width())

        box_width = max_width + padding * 2
        box_height = title_surf.get_height() + len(self.controls) * line_height + padding * 3

        # Position in bottom-left corner
        box_x = 10
        box_y = self.screen_height - box_height - 10

        # Draw background with opacity
        bg_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        bg_color_alpha = (*self.bg_color, int(200 * self.opacity / 255))
        bg_surf.fill(bg_color_alpha)
        surface.blit(bg_surf, (box_x, box_y))

        # Draw border
        border_color = (*self.text_color, self.opacity)
        pygame.draw.rect(surface, border_color, (box_x, box_y, box_width, box_height), 1)

        # Draw title
        title_surf.set_alpha(self.opacity)
        title_x = box_x + (box_width - title_surf.get_width()) // 2
        title_y = box_y + padding
        surface.blit(title_surf, (title_x, title_y))

        # Draw controls
        current_y = title_y + title_surf.get_height() + padding
        for action, keys in self.controls:
            text = f"{action}: {keys}"
            text_surf = self.font.render(text, True, self.text_color)
            text_surf.set_alpha(self.opacity)
            text_x = box_x + padding
            surface.blit(text_surf, (text_x, current_y))
            current_y += line_height

    def hide(self):
        """Immediately hide the overlay"""
        self.visible = False
        self.opacity = 0
        self.auto_fade = False

    def show(self, auto_fade: bool = False):
        """Show the overlay (optionally with auto-fade)."""
        self.visible = True
        self.opacity = 255
        self.elapsed_time = 0.0
        self.auto_fade = auto_fade

    def toggle(self):
        """Toggle overlay visibility."""
        if self.visible:
            self.hide()
        else:
            self.show(auto_fade=False)

    def reset(self):
        """Reset overlay to initial state"""
        self.visible = True
        self.opacity = 255
        self.elapsed_time = 0.0
