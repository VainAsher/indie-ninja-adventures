"""
Multiplayer wire protocol — length-prefixed msgpack frames over TCP.

Format: [4 bytes big-endian uint32: payload length][msgpack binary body]

Switched from JSON to msgpack in v0.8.8 for ~65% packet size reduction.
All I/O is async (asyncio StreamReader/StreamWriter).
Message encoding/decoding is pure-data and independently testable.

PROTOCOL_VERSION must match between client and server.  A version mismatch
is logged as a warning (lenient mode) but the incompatible wire format will
cause a decode error and disconnect regardless.
"""

import asyncio
import struct
from dataclasses import dataclass
from typing import Any

import msgpack

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

HEADER_SIZE = 4          # 4-byte big-endian uint32
MAX_MESSAGE_BYTES = 1_048_576  # 1 MB safety cap
PROTOCOL_VERSION = "2"   # bump when wire format changes (1 = JSON, 2 = msgpack)


# ──────────────────────────────────────────────────────────────────────────────
# Message types
# ──────────────────────────────────────────────────────────────────────────────

class MessageType:
    # Client → Server
    CLIENT_HELLO  = "client_hello"   # {player_id, version}
    INPUT         = "input"          # InputCommand.to_dict()
    # Phase 2.5: client notifies server of a world-state event (pickup collected,
    # enemy killed, platform triggered).  Server rebroadcasts to all other clients
    # so each simulation can apply the same mutation deterministically.
    # etype values: "pickup_collect", "enemy_kill", "platform_trigger"
    ENTITY_EVENT  = "entity_event"   # {etype, entity_id, slot, data?}

    # Server → Client
    SERVER_HELLO      = "server_hello"      # {player_id, slot, frame, seed, max_players}
    SERVER_STATE      = "server_state"      # MultiplayerSnapshot.to_dict()
    WORLD_STATE       = "world_state"       # WorldSnapshot.to_dict() — Phase 3 authoritative broadcast
    PLAYER_JOIN       = "player_join"       # {player_id, slot}
    PLAYER_LEAVE      = "player_leave"      # {player_id, slot}
    LOBBY_UPDATE      = "lobby_update"      # {connected: int, max: int, players: [{player_id, slot}]}
    GAME_START        = "game_start"        # {seed: int}
    ERROR             = "error"             # {code, message}
    # Phase 4 — instanced zones
    WORLD_TRANSITION  = "world_transition"  # {hub_id, seed, shape, rooms, world_seed, spawn_x, spawn_y}
    ZONE_PRESENCE     = "zone_presence"     # {player_id, slot, hub_id, action: "arrived"|"departed"}

    # Phase 4 — Client → Server (portal travel request)
    PORTAL_TRAVEL     = "portal_travel"     # {destination_id, portal_id}


# ──────────────────────────────────────────────────────────────────────────────
# Message dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Message:
    type: str
    payload: dict[str, Any]

    def encode(self) -> bytes:
        """Encode to length-prefixed msgpack bytes ready for the wire."""
        body = msgpack.packb(
            {"type": self.type, "payload": self.payload},
            use_bin_type=True,
        )
        return struct.pack(">I", len(body)) + body

    @classmethod
    def decode(cls, data: bytes) -> "Message":
        """Decode from raw msgpack bytes (no length header)."""
        obj = msgpack.unpackb(data, raw=False)
        return cls(type=obj["type"], payload=obj.get("payload", {}))


# ──────────────────────────────────────────────────────────────────────────────
# Async I/O helpers
# ──────────────────────────────────────────────────────────────────────────────

async def read_message(reader: asyncio.StreamReader) -> Message:
    """
    Read one length-prefixed message from an asyncio StreamReader.

    Raises:
        asyncio.IncompleteReadError  — connection closed mid-message
        ValueError                   — message exceeds MAX_MESSAGE_BYTES or malformed
    """
    header = await reader.readexactly(HEADER_SIZE)
    length = struct.unpack(">I", header)[0]
    if length > MAX_MESSAGE_BYTES:
        raise ValueError(f"Incoming message too large: {length} bytes")
    body = await reader.readexactly(length)
    try:
        return Message.decode(body)
    except (msgpack.UnpackException, msgpack.UnpackValueError, KeyError,
            TypeError, ValueError) as exc:
        raise ValueError(f"Malformed message ({len(body)} bytes): {exc}") from exc


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


def encode_message(msg_type: str, payload: dict[str, Any]) -> bytes:
    """
    Encode a message to wire bytes without sending.

    Use this when broadcasting the same payload to multiple writers — encode
    once, then pass the result to write_encoded() for each writer rather than
    re-encoding N times.
    """
    return Message(type=msg_type, payload=payload).encode()


async def write_encoded(writer: asyncio.StreamWriter, encoded: bytes) -> None:
    """
    Write pre-encoded bytes to a StreamWriter and flush.

    Pair with encode_message() for zero-copy multi-client broadcast.
    """
    writer.write(encoded)
    await writer.drain()
