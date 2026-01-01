"""
Shop UI - NPC shop interface

Buy and sell items with NPCs.
Split view: NPC inventory (left) | Player inventory (right)

Version: v0.6.0 (Phase 6) - Simplified
"""

from dataclasses import dataclass

import pygame

# ============================================================
# Shop UI State
# ============================================================


@dataclass
class ShopUIState:
    """Shop UI state"""

    open: bool = False
    selected_side: str = "npc"  # "npc" or "player"
    selected_index: int = 0
    transaction_mode: str | None = None  # "buy", "sell", or None


# ============================================================
# Shop UI Renderer
# ============================================================


class ShopUI:
    """
    Simple shop UI for buying/selling items.

    Features:
    - Split view (NPC left, Player right)
    - Buy/sell transactions
    - Price display
    - Currency validation

    Note: Simplified version. Full implementation would
    integrate with game/trading_system.py from Phase 1.
    """

    def __init__(self, font_name: str = "consolas", font_size: int = 16):
        """Initialize shop UI"""
        self.font = pygame.font.SysFont(font_name, font_size)
        self.small_font = pygame.font.SysFont(font_name, 14)
        self.title_font = pygame.font.SysFont(font_name, 20, bold=True)

        # Colors
        self.color_bg = (30, 30, 40, 230)
        self.color_panel_npc = (50, 40, 60)
        self.color_panel_player = (40, 50, 60)
        self.color_selected = (100, 120, 140)
        self.color_border = (100, 100, 120)
        self.color_text = (220, 220, 230)
        self.color_price_buy = (255, 215, 0)  # Gold
        self.color_price_sell = (100, 255, 100)  # Green
        self.color_price_cant_afford = (255, 100, 100)  # Red

        # State
        self.state = ShopUIState()
        # Track previous command states for edge detection (replay safe)
        self._prev_left = False
        self._prev_right = False
        self._prev_up = False
        self._prev_down = False
        self._prev_confirm = False
        self._prev_back = False

    def open(self, npc_name: str = "Shopkeeper"):
        """Open shop"""
        self.state.open = True
        self.npc_name = npc_name

    def close(self):
        """Close shop"""
        self.state.open = False

    def is_open(self) -> bool:
        """Check if shop is open"""
        return self.state.open

    def draw(
        self,
        surface: pygame.Surface,
        npc_items: list[dict] | None = None,
        player_items: list[dict] | None = None,
        player_currency: int = 0,
        npc_currency: int = 1000,
    ):
        """
        Draw shop UI.

        Args:
            surface: Surface to draw on
            npc_items: NPC shop items (name, price, quantity)
            player_items: Player items (name, sell_price, quantity)
            player_currency: Player gold
            npc_currency: NPC gold
        """
        if not self.state.open:
            return

        screen_w = surface.get_width()
        screen_h = surface.get_height()

        # Center panel
        panel_w = 700
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
        title = f"{getattr(self, 'npc_name', 'Shop')}"
        title_surf = self.title_font.render(title, True, self.color_text)
        surface.blit(
            title_surf, (panel_x + panel_w // 2 - title_surf.get_width() // 2, panel_y + 15)
        )

        # Split view
        split_x = panel_x + panel_w // 2

        # Draw NPC inventory (left)
        self._draw_npc_inventory(
            surface, panel_x + 20, panel_y + 60, npc_items or [], npc_currency, player_currency
        )

        # Draw divider
        pygame.draw.line(
            surface,
            self.color_border,
            (split_x, panel_y + 50),
            (split_x, panel_y + panel_h - 80),
            2,
        )

        # Draw player inventory (right)
        self._draw_player_inventory(
            surface, split_x + 20, panel_y + 60, player_items or [], player_currency
        )

        # Draw transaction buttons
        self._draw_transaction_buttons(surface, panel_x, panel_y + panel_h - 60, panel_w)

        # Draw controls hint
        hint = "Arrow keys to select | Enter to buy/sell | ESC to close"
        hint_surf = self.small_font.render(hint, True, (150, 150, 160))
        surface.blit(hint_surf, (panel_x + 20, panel_y + panel_h - 30))

    def _draw_npc_inventory(self, surface, x, y, items, npc_currency, player_currency):
        """Draw NPC shop inventory"""
        # Header
        header = f"Shop Items (Gold: {npc_currency})"
        header_surf = self.font.render(header, True, self.color_text)
        surface.blit(header_surf, (x, y))

        y += 30

        # List items
        max_items = 8
        for i, item in enumerate(items[:max_items]):
            item_y = y + i * 35

            # Highlight if selected
            if self.state.selected_side == "npc" and self.state.selected_index == i:
                pygame.draw.rect(
                    surface,
                    self.color_selected,
                    pygame.Rect(x - 5, item_y - 5, 300, 30),
                    border_radius=4,
                )

            # Item name
            name = item.get("name", "Item")
            name_surf = self.small_font.render(name, True, self.color_text)
            surface.blit(name_surf, (x, item_y))

            # Price
            price = item.get("price", 0)
            can_afford = player_currency >= price
            price_color = self.color_price_buy if can_afford else self.color_price_cant_afford
            price_text = f"{price}g"
            price_surf = self.small_font.render(price_text, True, price_color)
            surface.blit(price_surf, (x + 220, item_y))

    def _draw_player_inventory(self, surface, x, y, items, player_currency):
        """Draw player inventory"""
        # Header
        header = f"Your Items (Gold: {player_currency})"
        header_surf = self.font.render(header, True, self.color_text)
        surface.blit(header_surf, (x, y))

        y += 30

        # List items
        max_items = 8
        for i, item in enumerate(items[:max_items]):
            item_y = y + i * 35

            # Highlight if selected
            if self.state.selected_side == "player" and self.state.selected_index == i:
                pygame.draw.rect(
                    surface,
                    self.color_selected,
                    pygame.Rect(x - 5, item_y - 5, 300, 30),
                    border_radius=4,
                )

            # Item name
            name = item.get("name", "Item")
            quantity = item.get("quantity", 1)
            name_text = f"{name} x{quantity}" if quantity > 1 else name
            name_surf = self.small_font.render(name_text, True, self.color_text)
            surface.blit(name_surf, (x, item_y))

            # Sell price (50% of value)
            sell_price = item.get("sell_price", 0)
            price_text = f"{sell_price}g"
            price_surf = self.small_font.render(price_text, True, self.color_price_sell)
            surface.blit(price_surf, (x + 220, item_y))

    def _draw_transaction_buttons(self, surface, x, y, width):
        """Draw buy/sell/cancel buttons"""
        button_w = 100
        button_h = 40
        button_spacing = 20

        # Calculate button positions
        total_w = button_w * 3 + button_spacing * 2
        start_x = x + (width - total_w) // 2

        # Buy button
        buy_rect = pygame.Rect(start_x, y, button_w, button_h)
        buy_color = (80, 120, 80) if self.state.selected_side == "npc" else (60, 60, 70)
        pygame.draw.rect(surface, buy_color, buy_rect, border_radius=6)
        pygame.draw.rect(surface, self.color_border, buy_rect, width=2, border_radius=6)
        buy_text = self.font.render("Buy", True, self.color_text)
        surface.blit(
            buy_text,
            (
                buy_rect.centerx - buy_text.get_width() // 2,
                buy_rect.centery - buy_text.get_height() // 2,
            ),
        )

        # Sell button
        sell_rect = pygame.Rect(start_x + button_w + button_spacing, y, button_w, button_h)
        sell_color = (120, 80, 80) if self.state.selected_side == "player" else (60, 60, 70)
        pygame.draw.rect(surface, sell_color, sell_rect, border_radius=6)
        pygame.draw.rect(surface, self.color_border, sell_rect, width=2, border_radius=6)
        sell_text = self.font.render("Sell", True, self.color_text)
        surface.blit(
            sell_text,
            (
                sell_rect.centerx - sell_text.get_width() // 2,
                sell_rect.centery - sell_text.get_height() // 2,
            ),
        )

        # Cancel button
        cancel_rect = pygame.Rect(start_x + (button_w + button_spacing) * 2, y, button_w, button_h)
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

    def handle_input(self, event: pygame.event.Event):
        """
        Handle input events.

        Returns:
            Tuple[action, index] or ("close", -1) when closing, None otherwise.
        """
        if not self.state.open:
            return None

        if event.type == pygame.KEYDOWN:
            # Arrow keys to navigate
            if event.key == pygame.K_LEFT:
                self.state.selected_side = "npc"
            elif event.key == pygame.K_RIGHT:
                self.state.selected_side = "player"
            elif event.key == pygame.K_UP:
                self.state.selected_index = max(0, self.state.selected_index - 1)
            elif event.key == pygame.K_DOWN:
                self.state.selected_index = min(7, self.state.selected_index + 1)
            elif event.key == pygame.K_RETURN:
                # Execute transaction
                if self.state.selected_side == "npc":
                    return ("buy", self.state.selected_index)
                else:
                    return ("sell", self.state.selected_index)
            elif event.key == pygame.K_ESCAPE:
                self.close()
                return ("close", -1)

        return None

    def handle_command(self, command, pressed_once: list[int]):
        """
        Handle input from command-based replay pipeline (keyboard-equivalent).

        Returns:
            Tuple[action, index] or ("close", -1) when closing, None otherwise.
        """
        if not self.state.open:
            return None

        left_edge = (
            pygame.K_LEFT in pressed_once
            or pygame.K_a in pressed_once
            or (getattr(command, "left", False) and not self._prev_left)
        )
        right_edge = (
            pygame.K_RIGHT in pressed_once
            or pygame.K_d in pressed_once
            or (getattr(command, "right", False) and not self._prev_right)
        )
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

        if left_edge:
            self.state.selected_side = "npc"
        elif right_edge:
            self.state.selected_side = "player"

        if up_edge:
            self.state.selected_index = max(0, self.state.selected_index - 1)
        elif down_edge:
            self.state.selected_index = min(7, self.state.selected_index + 1)

        result = None
        if confirm_edge:
            if self.state.selected_side == "npc":
                result = ("buy", self.state.selected_index)
            else:
                result = ("sell", self.state.selected_index)
        elif back_edge:
            self.close()
            result = ("close", -1)

        # Update edge trackers
        self._prev_left = getattr(command, "left", False)
        self._prev_right = getattr(command, "right", False)
        self._prev_up = getattr(command, "up", False)
        self._prev_down = getattr(command, "down", False)
        self._prev_confirm = getattr(command, "menu_confirm", False)
        self._prev_back = getattr(command, "menu_back", False)

        return result


# ============================================================
# Helper Functions
# ============================================================


def create_shop_ui() -> ShopUI:
    """Create a shop UI instance"""
    return ShopUI()
