"""
tests/unit/test_network_protocol.py

Unit tests for network/protocol.py — message encoding, decoding, the
async read_message / write_message helpers, and MessageType constants.

No running server, no pygame, no network connections.
asyncio.StreamReader.feed_data() is used to push bytes into the reader
in-process so read_message() can be tested without a live socket.
"""

import asyncio
import struct
import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import msgpack

from network.protocol import (
    HEADER_SIZE,
    MAX_MESSAGE_BYTES,
    PROTOCOL_VERSION,
    Message,
    MessageType,
    encode_message,
    read_message,
    write_message,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    """Run a coroutine synchronously in a fresh event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _feed_reader(encoded: bytes) -> asyncio.StreamReader:
    """Return a StreamReader pre-loaded with *encoded* bytes."""
    reader = asyncio.StreamReader()
    reader.feed_data(encoded)
    return reader


class _MemoryWriter:
    """Minimal StreamWriter substitute that captures written bytes."""

    def __init__(self):
        self._buf = bytearray()
        self.is_closing_called = False

    def write(self, data: bytes) -> None:
        self._buf.extend(data)

    async def drain(self) -> None:
        pass  # no-op

    def get_value(self) -> bytes:
        return bytes(self._buf)


# ── Message encode / decode ───────────────────────────────────────────────────

def test_message_encode_decode_roundtrip():
    payload = {"player_id": "abc", "slot": 1, "frame": 42}
    msg = Message(type=MessageType.SERVER_HELLO, payload=payload)
    encoded = msg.encode()

    # Header is 4 bytes big-endian uint32 followed by the body.
    assert len(encoded) > HEADER_SIZE
    length = struct.unpack(">I", encoded[:HEADER_SIZE])[0]
    body = encoded[HEADER_SIZE:]
    assert len(body) == length

    decoded = Message.decode(body)
    assert decoded.type == MessageType.SERVER_HELLO
    assert decoded.payload == payload


def test_encode_message_helper_matches_message_encode():
    msg_type = MessageType.INPUT
    payload = {"left": True, "right": False, "jump": True}
    assert encode_message(msg_type, payload) == Message(type=msg_type, payload=payload).encode()


def test_decode_raises_on_malformed_body():
    with pytest.raises((ValueError, Exception)):
        Message.decode(b"\xff\xfe\xfd\xfc garbage bytes")


def test_empty_payload_roundtrip():
    msg = Message(type=MessageType.GAME_START, payload={})
    body = msg.encode()[HEADER_SIZE:]
    decoded = Message.decode(body)
    assert decoded.type == MessageType.GAME_START
    assert decoded.payload == {}


def test_nested_payload_roundtrip():
    payload = {
        "players": [{"player_id": "p1", "slot": 0}, {"player_id": "p2", "slot": 1}],
        "seed": 123456,
    }
    msg = Message(type=MessageType.SERVER_STATE, payload=payload)
    body = msg.encode()[HEADER_SIZE:]
    decoded = Message.decode(body)
    assert len(decoded.payload["players"]) == 2
    assert decoded.payload["seed"] == 123456


# ── read_message ──────────────────────────────────────────────────────────────

def test_read_message_roundtrip_via_feed():
    payload = {"action": "ping", "ts": 999}
    encoded = encode_message(MessageType.CLIENT_HELLO, payload)
    reader = _feed_reader(encoded)

    msg = _run(read_message(reader))
    assert msg.type == MessageType.CLIENT_HELLO
    assert msg.payload["action"] == "ping"


def test_read_message_raises_when_body_too_large():
    # Build a header claiming a body larger than MAX_MESSAGE_BYTES.
    oversized_header = struct.pack(">I", MAX_MESSAGE_BYTES + 1)
    reader = _feed_reader(oversized_header)
    # feed enough dummy bytes so readexactly(4) won't raise IncompleteReadError
    # before we get to the length check (it raises ValueError before reading the body).
    with pytest.raises(ValueError, match="too large"):
        _run(read_message(reader))


def test_read_message_raises_on_malformed_body():
    garbage_body = b"\x00\x01\x02garbage"
    header = struct.pack(">I", len(garbage_body))
    reader = _feed_reader(header + garbage_body)
    with pytest.raises(ValueError, match="[Mm]alformed"):
        _run(read_message(reader))


# ── write_message ─────────────────────────────────────────────────────────────

def test_write_message_produces_decodable_frame():
    payload = {"seed": 7777, "hub_id": "central_hub"}
    writer = _MemoryWriter()
    _run(write_message(writer, MessageType.GAME_START, payload))  # type: ignore[arg-type]

    raw = writer.get_value()
    assert len(raw) > HEADER_SIZE
    length = struct.unpack(">I", raw[:HEADER_SIZE])[0]
    body = raw[HEADER_SIZE:]
    assert len(body) == length
    decoded = Message.decode(body)
    assert decoded.payload["seed"] == 7777
    assert decoded.payload["hub_id"] == "central_hub"


# ── MessageType constants ─────────────────────────────────────────────────────

def test_all_message_type_values_are_non_empty_strings():
    attrs = {
        k: v
        for k, v in vars(MessageType).items()
        if not k.startswith("_")
    }
    assert len(attrs) > 0, "MessageType has no attributes"
    for name, value in attrs.items():
        assert isinstance(value, str), f"MessageType.{name} is not a str"
        assert len(value) > 0, f"MessageType.{name} is empty"


def test_message_type_values_are_unique():
    values = [
        v for k, v in vars(MessageType).items()
        if not k.startswith("_") and isinstance(v, str)
    ]
    assert len(values) == len(set(values)), "Duplicate MessageType values detected"


# ── PROTOCOL_VERSION ──────────────────────────────────────────────────────────

def test_protocol_version_is_string():
    assert isinstance(PROTOCOL_VERSION, str)
    assert len(PROTOCOL_VERSION) > 0
