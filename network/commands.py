"""
Input command representation and deterministic serialization.
"""

from dataclasses import asdict, dataclass
from typing import Any

import pygame


@dataclass
class InputCommand:
    frame: int
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    jump: bool = False
    dash: bool = False
    crouch: bool = False
    toggle_proc: bool = False
    cycle_camera: bool = False
    attack: bool = False  # J: melee combo/air slash
    throw: bool = False  # K: shuriken throw
    teleport: bool = False  # F (phase blink)
    ninjutsu: bool = False  # L/Q hold
    interact: bool = False  # E: context action
    inventory: bool = False  # I: inventory UI toggle
    consumable: bool = False  # R: quick-use item
    minimap: bool = False  # Tab: minimap toggle
    fullmap: bool = False  # M: full map toggle
    controls_overlay: bool = False  # H: controls hint toggle
    debug_overlay: bool = False  # F3: debug overlay toggle
    slow_walk: bool = False  # Alt: slow walk/ninja side walk
    menu_confirm: bool = False  # Enter/Return: menu accept/advance
    menu_back: bool = False  # Escape: menu back/pause

    @classmethod
    def from_keys(cls, keys, frame: int) -> "InputCommand":
        """Build a command from a pygame key state or compatible object."""
        return cls(
            frame=frame,
            up=keys[pygame.K_UP] or keys[pygame.K_w],
            down=keys[pygame.K_DOWN] or keys[pygame.K_s],
            left=keys[pygame.K_LEFT] or keys[pygame.K_a],
            right=keys[pygame.K_RIGHT] or keys[pygame.K_d],
            jump=keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP],
            dash=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            crouch=keys[pygame.K_DOWN] or keys[pygame.K_s],
            toggle_proc=keys[pygame.K_p],
            cycle_camera=keys[pygame.K_c],
            attack=keys[pygame.K_j],
            throw=keys[pygame.K_k],
            teleport=keys[pygame.K_f],
            ninjutsu=keys[pygame.K_l] or keys[pygame.K_q],
            interact=keys[pygame.K_e],
            inventory=keys[pygame.K_i],
            consumable=keys[pygame.K_r],
            minimap=keys[pygame.K_TAB],
            fullmap=keys[pygame.K_m],
            controls_overlay=keys[pygame.K_h],
            debug_overlay=keys[pygame.K_F3],
            slow_walk=keys[pygame.K_LALT] or keys[pygame.K_RALT],
            menu_confirm=keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER],
            menu_back=keys[pygame.K_ESCAPE],
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # ensure deterministic ordering by constructing an ordered dict manually
        ordered_keys = [
            "frame",
            "up",
            "down",
            "left",
            "right",
            "jump",
            "dash",
            "crouch",
            "toggle_proc",
            "cycle_camera",
            "attack",
            "throw",
            "teleport",
            "ninjutsu",
            "interact",
            "inventory",
            "consumable",
            "minimap",
            "fullmap",
            "controls_overlay",
            "debug_overlay",
            "slow_walk",
            "menu_confirm",
            "menu_back",
        ]
        return {k: data[k] for k in ordered_keys}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InputCommand":
        return cls(
            frame=int(data["frame"]),
            up=bool(data.get("up", False)),
            down=bool(data.get("down", False)),
            left=bool(data.get("left", False)),
            right=bool(data.get("right", False)),
            jump=bool(data.get("jump", False)),
            dash=bool(data.get("dash", False)),
            crouch=bool(data.get("crouch", False)),
            toggle_proc=bool(data.get("toggle_proc", False)),
            cycle_camera=bool(data.get("cycle_camera", False)),
            attack=bool(data.get("attack", False)),
            throw=bool(data.get("throw", False)),
            teleport=bool(data.get("teleport", False)),
            ninjutsu=bool(data.get("ninjutsu", False)),
            interact=bool(data.get("interact", False)),
            inventory=bool(data.get("inventory", False)),
            consumable=bool(data.get("consumable", False)),
            minimap=bool(data.get("minimap", False)),
            fullmap=bool(data.get("fullmap", False)),
            controls_overlay=bool(data.get("controls_overlay", False)),
            debug_overlay=bool(data.get("debug_overlay", False)),
            slow_walk=bool(data.get("slow_walk", False)),
            menu_confirm=bool(data.get("menu_confirm", False)),
            menu_back=bool(data.get("menu_back", False)),
        )
