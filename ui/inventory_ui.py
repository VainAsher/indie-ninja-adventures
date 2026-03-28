"""
Inventory UI - Player inventory display and management

Simple grid-based inventory with equipment slots.
Press I to open/close.

Version: v0.6.0 (Phase 6) - Simplified
"""

from dataclasses import dataclass

import pygame

# ============================================================
# UI State
# ============================================================


@dataclass
class InventoryUIState:
    """Inventory UI state"""

    open: bool = False
    selected_slot: int = 0
    hover_slot: int | None = None
    show_tooltip: bool = False


# ============================================================
# Inventory UI Renderer
# ============================================================


class InventoryUI:
    """
    Simple inventory UI for displaying items.

    Features:
    - Grid-based layout (4x5 = 20 slots)
    - Equipment slots (weapon, armor)
    - Currency display
    - Hover tooltips
    - Keyboard/mouse controls

    Note: This is a simplified version. Full implementation
    would integrate with game/inventory_system.py from Phase 1.
    """

    def __init__(self, font_name: str = "consolas", font_size: int = 16):
        """Initialize inventory UI"""
        self.font = pygame.font.SysFont(font_name, font_size)
        self.small_font = pygame.font.SysFont(font_name, 14)
        self.title_font = pygame.font.SysFont(font_name, 20, bold=True)

        # Grid layout
        self.grid_cols = 4
        self.grid_rows = 5
        self.slot_size = 64
        self.slot_spacing = 8

        # Colors
        self.color_bg = (30, 30, 40, 230)
        self.color_slot_empty = (50, 50, 60)
        self.color_slot_hover = (80, 80, 100)
        self.color_slot_selected = (100, 120, 140)
        self.color_border = (100, 100, 120)
        self.color_text = (220, 220, 230)

        # Rarity colors
        self.rarity_colors = {
            "common": (180, 180, 180),
            "uncommon": (100, 255, 100),
            "rare": (100, 150, 255),
            "epic": (180, 100, 255),
            "legendary": (255, 150, 50),
        }

        # State
        self.state = InventoryUIState()

    def open(self):
        """Open inventory"""
        self.state.open = True

    def close(self):
        """Close inventory"""
        self.state.open = False

    def toggle(self):
        """Toggle inventory open/close"""
        self.state.open = not self.state.open

    def is_open(self) -> bool:
        """Check if inventory is open"""
        return self.state.open

    def draw(
        self,
        surface: pygame.Surface,
        items: list[dict] | None = None,
        currency: int = 0,
        equipped_weapon: str | None = None,
        equipped_armor: str | None = None,
    ):
        """
        Draw inventory UI.

        Args:
            surface: Surface to draw on
            items: List of item dicts with keys: name, quantity, rarity
            currency: Player currency amount
            equipped_weapon: Equipped weapon name
            equipped_armor: Equipped armor name
        """
        if not self.state.open:
            return

        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Center panel
        panel_w = 450
        panel_h = 500
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
        title = "Inventory"
        title_surf = self.title_font.render(title, True, self.color_text)
        surface.blit(title_surf, (panel_x + 20, panel_y + 15))

        # Draw equipment slots
        y_pos = panel_y + 50
        self._draw_equipment_slots(surface, panel_x + 20, y_pos, equipped_weapon, equipped_armor)

        # Draw item grid
        y_pos += 100
        self._draw_item_grid(surface, panel_x + 20, y_pos, items or [])

        # Draw currency
        y_pos += self.grid_rows * (self.slot_size + self.slot_spacing) + 20
        self._draw_currency(surface, panel_x + 20, y_pos, currency)

        # Draw controls hint
        hint = "Press I to close | Arrow keys to select | Enter to use/equip"
        hint_surf = self.small_font.render(hint, True, (150, 150, 160))
        surface.blit(hint_surf, (panel_x + 20, panel_y + panel_h - 30))

    def _draw_equipment_slots(self, surface, x, y, weapon, armor):
        """Draw equipment slots"""
        slot_w = 80
        slot_h = 60

        # Weapon slot
        pygame.draw.rect(
            surface, self.color_slot_empty, pygame.Rect(x, y, slot_w, slot_h), border_radius=4
        )
        pygame.draw.rect(
            surface, self.color_border, pygame.Rect(x, y, slot_w, slot_h), width=2, border_radius=4
        )

        label = self.small_font.render("Weapon", True, self.color_text)
        surface.blit(label, (x + 5, y - 18))

        if weapon:
            text = self.small_font.render(weapon[:10], True, (255, 215, 0))
            surface.blit(text, (x + 5, y + 20))

        # Armor slot
        pygame.draw.rect(
            surface,
            self.color_slot_empty,
            pygame.Rect(x + slot_w + 20, y, slot_w, slot_h),
            border_radius=4,
        )
        pygame.draw.rect(
            surface,
            self.color_border,
            pygame.Rect(x + slot_w + 20, y, slot_w, slot_h),
            width=2,
            border_radius=4,
        )

        label = self.small_font.render("Armor", True, self.color_text)
        surface.blit(label, (x + slot_w + 25, y - 18))

        if armor:
            text = self.small_font.render(armor[:10], True, (100, 150, 255))
            surface.blit(text, (x + slot_w + 25, y + 20))

    def _draw_item_grid(self, surface, x, y, items):
        """Draw item grid"""
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                slot_index = row * self.grid_cols + col
                slot_x = x + col * (self.slot_size + self.slot_spacing)
                slot_y = y + row * (self.slot_size + self.slot_spacing)

                # Get item for this slot
                item = items[slot_index] if slot_index < len(items) else None

                # Draw slot
                self._draw_item_slot(surface, slot_x, slot_y, slot_index, item)

    def _draw_item_slot(self, surface, x, y, slot_index, item):
        """Draw a single item slot"""
        # Determine slot color
        if slot_index == self.state.selected_slot:
            color = self.color_slot_selected
        elif slot_index == self.state.hover_slot:
            color = self.color_slot_hover
        else:
            color = self.color_slot_empty

        # Draw slot background
        pygame.draw.rect(
            surface, color, pygame.Rect(x, y, self.slot_size, self.slot_size), border_radius=4
        )

        # Draw border (rarity color if item exists)
        if item:
            rarity = item.get("rarity", "common")
            border_color = self.rarity_colors.get(rarity, self.color_border)
        else:
            border_color = self.color_border

        pygame.draw.rect(
            surface,
            border_color,
            pygame.Rect(x, y, self.slot_size, self.slot_size),
            width=2,
            border_radius=4,
        )

        # Draw item if present
        if item:
            # Item name (truncated)
            name = item.get("name", "Item")[:8]
            name_surf = self.small_font.render(name, True, self.color_text)
            surface.blit(name_surf, (x + 4, y + 4))

            # Quantity
            quantity = item.get("quantity", 1)
            if quantity > 1:
                qty_text = f"x{quantity}"
                qty_surf = self.small_font.render(qty_text, True, (200, 200, 210))
                surface.blit(qty_surf, (x + self.slot_size - 28, y + self.slot_size - 20))

    def _draw_currency(self, surface, x, y, currency):
        """Draw currency display"""
        text = f"Gold: {currency}"
        text_surf = self.font.render(text, True, (255, 215, 0))
        surface.blit(text_surf, (x, y))

    def handle_input(self, event: pygame.event.Event):
        """
        Handle input events.

        Args:
            event: Pygame event
        """
        if not self.state.open:
            return

        if event.type == pygame.KEYDOWN:
            # Arrow keys to navigate
            if event.key == pygame.K_RIGHT:
                self.state.selected_slot = min(self.state.selected_slot + 1, 19)
            elif event.key == pygame.K_LEFT:
                self.state.selected_slot = max(self.state.selected_slot - 1, 0)
            elif event.key == pygame.K_DOWN:
                self.state.selected_slot = min(self.state.selected_slot + self.grid_cols, 19)
            elif event.key == pygame.K_UP:
                self.state.selected_slot = max(self.state.selected_slot - self.grid_cols, 0)
            elif event.key == pygame.K_RETURN:
                # Use/equip selected item
                print(f"Use/equip item at slot {self.state.selected_slot}")

    def handle_command(self, pressed_once: list[int]) -> int | None:
        """
        Handle command-style input (pressed-once keys).

        Returns:
            Selected slot index if "activate" pressed, else None.
        """
        if not self.state.open:
            return None

        max_slot = self.grid_cols * self.grid_rows - 1

        # Arrow keys or WASD to navigate
        if pygame.K_RIGHT in pressed_once or pygame.K_d in pressed_once:
            self.state.selected_slot = min(self.state.selected_slot + 1, max_slot)
        elif pygame.K_LEFT in pressed_once or pygame.K_a in pressed_once:
            self.state.selected_slot = max(self.state.selected_slot - 1, 0)
        elif pygame.K_DOWN in pressed_once or pygame.K_s in pressed_once:
            self.state.selected_slot = min(self.state.selected_slot + self.grid_cols, max_slot)
        elif pygame.K_UP in pressed_once or pygame.K_w in pressed_once:
            self.state.selected_slot = max(self.state.selected_slot - self.grid_cols, 0)

        if pygame.K_RETURN in pressed_once:
            return self.state.selected_slot

        return None


# ============================================================
# Helper Functions
# ============================================================


def create_inventory_ui() -> InventoryUI:
    """Create an inventory UI instance"""
    return InventoryUI()
