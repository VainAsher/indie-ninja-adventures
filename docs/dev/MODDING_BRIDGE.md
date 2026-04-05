# Modding Bridge — Decision Document

**Status:** Decided — ZeroMQ IPC  
**Date:** 2026-04-05  
**Context:** Phase C of the Java rewrite (see plan `curried-twirling-prism.md`)

---

## Problem

The Python mod system (`core/mod_system.py`) lets players write Python scripts that hook into
game events. With the Java libGDX client becoming the primary client, mods need a way to
communicate with the running Java process.

Two options were evaluated:

---

## Option A — GraalVM Polyglot (Rejected)

Run Python inside the JVM via GraalVM's Truffle/Polyglot API.

**Pros:**
- Mods run in the same process; zero IPC overhead
- Direct access to Java objects from Python

**Cons:**
- GraalVM is a separate JDK distribution (~250 MB extra download for players)
- Polyglot context startup is slow (~1–2s per session)
- Python support on GraalVM (GraalPy) lags CPython by 1–2 versions
- Mods can accidentally crash the JVM process (no isolation)
- Breaks the launcher's simple `java -jar` launch model

**Verdict:** Too heavyweight for a 4-player co-op indie game. Modding is a secondary feature
and should not force a JDK change on all players.

---

## Option B — ZeroMQ IPC (Chosen)

The Java client exposes a local ZeroMQ socket. Python mods run as a **separate process** and
connect to it to subscribe to events and call actions.

**Pros:**
- Zero change to the player's Java install — standard JRE 21 still works
- Mods are fully isolated; a crashing mod cannot take down the game
- Language-agnostic: mods could be written in Python, Lua, Node.js, or anything that has
  a ZeroMQ binding
- Simple pub/sub model maps naturally to the existing `EventBus` architecture
- Python mod API stays nearly identical to current `mod_system.py`

**Cons:**
- Adds `jeromq` (~300 KB) as a runtime dependency on the Java side
- Adds `pyzmq` as a dependency for Python mods (single `pip install`)
- ~0.5ms round-trip latency on localhost (acceptable; mods are not on the hot path)

**Verdict:** Chosen. Best balance of simplicity, isolation, and compatibility.

---

## Design Sketch

### Java side (`mod_bridge` package — Phase C+)

```java
// ModBridge.java — runs alongside the libGDX render loop
class ModBridge {
    static final int PORT = 7778;   // game on 7777, mods on 7778

    // PUB socket: broadcasts game events to all connected mods
    ZMQ.Socket pub;

    // REP socket: receives action requests from mods (e.g. spawn entity, play sound)
    ZMQ.Socket rep;

    void emitEvent(String type, Map<String, Object> payload) {
        pub.sendMore(type);
        pub.send(MessagePack.pack(payload));
    }
}
```

### Python mod side (`core/mod_zmq_client.py` — Phase C+)

```python
import zmq, msgpack

class ModZmqClient:
    def __init__(self, port=7778):
        ctx = zmq.Context()
        self.sub = ctx.socket(zmq.SUB)
        self.sub.connect(f"tcp://127.0.0.1:{port}")
        self.sub.setsockopt(zmq.SUBSCRIBE, b"")   # subscribe to all events

    def next_event(self) -> tuple[str, dict]:
        event_type = self.sub.recv_string()
        payload    = msgpack.unpackb(self.sub.recv(), raw=False)
        return event_type, payload
```

Existing mods using `core/mod_system.py` hooks stay unchanged for the Python client.
When running the Java client, `ModZmqClient` replaces the direct hook mechanism.

---

## Implementation Plan

1. Add `org.zeromq:jeromq:0.6.0` to `:client` dependencies
2. Create `com.indieniinja.client.mod.ModBridge` — PUB + REP socket lifecycle
3. Wire `EventBus` → `ModBridge.emitEvent()` for `TickEvent`, `CollisionEvent`, etc.
4. Update `core/mod_system.py` to optionally use `ModZmqClient` when `--java-client` flag
   is detected
5. Document mod API in `docs/dev/MOD_API.md`

This is deferred to a Phase C+ sprint — the bridge is not required for Phase C completion.
