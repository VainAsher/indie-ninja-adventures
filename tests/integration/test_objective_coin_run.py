"""
Integration-style test for coin collection objectives.

Verifies:
- ObjectiveTracker can start a mission with a collect_items (coin) objective
- ItemCollectedEvent updates progress
- All objectives complete after collecting required coins
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from game.objective_tracker import ObjectiveTracker, ItemCollectedEvent  # noqa: E402
from game.mission_registry import MissionRegistry  # noqa: E402
from core import EventBus  # noqa: E402


def test_coin_collection_objective_completes():
    bus = EventBus()
    tracker = ObjectiveTracker(bus)
    registry = MissionRegistry()

    mission = registry.get_mission("demo_coin_run")
    assert mission is not None, "demo_coin_run mission must exist"

    tracker.start_mission_objectives(mission.mission_id)
    assert tracker.get_active_objectives(), "Objectives should be active after start"

    # Collect 5 coins
    for _ in range(5):
        bus.emit(ItemCollectedEvent(item_id="coin", quantity=1, position=(0, 0)))
    bus.process()

    assert tracker.are_all_objectives_complete(), "All objectives should be complete after collecting coins"


if __name__ == "__main__":
    test_coin_collection_objective_completes()
    print("[PASS] Coin objective integration test")
