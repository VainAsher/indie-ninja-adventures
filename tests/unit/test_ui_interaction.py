"""
UI Interaction Tests

Tests for UI systems to ensure menu navigation, keyboard input,
and dialogue interactions work correctly.

Coverage:
- Menu navigation (up/down/select)
- Keyboard input handling
- Dialogue UI navigation
- Menu state management
- Input event processing

Test philosophy: Verify UI logic, not visual rendering
"""


import pygame
import pytest

from game.dialogue_system import DialogueChoice, DialogueNode
from ui.dialogue_ui import DialogueUI

# Import UI modules
from ui.menu_system import BaseMenu, MainMenu, MenuAction, PauseMenu

# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture(scope="module", autouse=True)
def pygame_init():
    """Initialize pygame once for all tests"""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def base_menu():
    """Create a simple base menu for testing"""
    menu = BaseMenu("Test Menu", 800, 600)
    menu.add_item("Start Game", MenuAction.START_GAME)
    menu.add_item("Settings", MenuAction.OPEN_SETTINGS)
    menu.add_item("Quit", MenuAction.QUIT_GAME)
    return menu


@pytest.fixture
def dialogue_ui():
    """Create a dialogue UI instance"""
    return DialogueUI(screen_width=800, screen_height=600)


@pytest.fixture
def sample_dialogue_node():
    """Create a sample dialogue node"""
    return DialogueNode(
        node_id="test_node",
        speaker="Elder",
        text="Welcome, young ninja. What brings you here?",
        choices=["ask_about_mission", "ask_about_village", "leave"],
    )


@pytest.fixture
def sample_dialogue_choices():
    """Create sample dialogue choices"""
    return [
        DialogueChoice(choice_text="Tell me about the mission", next_node_id="mission_info"),
        DialogueChoice(choice_text="What happened to the village?", next_node_id="village_info"),
        DialogueChoice(choice_text="I must go", next_node_id="goodbye"),
    ]


# ============================================================
# Menu Navigation Tests
# ============================================================


def test_menu_initialization(base_menu):
    """Test menu can be initialized"""
    assert base_menu is not None
    assert base_menu.title == "Test Menu"
    assert len(base_menu.items) == 3
    assert base_menu.selected_index == 0
    print("[PASS] Menu initialization")


def test_menu_add_item(base_menu):
    """Test adding menu items"""
    initial_count = len(base_menu.items)
    base_menu.add_item("Help", MenuAction.BACK)
    assert len(base_menu.items) == initial_count + 1
    assert base_menu.items[-1].label == "Help"
    assert base_menu.items[-1].action == MenuAction.BACK
    print("[PASS] Menu add item")


def test_menu_navigate_down(base_menu):
    """Test navigating down through menu"""
    base_menu.selected_index = 0
    base_menu.navigate_down()
    assert base_menu.selected_index == 1

    base_menu.navigate_down()
    assert base_menu.selected_index == 2
    print("[PASS] Menu navigate down")


def test_menu_navigate_down_wraps(base_menu):
    """Test navigating down wraps to top"""
    base_menu.selected_index = 2  # Last item
    base_menu.navigate_down()
    assert base_menu.selected_index == 0  # Wrapped to first
    print("[PASS] Menu navigate down wraps")


def test_menu_navigate_up(base_menu):
    """Test navigating up through menu"""
    base_menu.selected_index = 2
    base_menu.navigate_up()
    assert base_menu.selected_index == 1

    base_menu.navigate_up()
    assert base_menu.selected_index == 0
    print("[PASS] Menu navigate up")


def test_menu_navigate_up_wraps(base_menu):
    """Test navigating up wraps to bottom"""
    base_menu.selected_index = 0  # First item
    base_menu.navigate_up()
    assert base_menu.selected_index == 2  # Wrapped to last
    print("[PASS] Menu navigate up wraps")


def test_menu_select_current(base_menu):
    """Test selecting current menu item"""
    base_menu.selected_index = 0
    action = base_menu.select_current()
    assert action == MenuAction.START_GAME

    base_menu.selected_index = 1
    action = base_menu.select_current()
    assert action == MenuAction.OPEN_SETTINGS

    base_menu.selected_index = 2
    action = base_menu.select_current()
    assert action == MenuAction.QUIT_GAME
    print("[PASS] Menu select current")


def test_menu_disabled_item_skipped():
    """Test navigation skips disabled items"""
    menu = BaseMenu("Test", 800, 600)
    menu.add_item("Item 1", MenuAction.NONE, enabled=True)
    menu.add_item("Item 2", MenuAction.NONE, enabled=False)  # Disabled
    menu.add_item("Item 3", MenuAction.NONE, enabled=True)

    menu.selected_index = 0
    menu.navigate_down()
    # Should skip disabled item 2 and go to item 3
    assert menu.selected_index == 2
    print("[PASS] Menu skips disabled items")


def test_menu_select_disabled_returns_none():
    """Test selecting disabled item returns NONE"""
    menu = BaseMenu("Test", 800, 600)
    menu.add_item("Disabled", MenuAction.START_GAME, enabled=False)

    menu.selected_index = 0
    action = menu.select_current()
    assert action == MenuAction.NONE
    print("[PASS] Menu select disabled returns NONE")


def test_menu_callback_called():
    """Test menu item callback is called on selection"""
    callback_called = []

    def test_callback():
        callback_called.append(True)

    menu = BaseMenu("Test", 800, 600)
    menu.add_item("Test", MenuAction.NONE, callback=test_callback)

    menu.selected_index = 0
    menu.select_current()

    assert len(callback_called) == 1
    print("[PASS] Menu callback called")


def test_menu_empty_navigation():
    """Test navigation with empty menu"""
    menu = BaseMenu("Empty", 800, 600)

    # Should not crash with empty menu
    menu.navigate_up()
    menu.navigate_down()
    action = menu.select_current()

    assert action == MenuAction.NONE
    print("[PASS] Menu empty navigation")


# ============================================================
# Main Menu Tests
# ============================================================


def test_main_menu_initialization():
    """Test MainMenu can be initialized"""
    menu = MainMenu(800, 600)
    assert menu is not None
    assert menu.title == "NINJA DASH"
    assert len(menu.items) > 0
    print("[PASS] MainMenu initialization")


def test_main_menu_has_start_option():
    """Test MainMenu has start game option"""
    menu = MainMenu(800, 600)

    # Check that START_GAME action exists
    has_start = any(item.action == MenuAction.START_GAME for item in menu.items)
    assert has_start
    print("[PASS] MainMenu has start option")


def test_main_menu_has_quit_option():
    """Test MainMenu has quit option"""
    menu = MainMenu(800, 600)

    # Check that QUIT_GAME action exists
    has_quit = any(item.action == MenuAction.QUIT_GAME for item in menu.items)
    assert has_quit
    print("[PASS] MainMenu has quit option")


# ============================================================
# Pause Menu Tests
# ============================================================


def test_pause_menu_initialization():
    """Test PauseMenu can be initialized"""
    menu = PauseMenu(800, 600)
    assert menu is not None
    assert menu.title == "PAUSED"
    assert len(menu.items) > 0
    print("[PASS] PauseMenu initialization")


def test_pause_menu_has_resume_option():
    """Test PauseMenu has resume option"""
    menu = PauseMenu(800, 600)

    # Check that RESUME_GAME action exists
    has_resume = any(item.action == MenuAction.RESUME_GAME for item in menu.items)
    assert has_resume
    print("[PASS] PauseMenu has resume option")


def test_pause_menu_has_quit_to_menu_option():
    """Test PauseMenu has quit to menu option"""
    menu = PauseMenu(800, 600)

    # Check that QUIT_TO_MENU action exists
    has_quit_to_menu = any(item.action == MenuAction.QUIT_TO_MENU for item in menu.items)
    assert has_quit_to_menu
    print("[PASS] PauseMenu has quit to menu option")


# ============================================================
# Dialogue UI Tests
# ============================================================


def test_dialogue_ui_initialization(dialogue_ui):
    """Test DialogueUI can be initialized"""
    assert dialogue_ui is not None
    assert dialogue_ui.screen_width == 800
    assert dialogue_ui.screen_height == 600
    assert dialogue_ui.selected_choice_index == 0
    print("[PASS] DialogueUI initialization")


def test_dialogue_ui_handle_input_down(dialogue_ui, sample_dialogue_choices):
    """Test handling DOWN arrow key in dialogue"""
    dialogue_ui.selected_choice_index = 0
    result = dialogue_ui.handle_input([pygame.K_DOWN], sample_dialogue_choices)
    assert dialogue_ui.selected_choice_index == 1
    assert result is None  # No selection, just navigation
    print("[PASS] DialogueUI handle input down")


def test_dialogue_ui_handle_input_down_at_bottom(dialogue_ui, sample_dialogue_choices):
    """Test DOWN key at bottom choice (should not wrap)"""
    dialogue_ui.selected_choice_index = len(sample_dialogue_choices) - 1
    result = dialogue_ui.handle_input([pygame.K_DOWN], sample_dialogue_choices)
    # Should stay at last item (doesn't wrap)
    assert dialogue_ui.selected_choice_index == len(sample_dialogue_choices) - 1
    print("[PASS] DialogueUI handle input down at bottom")


def test_dialogue_ui_handle_input_up(dialogue_ui, sample_dialogue_choices):
    """Test handling UP arrow key in dialogue"""
    dialogue_ui.selected_choice_index = 2
    result = dialogue_ui.handle_input([pygame.K_UP], sample_dialogue_choices)
    assert dialogue_ui.selected_choice_index == 1
    assert result is None
    print("[PASS] DialogueUI handle input up")


def test_dialogue_ui_handle_input_up_at_top(dialogue_ui, sample_dialogue_choices):
    """Test UP key at top choice (should not wrap)"""
    dialogue_ui.selected_choice_index = 0
    result = dialogue_ui.handle_input([pygame.K_UP], sample_dialogue_choices)
    # Should stay at first item (doesn't wrap)
    assert dialogue_ui.selected_choice_index == 0
    print("[PASS] DialogueUI handle input up at top")


def test_dialogue_ui_handle_input_select(dialogue_ui, sample_dialogue_choices):
    """Test selecting dialogue choice with ENTER"""
    dialogue_ui.selected_choice_index = 1
    result = dialogue_ui.handle_input([pygame.K_RETURN], sample_dialogue_choices)
    assert result == "select_1"
    print("[PASS] DialogueUI handle input select")


def test_dialogue_ui_reset_selection(dialogue_ui):
    """Test resetting dialogue selection"""
    dialogue_ui.selected_choice_index = 5
    dialogue_ui.reset_selection()
    assert dialogue_ui.selected_choice_index == 0
    print("[PASS] DialogueUI reset selection")


def test_dialogue_ui_no_choices():
    """Test DialogueUI with no choices (simple continue dialogue)"""
    ui = DialogueUI()
    ui.selected_choice_index = 0

    # With empty choices, should handle gracefully
    empty_choices = []
    result = ui.handle_input([pygame.K_DOWN], empty_choices)
    # Should not crash and index should remain 0
    assert ui.selected_choice_index == 0
    assert result is None
    print("[PASS] DialogueUI handles no choices")


# ============================================================
# Input Handling Tests
# ============================================================


def test_menu_render_no_crash():
    """Test menu rendering doesn't crash"""
    menu = BaseMenu("Test", 800, 600)
    menu.add_item("Test 1", MenuAction.NONE)
    menu.add_item("Test 2", MenuAction.NONE)

    surface = pygame.Surface((800, 600))
    menu.render(surface)
    # No crash = success
    print("[PASS] Menu render no crash")


def test_dialogue_ui_render_no_crash(dialogue_ui, sample_dialogue_node, sample_dialogue_choices):
    """Test dialogue UI rendering doesn't crash"""
    surface = pygame.Surface((800, 600))
    dialogue_ui.render(surface, sample_dialogue_node, sample_dialogue_choices)
    # No crash = success
    print("[PASS] DialogueUI render no crash")


def test_dialogue_ui_render_no_choices(dialogue_ui, sample_dialogue_node):
    """Test dialogue UI rendering with no choices"""
    surface = pygame.Surface((800, 600))
    dialogue_ui.render(surface, sample_dialogue_node, [])
    # No crash = success
    print("[PASS] DialogueUI render no choices")


# ============================================================
# Edge Cases
# ============================================================


def test_menu_single_item():
    """Test menu with single item"""
    menu = BaseMenu("Single", 800, 600)
    menu.add_item("Only Option", MenuAction.START_GAME)

    # Navigation should stay on same item
    menu.navigate_up()
    assert menu.selected_index == 0
    menu.navigate_down()
    assert menu.selected_index == 0

    action = menu.select_current()
    assert action == MenuAction.START_GAME
    print("[PASS] Menu single item")


def test_menu_all_disabled():
    """Test menu with all disabled items"""
    menu = BaseMenu("All Disabled", 800, 600)
    menu.add_item("Item 1", MenuAction.NONE, enabled=False)
    menu.add_item("Item 2", MenuAction.NONE, enabled=False)
    menu.add_item("Item 3", MenuAction.NONE, enabled=False)

    menu.selected_index = 0
    menu.navigate_down()
    # Will cycle through all items (even disabled) due to implementation
    # But selection will return NONE
    action = menu.select_current()
    assert action == MenuAction.NONE
    print("[PASS] Menu all disabled")


def test_dialogue_single_choice(dialogue_ui):
    """Test dialogue with single choice"""
    single_choice = [DialogueChoice(choice_text="Continue", next_node_id="next")]

    dialogue_ui.selected_choice_index = 0

    # Try navigating down (should stay at 0 since there's only one choice)
    result = dialogue_ui.handle_input([pygame.K_DOWN], single_choice)
    assert dialogue_ui.selected_choice_index == 0
    assert result is None

    # Select the choice
    result = dialogue_ui.handle_input([pygame.K_RETURN], single_choice)
    assert result == "select_0"
    print("[PASS] Dialogue single choice")


# ============================================================
# Integration Tests
# ============================================================


def test_menu_full_navigation_cycle():
    """Test complete navigation cycle through menu"""
    menu = BaseMenu("Cycle Test", 800, 600)
    menu.add_item("Item 1", MenuAction.NONE)
    menu.add_item("Item 2", MenuAction.NONE)
    menu.add_item("Item 3", MenuAction.NONE)

    # Start at top
    menu.selected_index = 0

    # Navigate down through all items
    positions = []
    for _ in range(5):
        positions.append(menu.selected_index)
        menu.navigate_down()

    # Should cycle: 0 -> 1 -> 2 -> 0 -> 1 -> 2
    assert positions == [0, 1, 2, 0, 1]
    print("[PASS] Menu full navigation cycle")


def test_dialogue_full_navigation_cycle(dialogue_ui, sample_dialogue_choices):
    """Test complete navigation through dialogue choices"""
    choice_count = len(sample_dialogue_choices)

    # Start at top
    dialogue_ui.selected_choice_index = 0

    # Navigate down through all choices
    positions = []
    for _ in range(choice_count):
        positions.append(dialogue_ui.selected_choice_index)
        dialogue_ui.handle_input([pygame.K_DOWN], sample_dialogue_choices)

    # Should go: 0 -> 1 -> 2 (then stay at 2 since DialogueUI doesn't wrap)
    assert positions == [0, 1, 2]
    assert dialogue_ui.selected_choice_index == 2  # Stayed at bottom
    print("[PASS] Dialogue full navigation cycle")


def test_multiple_menus_independence():
    """Test multiple menus maintain independent state"""
    menu1 = BaseMenu("Menu 1", 800, 600)
    menu1.add_item("Item A", MenuAction.NONE)
    menu1.add_item("Item B", MenuAction.NONE)

    menu2 = BaseMenu("Menu 2", 800, 600)
    menu2.add_item("Item X", MenuAction.NONE)
    menu2.add_item("Item Y", MenuAction.NONE)
    menu2.add_item("Item Z", MenuAction.NONE)

    # Navigate menu1
    menu1.selected_index = 0
    menu1.navigate_down()
    assert menu1.selected_index == 1

    # menu2 should be unaffected
    assert menu2.selected_index == 0

    # Navigate menu2
    menu2.navigate_down()
    menu2.navigate_down()
    assert menu2.selected_index == 2

    # menu1 should still be at 1
    assert menu1.selected_index == 1
    print("[PASS] Multiple menus independence")


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
