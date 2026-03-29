# Implementation Plan — N4 Remote Players + L2 Lobby

**Date:** 2026-03-29
**Status:** In progress
**Scope:** Make multiplayer visible (remote player rendering + interpolation) + pre-game lobby

---

## Context

Phase 1 (N1–N3) is complete and working:
- Server relays inputs and broadcasts `MultiplayerSnapshot` at 60 Hz
- Client sends per-frame `InputCommand` and receives snapshots
- `poll_state()` returns the snapshot dict each frame — **but it is currently discarded**

The two goals for this session:
1. **N4** — Render the remote player on each client using the snapshot data
2. **L2** — Lobby screen so both players are in sync before the game starts

---

## Phase N4 — Remote Player Rendering

### What we're building

- A lightweight `RemotePlayer` entity (no physics engine, just state holder)
- A ghost renderer: colored silhouette + directional arrow + health bar + slot label
- Linear interpolation between received positions to smooth 60 Hz network jitter
- Wired into `demo_game.py`: parse snapshot → update entities → render after local player

### Why ghost not full sprite

The `AnimationStateMachine` tracks animation state tied to input events. Replicating that per remote player requires receiving full animation state over the wire (not sent yet). A ghost is correct for Phase N4. Full sprite sync is N5.

### Files

| File | Action | Purpose |
|---|---|---|
| `entities/remote_player.py` | New | RemotePlayer dataclass + lerp helper |
| `rendering/remote_player_renderer.py` | New | Draw ghost, health bar, name tag |
| `demo_game.py` | Modified | Parse snapshot, maintain `_remote_players` dict, render |

### RemotePlayer entity

```python
@dataclass
class RemotePlayer:
    slot: int
    player_id: str
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    health: int = 5
    facing: int = 1       # 1=right -1=left
    is_dead: bool = False
    # Interpolation state
    prev_x: float = 0.0
    prev_y: float = 0.0
    last_server_time: float = 0.0  # pygame.time.get_ticks() ms at last update
```

Lerp helper:
```python
def interpolated_pos(rp: RemotePlayer, now_ms: float, tick_ms: float = 16.67):
    t = min(1.0, (now_ms - rp.last_server_time) / tick_ms)
    x = rp.prev_x + (rp.x - rp.prev_x) * t
    y = rp.prev_y + (rp.y - rp.prev_y) * t
    return x, y
```

### Ghost renderer

Draw order per remote player:
1. Semi-transparent body rect (28×56, matching local player hitbox)
2. Direction arrow (small triangle pointing left or right inside rect)
3. Health bar (above head, same style as game HUD)
4. Slot label "P2" above health bar

Colours:
- Alive body fill: `(80, 160, 255, 160)` — blue tint to distinguish from local player
- Dead body fill: `(100, 100, 100, 80)` — grey ghost
- Health bar: green/red as normal

### demo_game.py wiring

```python
# After input pipeline
snapshot_dict = _net_client.poll_state() if _net_client else None
if snapshot_dict:
    from network.snapshots import MultiplayerSnapshot as _MPS
    _snap = _MPS.from_dict(snapshot_dict)
    _now_ms = pygame.time.get_ticks()
    for _ps in _snap.players:
        if _ps.slot == (_net_client.local_slot or 0):
            continue
        if _ps.slot not in _remote_players:
            _remote_players[_ps.slot] = RemotePlayer(slot=_ps.slot, player_id=_ps.player_id)
        _rp = _remote_players[_ps.slot]
        _rp.prev_x, _rp.prev_y = _rp.x, _rp.y
        _rp.x, _rp.y = _ps.pos
        _rp.vx, _rp.vy = _ps.vel
        _rp.health = _ps.health
        _rp.facing = _ps.facing
        _rp.is_dead = _ps.is_dead
        _rp.last_server_time = _now_ms

# Rendering: after local player render (~line 3415)
for _rp in _remote_players.values():
    remote_player_renderer.draw(game_surface, _rp, camera, pygame.time.get_ticks())
```

Cleanup: remove remote players from `_remote_players` when `PLAYER_LEAVE` message
received — monitor `_net_client.last_leave_slot` (new small field on NetworkClient).

---

## Phase L2 — Lobby Screen

### What we're building

A simple pre-game lobby that keeps all players in sync before gameplay starts:
- **Server (host)**: game waits at lobby overlay; sees "1/2 connected"; presses ENTER to start
- **Client (joiner)**: sees "Connected — waiting for host..."; game starts when host sends signal
- Auto-cancels if client disconnects before start

### New message types

Add to `network/protocol.py`:
- `LOBBY_UPDATE` — server → clients: current player count `{"connected": 1, "max": 2}`
- `GAME_START` — server → clients: game begins `{"seed": 12345}`

### Server changes (`network/server.py`)

1. Add `GameSession.game_started: bool = False`
2. `GameServer` exposes `session.start_game()` — broadcasts `GAME_START`
3. On each player join/leave, broadcast `LOBBY_UPDATE`
4. `_client_loop` queues inputs only after `game_started`; before that, hold in lobby

### Client changes (`network/client.py`)

1. Add `NetworkClient.game_started: threading.Event`
2. `_recv_loop` handles `LOBBY_UPDATE` → expose `connected_count` property
3. `_recv_loop` handles `GAME_START` → sets `game_started` event + stores seed

### demo_game.py lobby flow

```python
if _net_client is not None:
    # Show lobby overlay until GAME_START received or timeout
    _lobby_running = True
    while _lobby_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if args.host and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                # Host triggers start
                _net_thread_ref.session.start_game()  # need ref exposure

        # Check if game_started event fired (client side)
        if _net_client.game_started.is_set():
            _lobby_running = False

        _draw_lobby_overlay(game_surface, _net_client, is_host=bool(args.host))
        pygame.display.flip()
        clock.tick(30)
```

Lobby overlay:
- Dark semi-transparent panel centred on screen
- "LOBBY" title in gold Impact font (matches main menu)
- "Players: 1/2" count
- Host: "Press ENTER to start" prompt
- Client: "Waiting for host..."
- ESC to cancel (disconnects)

---

## Sequence — what to implement first

1. `entities/remote_player.py` — dataclass + lerp
2. `rendering/remote_player_renderer.py` — ghost renderer
3. Wire N4 into `demo_game.py` — parse snapshot + render
4. Add LOBBY_UPDATE + GAME_START to `network/protocol.py`
5. Update `network/server.py` — lobby state + start_game
6. Update `network/client.py` — handle lobby messages
7. Wire L2 lobby into `demo_game.py`
8. Update CHANGELOG + TASK_LIST
9. Commit + push + tag v0.7.5

---

## Out of scope this session

- Full sprite animation sync for remote players (N5)
- Input prediction / rollback (N5)
- Reconnect mid-session (N5)
- More than 2 players
- Mod browser (L3)
