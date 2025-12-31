"""
Input command pipeline for live, record, and replay flows.

Provides:
- CommandKeyView: key-like interface backed by InputCommand
- InputPipeline: unified read/record/replay handling with metadata serialization
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple
import pygame

from .commands import InputCommand


class CommandKeyView:
    """Key-like adapter that exposes an InputCommand via __getitem__ for pygame-style access."""

    def __init__(self, command: InputCommand):
        self.command = command

    def __getitem__(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_w):
            return self.command.up
        if key in (pygame.K_DOWN, pygame.K_s):
            return self.command.down
        if key in (pygame.K_LEFT,):
            return self.command.left
        if key in (pygame.K_RIGHT,):
            return self.command.right
        if key in (pygame.K_SPACE,):
            return self.command.jump
        if key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            return self.command.dash
        if key in (pygame.K_c,):
            return self.command.cycle_camera
        if key in (pygame.K_p,):
            return self.command.toggle_proc
        if key in (pygame.K_j,):
            return self.command.attack
        if key in (pygame.K_k,):
            return self.command.throw
        if key in (pygame.K_f,):
            return self.command.teleport
        if key in (pygame.K_l, pygame.K_q):
            return self.command.ninjutsu
        if key in (pygame.K_e,):
            return self.command.interact
        if key in (pygame.K_i,):
            return self.command.inventory
        if key in (pygame.K_r,):
            return self.command.consumable
        if key in (pygame.K_TAB,):
            return self.command.minimap
        if key in (pygame.K_m,):
            return self.command.fullmap
        if key in (pygame.K_h,):
            return getattr(self.command, "controls_overlay", False)
        if key in (pygame.K_F3,):
            return self.command.debug_overlay
        if key in (pygame.K_LALT, pygame.K_RALT):
            return self.command.slow_walk
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return getattr(self.command, "menu_confirm", False)
        if key in (pygame.K_ESCAPE,):
            return getattr(self.command, "menu_back", False)
        # Crouch shares down keys
        return False


class InputPipeline:
    """
    Unified input pipeline for live input, recording, and replay.

    Usage:
        pipeline = InputPipeline(record_path=..., replay_path=..., metadata={...})
        keys_like, command = pipeline.next(raw_keys, frame_idx)
        ...
        pipeline.finalize()
    """

    def __init__(
        self,
        record_path: Optional[str] = None,
        replay_path: Optional[str] = None,
        metadata: Optional[Dict] = None,
        log_commands: bool = False,
        log_path: Optional[str] = None,
    ):
        self.record_path = record_path
        self.replay_path = replay_path
        self.metadata = metadata or {}
        self.log_commands = log_commands
        self.log_path = Path(log_path) if log_path else None

        self._recording: list[dict] = []
        self._replay_commands = []
        self._replay_index = 0
        self._log_buffer: list[dict] = []
        self._terminated_frame = self.metadata.get("terminated_frame")
        self._replay_done = False

        if replay_path:
            data = json.loads(Path(replay_path).read_text(encoding="utf-8"))
            commands = data.get("commands", [])
            self._replay_commands = [InputCommand.from_dict(cmd) for cmd in commands]
            # allow metadata override from file when present
            self.metadata = {**data, **self.metadata}
            self._terminated_frame = self.metadata.get("terminated_frame")

    def next(
        self,
        keys_state,
        frame: int,
        keydown_keys: Optional[set[int]] = None,
    ) -> Tuple[object, InputCommand]:
        """
        Return a key-like object and the InputCommand for this frame.

        - Replay: returns CommandKeyView for the stored command
        - Live: builds a command from keys_state and records if enabled
        """
        if self._replay_commands:
            if self._replay_index < len(self._replay_commands):
                command = self._replay_commands[self._replay_index]
            else:
                command = InputCommand(frame=frame)
                self._replay_done = True
            self._replay_index += 1
            self._log(command)
            return CommandKeyView(command), command

        command = InputCommand.from_keys(keys_state, frame=frame)
        if keydown_keys:
            self._apply_keydown(command, keydown_keys)
        if self.record_path is not None:
            self._recording.append(command.to_dict())
        self._log(command)
        return keys_state, command

    def finalize(self):
        """Persist recorded commands to disk if recording."""
        if self.record_path and self._recording:
            payload = {**self.metadata, "commands": self._recording}
            Path(self.record_path).write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        if self.log_commands and self._log_buffer and self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("w", encoding="utf-8") as f:
                for cmd in self._log_buffer:
                    f.write(json.dumps(cmd, separators=(",", ":")) + "\n")

    def _log(self, command: InputCommand):
        """Append command to log buffer if logging enabled."""
        if self.log_commands:
            self._log_buffer.append(command.to_dict())

    def _apply_keydown(self, command: InputCommand, keydown_keys: set[int]) -> None:
        """Apply KEYDOWN edges to a command so short taps are captured."""
        if pygame.K_UP in keydown_keys or pygame.K_w in keydown_keys:
            command.up = True
        if pygame.K_DOWN in keydown_keys or pygame.K_s in keydown_keys:
            command.down = True
        if pygame.K_LEFT in keydown_keys or pygame.K_a in keydown_keys:
            command.left = True
        if pygame.K_RIGHT in keydown_keys or pygame.K_d in keydown_keys:
            command.right = True
        if pygame.K_SPACE in keydown_keys or pygame.K_w in keydown_keys or pygame.K_UP in keydown_keys:
            command.jump = True
        if pygame.K_LSHIFT in keydown_keys or pygame.K_RSHIFT in keydown_keys:
            command.dash = True
        if pygame.K_DOWN in keydown_keys or pygame.K_s in keydown_keys:
            command.crouch = True
        if pygame.K_p in keydown_keys:
            command.toggle_proc = True
        if pygame.K_c in keydown_keys:
            command.cycle_camera = True
        if pygame.K_j in keydown_keys:
            command.attack = True
        if pygame.K_k in keydown_keys:
            command.throw = True
        if pygame.K_f in keydown_keys:
            command.teleport = True
        if pygame.K_l in keydown_keys or pygame.K_q in keydown_keys:
            command.ninjutsu = True
        if pygame.K_e in keydown_keys:
            command.interact = True
        if pygame.K_i in keydown_keys:
            command.inventory = True
        if pygame.K_r in keydown_keys:
            command.consumable = True
        if pygame.K_TAB in keydown_keys:
            command.minimap = True
        if pygame.K_m in keydown_keys:
            command.fullmap = True
        if pygame.K_h in keydown_keys:
            command.controls_overlay = True
        if pygame.K_F3 in keydown_keys:
            command.debug_overlay = True
        if pygame.K_LALT in keydown_keys or pygame.K_RALT in keydown_keys:
            command.slow_walk = True
        if pygame.K_RETURN in keydown_keys or pygame.K_KP_ENTER in keydown_keys:
            command.menu_confirm = True
        if pygame.K_ESCAPE in keydown_keys:
            command.menu_back = True

    def is_replay_exhausted(self, frame: int) -> bool:
        """
        True when replay commands are exhausted and (if set) the terminated_frame has been reached.
        """
        if self.replay_path is None:
            return False
        if self._terminated_frame is not None and frame >= self._terminated_frame:
            return True
        return self._replay_done

    def get_terminated_frame(self) -> Optional[int]:
        """Return the recorded termination frame if present."""
        return self._terminated_frame
