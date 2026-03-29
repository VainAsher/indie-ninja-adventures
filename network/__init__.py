"""
Network layer for Vain Asher Gaming's: Indie Ninja Adventures

Foundation for client/server multiplayer:
- Input command pattern
- State serialization/snapshots
- Network protocol
- Deterministic replay
"""

from .commands import InputCommand
from .input_pipeline import CommandKeyView, InputPipeline
from .protocol import Message, MessageType
from .snapshots import MultiplayerSnapshot, PlayerState, Snapshot

__all__ = [
    "InputCommand",
    "Snapshot",
    "InputPipeline",
    "CommandKeyView",
    "Message",
    "MessageType",
    "PlayerState",
    "MultiplayerSnapshot",
]
