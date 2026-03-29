"""
Multiplayer wire protocol — length-prefixed JSON frames over TCP.

Format: [4 bytes big-endian uint32: payload length][UTF-8 JSON body]

All I/O is async (asyncio StreamReader/StreamWriter).
Message encoding/decoding is pure-data and independently testable.
"""

import asyncio
import json
import struct
from dataclasses import dataclass
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

HEADER_SIZE = 4          # 4-byte big-endian uint32
MAX_MESSAGE_BYTES = 1_048_576  # 1 MB safety cap


# ──────────────────────────────────────────────────────────────────────────────
# Message types
# ──────────────────────────────────────────────────────────────────────────────

class MessageType:
    # Client → Server
    CLIENT_HELLO = "client_hello"   # {player_id, version}
    INPUT        = "input"          # InputCommand.to_dict()

    # Server → Client
    SERVER_HELLO  = "server_hello"   # {player_id, slot, frame, seed, max_players}
    SERVER_STATE  = "server_state"   # MultiplayerSnapshot.to_dict()
    PLAYER_JOIN   = "player_join"    # {player_id, slot}
    PLAYER_LEAVE  = "player_leave"   # {player_id, slot}
    LOBBY_UPDATE  = "lobby_update"   # {connected: int, max: int, players: [{player_id, slot}]}
    GAME_START    = "game_start"     # {seed: int}
    ERROR         = "error"          # {code, message}


# ──────────────────────────────────────────────────────────────────────────────
# Message dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Message:
    type: str
    payload: dict[str, Any]

    def encode(self) -> bytes:
        """Encode to length-prefixed bytes ready for the wire."""
        body = json.dumps(
            {"type": self.type, "payload": self.payload},
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return struct.pack(">I", len(body)) + body

    @classmethod
    def decode(cls, data: bytes) -> "Message":
        """Decode from raw JSON bytes (no length header)."""
        obj = json.loads(data.decode("utf-8"))
        return cls(type=obj["type"], payload=obj.get("payload", {}))


# ──────────────────────────────────────────────────────────────────────────────
# Async I/O helpers
# ──────────────────────────────────────────────────────────────────────────────

async def read_message(reader: asyncio.StreamReader) -> Message:
    """
    Read one length-prefixed message from an asyncio StreamReader.

    Raises:
        asyncio.IncompleteReadError  — connection closed mid-message
        ValueError                   — message exceeds MAX_MESSAGE_BYTES
    """
    header = await reader.readexactly(HEADER_SIZE)
    length = struct.unpack(">I", header)[0]
    if length > MAX_MESSAGE_BYTES:
        raise ValueError(f"Incoming message too large: {length} bytes")
    body = await reader.readexactly(length)
    return Message.decode(body)


async def write_message(
    writer: asyncio.StreamWriter, msg_type: str, payload: dict[str, Any]
) -> None:
    """
    Write one length-prefixed message to an asyncio StreamWriter.
    Calls drain() to flush the write buffer.
    """
    msg = Message(type=msg_type, payload=payload)
    writer.write(msg.encode())
    await writer.drain()
