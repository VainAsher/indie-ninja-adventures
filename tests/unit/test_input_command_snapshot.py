import json

import pygame

from network.commands import InputCommand
from network.snapshots import Snapshot


class FakeKeys:
    def __init__(self, pressed):
        self.pressed = set(pressed)

    def __getitem__(self, key):
        return key in self.pressed


def test_input_command_from_keys_and_serialization():
    pressed = {pygame.K_LEFT, pygame.K_SPACE, pygame.K_c}
    cmd = InputCommand.from_keys(FakeKeys(pressed), frame=5)

    assert cmd.frame == 5
    assert cmd.left is True
    assert cmd.jump is True
    assert cmd.cycle_camera is True
    assert cmd.right is False

    encoded = json.dumps(cmd.to_dict(), sort_keys=True, separators=(",", ":"))
    assert (
        encoded
        == '{"attack":false,"consumable":false,"controls_overlay":false,"crouch":false,"cycle_camera":true,"dash":false,"debug_overlay":false,"down":false,"frame":5,"fullmap":false,"interact":false,"inventory":false,"jump":true,"left":true,"menu_back":false,"menu_confirm":false,"minimap":false,"ninjutsu":false,"right":false,"slow_walk":false,"teleport":false,"throw":false,"toggle_proc":false,"up":false}'
    )

    decoded = InputCommand.from_dict(cmd.to_dict())
    assert decoded == cmd


def test_snapshot_roundtrip_deterministic_order():
    snap = Snapshot(
        frame=12,
        seed=12345,
        player_pos=(100.5, 200.25),
        player_vel=(1.0, -2.0),
        metadata={"mode": "PROCEDURAL"},
    )
    snap_dict = snap.to_dict()
    encoded = json.dumps(snap_dict, sort_keys=True, separators=(",", ":"))
    assert (
        encoded
        == '{"frame":12,"metadata":{"mode":"PROCEDURAL"},"player_pos":[100.5,200.25],"player_vel":[1.0,-2.0],"seed":12345}'
    )

    decoded = Snapshot.from_dict(snap_dict)
    assert decoded == snap
