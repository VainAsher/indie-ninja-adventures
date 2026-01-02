"""
Physics Parameter Tweaker - Live parameter adjustment overlay

Allows real-time tweaking of physics constants for rapid iteration on movement feel.
Toggle with 'P' key, adjust parameters with keyboard shortcuts.

Controls:
- P: Toggle physics tweaker overlay
- 1/2: Decrease/Increase GRAVITY
- 3/4: Decrease/Increase FALL_GRAVITY_MULT
- 5/6: Decrease/Increase MOVEMENT_ACCEL
- 7/8: Decrease/Increase JUMP_POWER
- 9/0: Decrease/Increase APEX_HANG_MULT
- [/]: Decrease/Increase MAX_RUN_SPEED
- R: Reset all to default values
- S: Save current values to file
"""

import pygame
from typing import Dict, Any
import config.physics_constants as physics


class PhysicsTweaker:
    """Debug tool for live physics parameter adjustment"""

    def __init__(self):
        # Font for overlay
        self.font = pygame.font.SysFont("consolas", 14)
        self.title_font = pygame.font.SysFont("consolas", 16, bold=True)

        # Visibility toggle
        self.visible = False

        # Default values (for reset)
        self.defaults = {
            "GRAVITY": 0.6,
            "FALL_GRAVITY_MULT": 2.0,
            "FAST_FALL_MULT": 2.0,
            "JUMP_CUT_MULT": 3.0,
            "APEX_HANG_THRESHOLD": 1.0,
            "APEX_HANG_MULT": 0.6,
            "MOVEMENT_ACCEL": 1200.0,
            "MAX_RUN_SPEED": 8.0,
            "JUMP_POWER": 14.5,
            "DOUBLE_JUMP_POWER": 14.5,
        }

        # Current parameter being adjusted (for visual feedback)
        self.last_adjusted = None
        self.last_adjusted_time = 0.0

        # Track key states for continuous adjustment
        self.keys_held = {}
        self.repeat_delay = 0.15  # Seconds between repeats
        self.last_repeat_time = {}

        # Safety warnings for physics changes
        self.safety_warnings = []

    def toggle(self):
        """Toggle visibility of the tweaker overlay"""
        self.visible = not self.visible
        return self.visible

    def handle_input(self, key_pressed: callable, dt: float):
        """
        Handle keyboard input for parameter adjustment

        Args:
            key_pressed: Function to check if key is pressed
            dt: Delta time for repeat timing
        """
        if not self.visible:
            return

        current_time = pygame.time.get_ticks() / 1000.0

        # Define parameter adjustments (key, parameter, decrease_amount, increase_amount)
        adjustments = [
            (pygame.K_1, pygame.K_2, "GRAVITY", -0.05, 0.05),
            (pygame.K_3, pygame.K_4, "FALL_GRAVITY_MULT", -0.1, 0.1),
            (pygame.K_5, pygame.K_6, "MOVEMENT_ACCEL", -100.0, 100.0),
            (pygame.K_7, pygame.K_8, "JUMP_POWER", -0.5, 0.5),
            (pygame.K_9, pygame.K_0, "APEX_HANG_MULT", -0.05, 0.05),
            (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET, "MAX_RUN_SPEED", -0.25, 0.25),
        ]

        for dec_key, inc_key, param, dec_amt, inc_amt in adjustments:
            # Decrease
            if key_pressed(dec_key):
                if self._can_repeat(param + "_dec", current_time):
                    self._adjust_param(param, dec_amt)
                    self.last_adjusted = param
                    self.last_adjusted_time = current_time

            # Increase
            if key_pressed(inc_key):
                if self._can_repeat(param + "_inc", current_time):
                    self._adjust_param(param, inc_amt)
                    self.last_adjusted = param
                    self.last_adjusted_time = current_time

        # Reset all
        if key_pressed(pygame.K_r):
            if self._can_repeat("reset", current_time):
                self.reset_all()
                self.last_adjusted = "RESET ALL"
                self.last_adjusted_time = current_time

    def _can_repeat(self, action_id: str, current_time: float) -> bool:
        """Check if enough time has passed to repeat an action"""
        if action_id not in self.last_repeat_time:
            self.last_repeat_time[action_id] = current_time
            return True

        if current_time - self.last_repeat_time[action_id] >= self.repeat_delay:
            self.last_repeat_time[action_id] = current_time
            return True

        return False

    def _adjust_param(self, param: str, amount: float):
        """Adjust a physics parameter by the given amount"""
        if hasattr(physics, param):
            current_value = getattr(physics, param)
            new_value = max(0.0, current_value + amount)  # Don't allow negative values
            setattr(physics, param, new_value)

            # Also update DOUBLE_JUMP_POWER if JUMP_POWER changes
            if param == "JUMP_POWER":
                physics.DOUBLE_JUMP_POWER = new_value

            # Check if change might break levels (for physics that affect movement)
            if param in ['GRAVITY', 'JUMP_POWER', 'DOUBLE_JUMP_POWER', 'MAX_RUN_SPEED']:
                self._check_safety(param, current_value, new_value)

    def _check_safety(self, param: str, old_value: float, new_value: float):
        """
        Check if physics change might break levels

        Args:
            param: Parameter name that was changed
            old_value: Previous value
            new_value: New value
        """
        from systems.physics_capabilities import validate_physics_for_generation

        # Only check physics that affect movement
        validation = validate_physics_for_generation()

        if not validation['valid']:
            self.safety_warnings = validation['warnings']
        else:
            self.safety_warnings = []

    def reset_all(self):
        """Reset all parameters to default values"""
        for param, default_value in self.defaults.items():
            if hasattr(physics, param):
                setattr(physics, param, default_value)

        # Clear warnings when resetting to defaults
        self.safety_warnings = []

    def save_to_file(self, filename: str = "config/physics_constants_tweaked.py"):
        """
        Save current physics constants to a file

        Args:
            filename: Path to save the constants
        """
        lines = [
            '"""',
            'Tweaked Physics Constants - Generated by Physics Tweaker',
            '"""',
            '',
        ]

        for param in self.defaults.keys():
            if hasattr(physics, param):
                value = getattr(physics, param)
                lines.append(f"{param} = {value}")

        with open(filename, 'w') as f:
            f.write('\n'.join(lines))

        print(f"Physics constants saved to {filename}")

    def draw(self, surface: pygame.Surface):
        """
        Draw the physics tweaker overlay

        Args:
            surface: Surface to draw on
        """
        if not self.visible:
            return

        # Semi-transparent background
        overlay_width = 400
        # Dynamic height based on warnings (estimate ~20px per warning line)
        base_height = 450
        warning_height = len(self.safety_warnings) * 60 if self.safety_warnings else 0
        overlay_height = base_height + warning_height
        x = surface.get_width() - overlay_width - 10
        y = 10

        # Background panel
        bg_surface = pygame.Surface((overlay_width, overlay_height))
        bg_surface.set_alpha(220)
        bg_surface.fill((20, 20, 30))
        surface.blit(bg_surface, (x, y))

        # Border
        pygame.draw.rect(surface, (100, 150, 255), (x, y, overlay_width, overlay_height), 2)

        # Title
        title = self.title_font.render("Physics Tweaker [P]", True, (100, 200, 255))
        surface.blit(title, (x + 10, y + 10))

        # Instructions
        instructions = [
            "Controls:",
            "1/2: GRAVITY",
            "3/4: FALL_GRAVITY_MULT",
            "5/6: MOVEMENT_ACCEL",
            "7/8: JUMP_POWER",
            "9/0: APEX_HANG_MULT",
            "[/]: MAX_RUN_SPEED",
            "R: Reset All",
        ]

        current_y = y + 40
        for instruction in instructions:
            text = self.font.render(instruction, True, (180, 180, 200))
            surface.blit(text, (x + 10, current_y))
            current_y += 18

        # Separator
        current_y += 10
        pygame.draw.line(surface, (80, 80, 100), (x + 10, current_y), (x + overlay_width - 10, current_y), 1)
        current_y += 15

        # Current values
        current_time = pygame.time.get_ticks() / 1000.0

        values_title = self.title_font.render("Current Values:", True, (100, 200, 255))
        surface.blit(values_title, (x + 10, current_y))
        current_y += 25

        # Display parameters
        params_to_display = [
            ("GRAVITY", "{:.2f}"),
            ("FALL_GRAVITY_MULT", "{:.2f}"),
            ("APEX_HANG_MULT", "{:.2f}"),
            ("APEX_HANG_THRESHOLD", "{:.2f}"),
            ("MOVEMENT_ACCEL", "{:.0f}"),
            ("MAX_RUN_SPEED", "{:.2f}"),
            ("JUMP_POWER", "{:.2f}"),
            ("FAST_FALL_MULT", "{:.2f}"),
            ("JUMP_CUT_MULT", "{:.2f}"),
        ]

        for param, fmt in params_to_display:
            if hasattr(physics, param):
                value = getattr(physics, param)

                # Highlight recently adjusted parameter
                if param == self.last_adjusted and (current_time - self.last_adjusted_time) < 1.0:
                    color = (255, 255, 100)  # Yellow highlight
                else:
                    color = (200, 200, 220)

                # Check if different from default
                is_modified = False
                if param in self.defaults:
                    is_modified = abs(value - self.defaults[param]) > 0.001

                # Format text
                display_text = f"{param}: {fmt.format(value)}"
                if is_modified:
                    display_text += " *"  # Mark modified values

                text = self.font.render(display_text, True, color)
                surface.blit(text, (x + 15, current_y))
                current_y += 18

        # Safety warnings section
        if self.safety_warnings:
            current_y += 10
            pygame.draw.line(surface, (80, 80, 100), (x + 10, current_y), (x + overlay_width - 10, current_y), 1)
            current_y += 15

            warning_title = self.title_font.render("⚠ WARNINGS:", True, (255, 200, 50))
            surface.blit(warning_title, (x + 10, current_y))
            current_y += 25

            for warning in self.safety_warnings:
                # Word wrap long warnings
                words = warning.split(' ')
                line = ""
                for word in words:
                    test_line = line + word + " "
                    if self.font.size(test_line)[0] < overlay_width - 30:
                        line = test_line
                    else:
                        if line:
                            warning_text = self.font.render(line.strip(), True, (255, 150, 50))
                            surface.blit(warning_text, (x + 15, current_y))
                            current_y += 18
                        line = word + " "

                # Render remaining line
                if line:
                    warning_text = self.font.render(line.strip(), True, (255, 150, 50))
                    surface.blit(warning_text, (x + 15, current_y))
                    current_y += 18

        # Footer note
        current_y += 10
        note = self.font.render("* = Modified from default", True, (150, 150, 170))
        surface.blit(note, (x + 10, current_y))


def create_tweaker() -> PhysicsTweaker:
    """Factory function to create a physics tweaker instance"""
    return PhysicsTweaker()
