---
doc_type: plan
status: completed
owner: core-team
last_updated: 2026-04-15
version_anchor: v0.11.45
---
# Multiplayer Hot-Join + Leave/Rejoin + Persistent Profiles (Server-Hosted)

**Date:** 2026-04-02  
**Status:** Design/implementation plan (ready to hand to a developer)  
**Applies to:** `indie-ninja-adventures` (Python 3.11 + pygame, asyncio TCP multiplayer)  
**Primary goal:** Dedicated server runs independently and players can join/leave/rejoin mid-session, with profile persistence (inventory layout, progression, NPC state, gate state, currency, unlocked hubs/locations).
**Related docs:** `docs/PLAN_PHASE3_AUTHORITATIVE_SERVER.md` (server simulation), `docs/SYSTEM_OVERVIEW.md` (system map)

---

## 0) Executive Summary (What to Build)

Build a **dedicated server** that can run with **0 clients**, and supports:

1. **Hot-join**: clients can connect at any time (before or after gameplay started).
2. **Hot-leave**: clients can disconnect any time without leaving â€œghostsâ€ or stuck simulation.
3. **Reconnect grace**: on disconnect, the server **reserves the slot** for *N seconds*; after that slot becomes available for new joiners.
4. **Server-hosted player profiles** (persisted to disk, per server instance):
   - Inventory **slot layout** + equipped items + currency
   - Abilities/progression (missions, story, defeated bosses, etc.)
   - NPC state (dialogue seen, shop stock, quest flags)
   - Gate/portal state (per hub)
   - Unlocked/visited hubs and other â€œlocationsâ€
5. **Reconnect spawn**: player always respawns at **hub spawn** (not last x/y), in either:
   - server default hub, or
   - the playerâ€™s last hub visited on that server.

This plan is **incremental**: ship hot-join first (small fix), then add persistent profiles, then expand NPC/gate/location state.

---

## 1) Current Code Reality (Deep-Dive Findings)

### 1.1 Why remote players canâ€™t join mid-session today

**Client** waits in a lobby loop until it receives `GAME_START`:
- `demo_game.py` holds until `_net_client.game_started.is_set()` (see the â€œL2: Multiplayer lobbyâ€ block).
- `NetworkClient` sets that event only when it receives `MessageType.GAME_START` (`network/client.py`).

**Server** only sends `GAME_START` once, when lobby is full:
- In `network/server.py`, `_handle_client()` broadcasts `LOBBY_UPDATE` and, if lobby becomes full and `game_started == False`, calls `start_game()` and broadcasts `GAME_START`.
- There is **no** â€œlate-join bootstrapâ€: if a client connects after `game_started=True`, it never receives `GAME_START`, so it stays stuck in lobby.

### 1.2 Multiplayer architecture constraints that matter for persistence

The serverâ€™s headless simulation (Phase 3) currently focuses on:
- physics + collision
- enemies + pickups + hazards
- authoritative `WORLD_STATE` broadcast
- instanced â€œzonesâ€ (`hub_id`) with `WORLD_TRANSITION` and zone presence notifications

It **does not** currently simulate campaign progression, dialogue, trading, or inventory systems. Therefore:
- Server-authoritative â€œprogression logicâ€ is a large follow-up project.
- For this feature set, the server acts as a **persistence + synchronization** authority:
  - It stores profiles and returns them on join/rejoin.
  - It applies sanity checks/validation to client-supplied profile updates.

### 1.3 Why leave/rejoin does not work today (even if hot-join is fixed)

Even after the â€œlate joiners need GAME_STARTâ€ bug is fixed, true rejoin still fails because:

- **Player identity is not stable**
  - `demo_game.py` uses random `player_id` values for both `--connect` and `--host`.
  - Result: reconnecting after a disconnect looks like a brand-new player to the server, so it canâ€™t restore anything.
- **No slot reservation / reconnect grace**
  - `network/server.py` assigns `slot = session.next_slot()` and immediately frees it on disconnect.
  - Result: even if the same player reconnects quickly, they usually get a different slot and (currently) no restored state.
- **â€œSticky inputâ€ in the authoritative simulator can create ghost movement**
  - `game/game_simulator.py::GameSimulator.step()` explicitly says absent slots â€œhold last known commandâ€.
  - `network/server.py::_zone_simulation_loop` only forwards inputs from currently connected players.
  - Result: if a player disconnects while holding movement, the server sim keeps that last input until explicitly neutralized.

### 1.4 How hubs/zones work right now (what we can leverage)

The project already has the core mechanics needed for â€œhub as entry pointâ€:

- **Zone creation is deterministic**: `network/server.py::_get_or_create_zone(hub_id)`
  - Uses `SeedDerivation.derive_region_seed(world_seed, hub_id)` so hub worlds match between server and clients.
  - Derives `shape` and `rooms` from `HubManager.get_hub_definition(hub_id)` when available.
- **Client travel is server-approved**
  - Client sends `PORTAL_TRAVEL` (`network/client.py`).
  - Server moves zone membership, then sends `WORLD_TRANSITION` including `spawn_x/spawn_y` (`network/server.py::_handle_portal_travel`).
  - Client rebuilds world on `poll_transition()` and `_apply_world_transition(...)` (`demo_game.py`).

Implication for reconnect: the server can pick an `entry_hub_id`, create that zone if needed, and spawn the player at that hubâ€™s spawn.

### 1.5 Existing persistence primitives you can reuse (and their gaps)

Useful â€œalready existsâ€ pieces:

- **Inventory layout serializer**: `game/inventory_system.py::Inventory.to_dict()/from_dict()`
  - This is the exact format needed to preserve slot layout, equipped flags, and currency.
- **Story serialization**: `game/story_manager.py::StoryManager.to_dict()/from_dict()`
  - Provides a clean blob for narrative progression and hub-state effects.
- **Shop serialization**: `game/trading_system.py::TradingManager.save_shops()/load_shops()`
  - Captures per-NPC shop stock, items, and generation seed.
- **Basic validation limits**: `systems/save_system.py` constants like `MAX_CURRENCY_LIMIT`, `MAX_ABILITIES_LIMIT`

Known gaps you must plan around:

- **Campaign save inventory format is not slot-based**
  - `systems/save_system.py` stores `CampaignSaveData.player_inventory` as `{item_id: quantity}`.
  - Slot layout is collapsed in `game/game_helpers.py::persist_player_inventory()`.
  - Multiplayer profile persistence must use `Inventory.to_dict()` (see Â§9).
- **Dialogue persistence does not exist**
  - `game/dialogue_system.py::DialogueManager` tracks only the *current* dialogue and a transient `history` list.
  - You need a persistent structure for â€œdialogue seen / choices madeâ€ (see Â§10.2).

---

## 2) Terminology (Use Consistently)

- **Server instance**: one running dedicated server process, with its own persistent storage directory and `server_uid`.
- **Session**: the runtime in-memory state of a server instance (connected players, zones, simulators).
- **Zone**: server â€œworld instanceâ€ keyed by `hub_id` (already implemented); may represent hubs and (eventually) missions.
- **Hub**: a safe â€œhub worldâ€ (e.g., `central_hub`, `forest_hub`), defined by `HubManager`. Reconnect always places the player into a hub.
- **Player profile**: persistent per-player data (inventory layout, progression, NPC state, gate state, unlocked hubs/locations).
- **Registry**: server-wide persisted index mapping `player_id` to profile metadata + slot reservation state.

---

## 3) Goals, Non-Goals, and Acceptance Criteria

### 3.1 Goals (must-have)

- Dedicated server can run without clients and accept connections at any time.
- Late-joining client successfully transitions from lobby â†’ gameplay when joining a running session.
- Disconnecting removes the player cleanly:
  - no â€œghost remote playerâ€
  - no â€œstuck inputâ€ continuing to move in server sim
- Reconnect within grace:
  - reuses reserved slot (if available)
  - restores profile (inventory layout + progression + NPC/gate state)
  - spawns at hub spawn in last hub visited (or default hub)
- Reconnect after grace:
  - may get a different slot
  - still restores profile
- Profiles and registry persist across server restarts.

### 3.2 Non-goals (explicitly out of scope for this milestone)

- Anti-cheat / authentication / encryption (but we still do basic validation).
- Fully server-authoritative campaign logic (mission completion, trading, dialogue triggers).
- Matchmaking / NAT traversal / server browser.
- Synchronizing inventory between multiple concurrently connected clients for the same player account.

### 3.3 Acceptance criteria (manual)

1. Start server. Leave it empty for 5 minutes. It stays alive.
2. Client A joins: receives profile, starts in hub, plays.
3. Client B joins while A is playing: B enters game (does not hang in lobby).
4. B travels to another hub. B disconnects.
5. B reconnects within grace: spawns at hub spawn in that hub; inventory/progression intact.
6. B disconnects. Wait until grace expires. Client C joins: can take freed slot.
7. B reconnects after grace: gets new slot but still receives profile and spawns at hub spawn.

### 3.4 Acceptance criteria (automated)

- Integration test that starts a server in-process and simulates:
  - connect A â†’ receive `GAME_START`
  - connect B after start â†’ still receive `GAME_START`
  - disconnect/reconnect B â†’ registry reservation logic works

---

## 4) High-Level Design

### 4.1 Key design decision: per-server profiles

Profiles are **per server instance**, not global:
- The same player can have different progress/inventory on different servers.
- Server identity is `server_uid` persisted on disk.

### 4.2 Hot-join bootstrap principle

Treat `GAME_START` as **bootstrap info** that can be sent:
- as a broadcast when the session starts, and
- as a unicast to any late joiner.

This avoids coupling gameplay start to a â€œfull lobbyâ€.

### 4.3 Reconnect grace principle

On disconnect, the server does **not** immediately free the slot:
- It marks that slot reserved for `player_id` until `reserved_until`.
- Other joiners may only claim non-reserved slots.

After grace expires:
- reservation cleared
- slot may be assigned to a new player

### 4.4 Profile synchronization principle (pragmatic)

For this milestone, use **client-reported profile updates** with server validation:
- client sends `PROFILE_UPDATE` on important changes + periodic flush
- server validates, stores, and acknowledges with a revision/etag

Later upgrade path:
- make server authoritative for currency from pickups, mission completion, etc.

### 4.5 Authority model (explicit) â€” what is authoritative for this milestone

Ship this feature by making the server authoritative for **identity, admission, and persistence**, while the client remains authoritative for â€œprogression logicâ€ for now.

| Domain | Authority now (this plan) | Notes / upgrade path |
|---|---|---|
| Connection, slots, grace reservations | **Server** | Required for fairness and stability |
| Zone membership (`hub_id`) | **Server** | Already server-controlled via `WORLD_TRANSITION` |
| Physics + enemies + pickups + hazards | **Server** | Already Phase 3+ in `network/server.py` |
| Inventory + currency + abilities + story progression | **Client â†’ server persisted** | Client reports; server validates + stores; later server can become authoritative |
| NPC dialogue flags + shop stock | **Client â†’ server persisted** | Best as per-player for now |
| Gate state | Mixed | Derived gates from abilities (recompute). Stateful gates require persistence (see Â§10.3). |

### 4.6 Shared-world vs per-player state (recommendations)

Decide what is â€œsharedâ€ between players and what is personal progression. For this milestone, recommend:

- **Per-player**: inventory, currency, abilities, mission completion, story, dialogue flags, shop stock.
- **Shared world (already happens)**: enemy/pickup/hazard state inside a currently running zone simulation (not persisted across zone teardown or server restarts).

If you later want â€œco-op shared campaign progressionâ€, move more logic server-side and treat the profile as shared group state.

---

## 5) Persistence Layout and Schemas

### 5.1 On-disk directory layout (recommended)

Inside the serverâ€™s user data root (configurable env `NINJADASH_USER_DATA` already exists for settings):

```
user_data/
  server_sessions/
    <server_uid>/
      server.json                # server instance config + schema version
      registry.json              # player_id -> reservation + profile metadata
      players/
        <player_id>.json         # PlayerProfile (full)
      logs/
        ...
```

**Atomic writes**
- Always write `*.tmp` then rename to final to avoid corruption on crash.

### 5.2 `server.json` (ServerInstanceConfig)

Fields:
- `schema_version`: integer
- `server_uid`: string UUID
- `created_at`: ISO timestamp
- `world_seed`: int (canonical base seed used by hub derivation)
- `default_hub_id`: string (e.g., `"central_hub"`)
- `max_players`: int
- `reconnect_grace_seconds`: int

### 5.3 `registry.json` (ServerRegistry)

Top-level:
- `schema_version`
- `server_uid`
- `players`: dict keyed by `player_id`

Per player entry:
- `player_id`
- `last_seen`: epoch seconds
- `last_safe_hub_id`: string (hub id only)
- `reserved_slot`: int | null
- `reserved_until`: epoch seconds | null
- `profile_rev`: int (monotonic)

### 5.4 `players/<player_id>.json` (PlayerProfile)

Top-level:
- `schema_version`
- `player_id`
- `profile_rev` (must match registry rev)
- `last_safe_hub_id`
- `visited_hubs`: list[str]
- `unlocked_hubs`: list[str]
- `unlocked_locations`: list[str] (implementation-defined, see Â§10.4)

Inventory (preserve **slot layout**):
- `inventory_layout`: exactly `Inventory.to_dict()` shape (`game/inventory_system.py`)
  - `slots`: list[slot|null] where slot is `{item_id, quantity, equipped}`
  - `currency`
  - `equipped_weapon`
  - `equipped_armor`

Progression:
- `unlocked_abilities`: list[str]
- `completed_missions`: list[str]
- `unlocked_regions`: list[str]
- `defeated_bosses`: list[str]
- `story_state`: dict (use `StoryManager.to_dict()` output)

NPC state:
- `shops`: dict (use `TradingManager.save_shops()` output; *per-player shop stock*)
- `dialogue`: dict (new; see Â§10.2)
- `npc_flags`: dict (extensible; quest flags, tutorial dismissed, etc.)

Gate/portal state:
- `gate_state`: dict (hub_id -> per-gate state, see Â§10.3)
- `portal_state`: dict (portal_id -> lock/unlock or discovery state; optional)

### 5.5 Example JSON (copy/paste templates)

These are intentionally minimal â€œknown-good shapesâ€ a developer can start from.

**`server.json`**
```json
{
  "schema_version": 1,
  "server_uid": "8c9d6b8b-8a46-49f0-97d3-8c5b1b1a1e5e",
  "created_at": "2026-04-02T12:00:00Z",
  "world_seed": 123456,
  "default_hub_id": "central_hub",
  "max_players": 4,
  "reconnect_grace_seconds": 30
}
```

**`registry.json`**
```json
{
  "schema_version": 1,
  "server_uid": "8c9d6b8b-8a46-49f0-97d3-8c5b1b1a1e5e",
  "players": {
    "f3b2b35e-0c3a-4d32-9b73-2d2d2e9b2b9a": {
      "player_id": "f3b2b35e-0c3a-4d32-9b73-2d2d2e9b2b9a",
      "last_seen": 1764800000,
      "last_safe_hub_id": "caves_hub",
      "reserved_slot": 1,
      "reserved_until": 1764800030,
      "profile_rev": 12
    }
  }
}
```

**`players/<player_id>.json`**
```json
{
  "schema_version": 1,
  "player_id": "f3b2b35e-0c3a-4d32-9b73-2d2d2e9b2b9a",
  "profile_rev": 12,
  "last_safe_hub_id": "caves_hub",
  "visited_hubs": ["central_hub", "forest_hub", "caves_hub"],
  "unlocked_hubs": ["central_hub", "forest_hub", "caves_hub"],
  "unlocked_locations": ["boss:spider_queen:defeated"],
  "inventory_layout": {
    "slots": [
      { "item_id": "weapon_sword", "quantity": 1, "equipped": true },
      null,
      { "item_id": "health_potion_small", "quantity": 3, "equipped": false }
    ],
    "currency": 250,
    "equipped_weapon": "weapon_sword",
    "equipped_armor": null
  },
  "unlocked_abilities": ["basic_movement", "jump", "dash"],
  "completed_missions": ["mission_intro"],
  "unlocked_regions": ["central_hub", "forest"],
  "defeated_bosses": ["SPIDER_QUEEN"],
  "story_state": {},
  "shops": {},
  "dialogue": { "seen_dialogues": ["npc_blacksmith_intro"] },
  "npc_flags": {},
  "gate_state": {},
  "portal_state": {}
}
```

### 5.6 Schema evolution rules (so you donâ€™t brick saves)

- Every persisted file has a `schema_version`.
- When loading:
  - if `schema_version` is older, migrate into the latest in-memory shape
  - if `schema_version` is newer, fail with a clear error (or load best-effort and warn)
- Keep migrations **pure** (data-in/data-out), idempotent, and unit-tested.

---

## 6) Protocol Changes (Wire Contract)

All messages are msgpack framed and use `{"type": ..., "payload": ...}` (`network/protocol.py`).

### 6.1 Existing messages to keep

- `client_hello`
- `server_hello`
- `game_start`
- `world_transition`
- `world_state`
- `player_join` / `player_leave`

### 6.2 Extend `client_hello` payload

Current:
```json
{ "player_id": "...", "version": "2.0.0" }
```

Add:
- `client_instance_id`: optional UUID (debugging)
- `requested_profile_rev`: int | null (allows â€œonly send profile if newerâ€)

### 6.3 Extend `server_hello` payload

Add:
- `server_uid`
- `session_started`: bool
- `reconnect_grace_seconds`

### 6.4 New message: `player_profile` (server â†’ client)

Sent:
- immediately after handshake (`server_hello`)
- also on explicit resync request (optional future)

Payload:
- `player_id`
- `profile_rev`
- `profile`: PlayerProfile object (or a subset if large)

### 6.5 New message: `profile_update` (client â†’ server)

Two options:

**Option A (simpler)**: send full profile snapshot
- `player_id`
- `base_profile_rev` (what client thinks server has)
- `profile` (full)

**Option B (better)**: send patch/delta
- `player_id`
- `base_profile_rev`
- `patch`: `{ set: {...}, unset: [...], append: {...} }`

Recommendation for milestone: start with Option A, then optimize to patches once stable.

### 6.6 New message: `profile_ack` (server â†’ client)

Payload:
- `player_id`
- `profile_rev` (new server rev after applying update)
- `accepted`: bool
- `warnings`: list[str] (clamps, unknown items removed, etc.)

### 6.7 Bootstrap message ordering (exact sequences)

This is the concrete wire-level order that prevents lobby hangs and avoids â€œspawn flashâ€ in the wrong hub.

**Case A: First player joins and session is not started yet (`start_mode=first_join`)**
1. Câ†’S: `client_hello {player_id, version, ...}`
2. Sâ†’C: `server_hello {player_id, slot, ..., server_uid, session_started:false, ...}`
3. Sâ†’C: `player_profile {player_id, profile_rev, profile}`
4. S: start session (initial zone sim init)
5. Sâ†’All: `game_start {seed, shape, rooms, hub_id:default_hub_id, world_seed}`
6. If entry hub â‰  default hub: Sâ†’C: `world_transition {hub_id:entry_hub_id, seed, shape, rooms, world_seed, spawn_x, spawn_y}`

**Case B: Late joiner connects after session started**
1. Câ†’S: `client_hello {...}`
2. Sâ†’C: `server_hello {..., session_started:true}`
3. Sâ†’C: `player_profile {...}`
4. Sâ†’C: `game_start {...}` (unicast; same payload as broadcast would have been)
5. If entry hub â‰  default hub: Sâ†’C: `world_transition {...}`

**Case C: Reconnect within grace**
Same as Case B, but the server picks the reserved slot and treats this as â€œrejoinâ€, not â€œnew joinâ€.

Client-side requirement for zero-flash:
- keep the â€œLOBBY/CONNECTINGâ€ overlay up until:
  - `game_start` received, and
  - `player_profile` received and applied, and
  - any initial `world_transition` needed for entry hub is applied.

### 6.8 Error codes (standardize now)

Standardize error codes so clients can display helpful messages:

- `expected_hello` (already exists)
- `session_full` (already exists)
- `duplicate_login` (same `player_id` already connected)
- `profile_invalid` (profile update rejected)
- `profile_rev_conflict` (client sent outdated base rev and server refuses)
- `hub_invalid` (requested hub not recognized)

### 6.9 Backward compatibility strategy

This feature touches wire messages. A pragmatic approach:

- Keep `PROTOCOL_VERSION = "2"` (still msgpack) unless you break framing/encoding.
- Bump `CLIENT_VERSION/SERVER_VERSION` when you ship profile messages.
- Servers can either:
  - accept older clients (best-effort) for a short window, or
  - hard-reject mismatched versions once profiles are required.

---

## 7) Server Runtime Behavior (Detailed)

### 7.1 Dedicated server startup

Add a dedicated server entrypoint that:
- loads/creates `server.json` + `registry.json`
- starts TCP listener
- pre-creates initial zone (`default_hub_id`)
- sets `session.game_started` based on `start_mode`:
  - `immediate`: start simulator immediately
  - `first_join` (recommended): start simulator when first player connects

### 7.2 Slot assignment algorithm (with grace reservations)

Inputs:
- `max_players`
- `registry.players[*].reserved_slot/reserved_until`
- joining `player_id`

Algorithm:
1. If player has existing unexpired reservation:
   - assign that reserved slot
2. Else:
   - compute `reserved_slots = {slot | reservation unexpired}`
   - compute `used_slots = {slot | currently connected}`
   - choose the smallest slot in `[0..max_players-1]` not in `reserved_slots âˆª used_slots`
3. If none available: reject with `error {code: session_full}`

### 7.3 Connection flow (new join or reconnect)

On `_handle_client()`:
1. Read `client_hello`.
2. Load/create PlayerProfile from disk.
3. Assign slot using algorithm above.
4. Send `server_hello`.
5. Send `player_profile`.
6. Ensure session started:
   - if `start_mode == first_join` and this is first player: start game and broadcast `game_start` to all
   - else if already started: **unicast** `game_start` to this client (late join bootstrap)
7. Add player to appropriate zone:
   - Determine `entry_hub_id = profile.last_safe_hub_id or default_hub_id`
   - Ensure zone exists; init simulator if needed
   - Set `ConnectedPlayer.hub_id = entry_hub_id`
   - Add to zone membership
   - Reset the server sim Player for this slot to the zone spawn (requirement: reconnect always spawns at hub spawn)
   - If `entry_hub_id != default_hub_id`, send `WORLD_TRANSITION` to this client immediately so the client spawns in the correct hub
8. Force a full world snapshot soon for that zone:
   - set zone delta countdown to 0 so first broadcast is full

### 7.4 Disconnect flow

On disconnect:
1. Remove player from session + zone membership.
2. Broadcast leave events (`player_leave`, `zone_presence departed`).
3. Prevent â€œsticky inputâ€:
   - clear that playerâ€™s `latest_input`
   - optionally reset the sim Player for that slot to neutral state
4. Start reservation timer in registry:
   - `reserved_slot = slot`
   - `reserved_until = now + reconnect_grace_seconds`
5. Persist registry to disk.

### 7.5 Reservation reaper task

Background task every ~5s:
- clears expired reservations
- persists registry if changed

### 7.6 Duplicate connection handling (same `player_id`)

Decide and implement one policy (recommendation: **kick old connection**):

- If a new connection arrives for a `player_id` that is currently connected:
  - close the old writer (server-initiated disconnect)
  - proceed with the new connection and keep the slot

This prevents â€œtwo clients controlling one profileâ€ and avoids split-brain updates.

### 7.7 Simulator player lifecycle (spawn/reset rules)

Because the server simulation pre-creates one Player per slot, you must reset a slot whenever it is (re)assigned.

Rules:

- On **new join** â†’ reset sim player to hub spawn.
- On **reconnect** â†’ reset sim player to hub spawn (requirement: reconnect spawn at hub spawn).
- On **slot reused by a different player** â†’ reset sim player to hub spawn.
- On **disconnect** â†’ neutralize immediately to stop â€œsticky inputâ€.

Implementation outline:

- Add a server helper:
  - `GameServer._reset_sim_player(zone: _ZoneInstance, slot: int) -> None`
  - sets physics x/y/vx/vy to `zone.spawn_x/zone.spawn_y/0/0`
  - restores HP to max (or a defined default)
  - clears transient action states if needed
- On disconnect, also feed one neutral `InputCommand(frame=...)` into that slot so mechanics release held keys.

### 7.8 Tracking `last_safe_hub_id` (so reconnect goes to the right hub)

Update and persist `last_safe_hub_id` whenever the server accepts a hub change:

- In `network/server.py::_handle_portal_travel(...)`:
  - after successful move, set `registry[player_id].last_safe_hub_id = new_hub_id`
  - update the playerâ€™s profile `last_safe_hub_id = new_hub_id`
  - persist registry (and optionally profile) immediately or via debounce

If you later add missions/non-hub zones:
- define â€œsafe hubsâ€ as a whitelist (e.g., hubs known by `HubManager`)
- only overwrite `last_safe_hub_id` when entering a hub, not a mission

---

## 8) Client Runtime Behavior (Detailed)

### 8.1 Persist player identity

The client must stop generating random `player_id` each launch.

Implementation:
- Create a local `client_id` file in `user_data/` on first boot.
- Use this ID as `player_id` in `client_hello`.

### 8.2 Join flow in `demo_game.py`

Current behavior blocks on lobby until `game_started` is set.

Required changes:
- Lobby overlay becomes informational only.
- Exit the lobby/bootstrap phase only when all required bootstrap data is ready:
  - `GAME_START` received (broadcast or unicast), AND
  - `PLAYER_PROFILE` received and applied, AND
  - if reconnecting into a non-default hub, the initial `WORLD_TRANSITION` is applied (so there is no â€œspawn flashâ€ in the default hub)

### 8.3 Applying the profile

When `PLAYER_PROFILE` arrives:
- Replace local runtime state with server profile:
  - `player_inventory` â† `Inventory.from_dict(profile.inventory_layout)`
  - `campaign_data.unlocked_abilities` â† profile
  - `campaign_data.completed_missions` â† profile
  - `campaign_data.currency` â† profile inventory currency (pick one canonical source)
  - `story_manager` â† `StoryManager.from_dict(profile.story_state)`
  - `trading_manager.load_shops(profile.shops)`
  - `dialogue_manager` restore state from `profile.dialogue` (requires new persistence hooks)
  - gate/portal states restored after hub regen (see Â§10.3)
- Call `sync_player_abilities(...)` so mechanics are enabled immediately.

### 8.4 Profile updates (client â†’ server)

Maintain a `profile_dirty` flag and a debounced flush:
- On any meaningful state change, mark dirty:
  - currency changes (coins, mission rewards, shop transactions)
  - inventory changes (add/remove/equip)
  - unlocked ability changes
  - completed missions
  - story progression changes
  - NPC dialogue flags
  - gate unlock changes
  - visited/unlocked hub changes
- Send `PROFILE_UPDATE`:
  - immediately (rate-limited), and
  - on a periodic flush timer (e.g., every 10s) if dirty
  - on graceful disconnect

### 8.5 How to detect changes (practical dirty-marking)

You donâ€™t need perfect event coverage on day 1, but you do need to catch the state the user explicitly cares about:

- **Inventory layout**: mark dirty on:
  - item add/remove
  - quantity change
  - equip/unequip
  - currency change
- **Progression**: mark dirty on:
  - mission completion
  - unlocked ability toggles
  - defeated boss recorded
  - story state transitions (act progression, endings, etc.)
- **NPC state**: mark dirty on:
  - trade/buy/sell (`game/trading_system.py` emits `TradeEvent`)
  - dialogue start/choice/advance/end (you will add these hooks in Â§10.2)
- **Hub/location state**: mark dirty on:
  - successful `WORLD_TRANSITION` (hub visited/unlocked updates)

Recommended implementation pattern:

- Create a `MultiplayerProfileSync` helper (new module) that owns:
  - `profile_dirty: bool`
  - `last_flush_time`
  - `build_profile_snapshot()` (reads from inventory/campaign/story/trading/dialogue)
  - `apply_profile_snapshot(profile)` (writes into those systems)
- Wire dirty marking from:
  - direct calls near inventory/trade/mission completion, and/or
  - event bus subscriptions (preferred if cleanly available)

### 8.6 Profile update conflict handling (rev/etag behavior)

Do not ignore concurrency, even in a small co-op game.

Server behavior:
- If `base_profile_rev` != current, either:
  - reject (`profile_rev_conflict`) and send the latest profile back, or
  - accept as â€œoverwriteâ€ (simpler but can lose updates)

Recommended for milestone:
- accept overwrite but **log warnings**; treat rev mismatch as â€œclient staleâ€
- later move to reject + resync once stable

Client behavior:
- keep `last_acked_profile_rev`
- if ack says rejected/conflict, request resync (future `profile_resync`) or wait for server to push `player_profile`

---

## 9) Critical Fix: Inventory Persistence Format Mismatch

Your code currently has a format mismatch:
- `SaveManager` stores campaign inventory as `dict[item_id -> quantity]` (`systems/save_system.py`).
- `Inventory.from_dict()` expects the **slot layout dict** format (`game/inventory_system.py`).
- `create_game_managers()` loads campaign inventory using `Inventory.from_dict(campaign_data.player_inventory)` which will not preserve slot layout and is structurally incompatible.

To preserve slot layout for multiplayer profiles, you must standardize one of:

**Approach 1 (recommended for this feature):**
- Keep server profiles using `Inventory.to_dict()`/`from_dict()` exclusively.
- Keep the existing local save schema unchanged for now (singleplayer).
- (Optional later) add a migration so local saves can also preserve layout.

**Approach 2 (bigger but cleaner):**
- Migrate `CampaignSaveData.player_inventory` to store full `Inventory.to_dict()` shape.
- Add save migration code for older saves.

This plan assumes Approach 1 for minimal risk.

---

## 10) Persisting â€œNPC Stateâ€, â€œGate Stateâ€, and â€œLocationsâ€

### 10.1 NPC state scope

Persist NPC state **per player profile** (not global world), unless you explicitly want shared world NPC stock.

At minimum:
- **Shop stock** per NPC: use `TradingManager.save_shops()` / `load_shops()`.
- **Dialogue flags**: track â€œdialogue seenâ€ and â€œchoices madeâ€.

### 10.2 Dialogue persistence (new work)

`DialogueManager` currently holds only the active dialogue + history for the current conversation.

Add:
- `DialogueManager.get_persistent_state()` â†’ dict
- `DialogueManager.apply_persistent_state(state)` â†’ None

Suggested persisted fields:
- `seen_dialogues`: set[str] (dialogue_id)
- `visited_nodes`: dict[dialogue_id -> set[node_id]]
- `last_node`: dict[dialogue_id -> node_id]
- `choice_history`: dict[dialogue_id -> list[{node_id, choice_index}]] (optional)

Hook points:
- After `start_dialogue()`, `select_choice()`, and `advance()`, update persistent state and mark profile dirty.

### 10.3 Gate/portal persistence (new work)

There are two gate categories:

1) **Derived gates** (no persistence required)
   - Ability-based portal restrictions (currently checked in `demo_game.py` by `_REGION_GATE_ABILITY` + unlocked abilities).
   - These can be recomputed from profile abilities and unlocked hubs.

2) **Stateful gates** (must persist)
   - Doors unlocked by keys/switches, one-time barriers, etc.
   - Persist as `{hub_id: {gate_id: {unlocked: bool, ...}}}`

**Gate ID stability is mandatory.**
Current `GateManager.add_gate()` auto-generates `gate_0`, `gate_1` which is not stable across regenerations.

Define stable IDs:
- Portal gate example: `gate:portal:<hub_id>:<portal_id>`
- Door gate example: `gate:door:<hub_id>:<room_x>:<room_y>:<local_x>:<local_y>`
- Switch gate example: `gate:switch:<hub_id>:<switch_id>`

Implementation steps:
- Extend gate creation API to accept explicit `gate_id`.
- When generating gates during hub regen, use the same stable IDs each time.
- After regen, apply persisted `unlocked` flags from profile.

### 10.4 Unlocked/visited hubs and â€œlocationsâ€

Define two explicit sets in the profile:
- `visited_hubs`: hubs the player has physically entered at least once
- `unlocked_hubs`: hubs the player is allowed to enter (could be equal to visited, or separate)

Define `unlocked_locations` as a flexible set of strings. Examples:
- `portal:<portal_id>` (discovered portals)
- `npc:<npc_id>:met` (met NPC)
- `region:<region_id>:unlocked`
- `boss:<boss_id>:defeated`

Update rules:
- On successful hub transition, add to `visited_hubs` and (optionally) `unlocked_hubs`.
- On story/mission milestones, add additional location flags.

### 10.5 Player abilities, currencies, and progression â€” exact fields to preserve

The user explicitly requested these to persist across reconnect:

- **Inventory slot layout** (including equipped flags)
  - Source: `player_inventory` (`game/inventory_system.py::Inventory`)
  - Persist: `inventory_layout = player_inventory.to_dict()`
  - Restore: `player_inventory = Inventory.from_dict(profile.inventory_layout)`
- **Coins / currency**
  - Source: `player_inventory.currency` (preferred canonical)
  - Persist: `inventory_layout.currency`
  - Restore: via `Inventory.from_dict(...)`
  - Keep `campaign_data.currency` in sync if UI reads it (choose one canonical path)
- **Unlocked abilities**
  - Source: `campaign_data.unlocked_abilities` (strings like `"dash"`, `"double_jump"`)
  - Persist/restore: list[str] in profile
  - After restore: call `sync_player_abilities(campaign_data.unlocked_abilities)` and rebuild hub gates.
- **Unlocked hubs / regions / locations**
  - Source (today): `campaign_data.unlocked_regions` plus hub travel history
  - Persist: `visited_hubs`, `unlocked_hubs`, and `unlocked_locations`
  - Restore: map back into `campaign_data.unlocked_regions` as needed for existing logic
- **Progression (missions / bosses / story)**
  - Missions: `campaign_data.completed_missions`, `mission_attempts`, `mission_best_times`
  - Bosses: `campaign_data.defeated_bosses`
  - Story: `story_manager.to_dict()/from_dict()`
- **NPC state**
  - Shops: `trading_manager.save_shops()/load_shops()`
  - Dialogue: persistent fields (seen dialogues, node history, choices)
- **Gate state**
  - Derived gates: recompute from unlocked abilities/hubs on hub load
  - Stateful gates: persist by stable gate IDs

---

## 11) Implementation Breakdown (PR-by-PR)

This is written as PRs so itâ€™s easy to review and so you can ship value early.

### PR 1 â€” Hot-join fix (unblocks late joiners immediately)

**Goal:** Fix â€œremote players canâ€™t join mid-sessionâ€ with the smallest change set.

**Key server changes** (`network/server.py`)
- After sending `SERVER_HELLO`, if `session.game_started` is already true, send `GAME_START` **unicast** to the newly joined client (same payload used in `session.start_game()`).
- Replace â€œauto-start only when lobby is fullâ€ with:
  - `start_mode=first_join` (recommended default): call `start_game()` when the first player connects, OR
  - `start_mode=immediate`: call `start_game()` at server boot.

**Key client changes** (`demo_game.py`)
- Lobby overlay must not assume â€œgame only starts when lobby is fullâ€.
- Exit lobby when `NetworkClient.game_started.is_set()` is true (works for both broadcast and unicast GAME_START).

**Acceptance tests**
- Start host with `max_players=4`. With only host connected, the game starts.
- Connect client B after host is already playing; B enters gameplay (no lobby hang).

**Estimated effort:** 0.5â€“1 day

### PR 2 â€” Dedicated server entrypoint (server runs without a client)

**Goal:** Run the server as a standalone process that can sit idle awaiting connections.

**Changes**
- Add CLI entrypoint (one of):
  - `python -m network.server --host 0.0.0.0 --port 7777 --seed 123 --max-players 4`, or
  - `tools/dedicated_server.py` importing `network.server.run_server`.
- Ensure headless mode is stable:
  - server sim already sets `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` during init; confirm this works when running as a dedicated server.

**Acceptance tests**
- Start server process with 0 clients; it stays alive.
- Client connects later and receives `SERVER_HELLO` + `GAME_START` and enters gameplay.

**Estimated effort:** 0.5â€“1 day

### PR 3 â€” Stable player identity (required for â€œrejoin restores profileâ€)

**Goal:** Reconnect uses the same `player_id` every time from the same client machine.

**Changes** (`demo_game.py`)
- Create/read `user_data/client_id.txt` (UUID string) during startup.
- Pass that as `player_id` to `NetworkClient(...)` instead of a random one.
- Add a CLI override `--player-id` for testing multiple identities from one machine.

**Acceptance tests**
- Quit and restart the client; it keeps the same `player_id`.

**Estimated effort:** 0.5 day

### PR 4 â€” ServerRegistry + reconnect grace (persisted)

**Goal:** Preserve a slot for a disconnected player for N seconds and persist the registry on disk.

**New code (recommended new module)**
- `network/server_persistence.py` (or `systems/server_persistence.py`)
  - `atomic_write_json(path, data)`
  - `load_json(path, default)`
  - dataclasses for `ServerInstanceConfig` and `ServerRegistry`

**Server changes** (`network/server.py`)
- Create/load `server.json` + `registry.json` under `user_data/server_sessions/<server_uid>/`.
- Replace `session.next_slot()` with reservation-aware slot selection (Â§7.2).
- On disconnect: write reservation into registry (reserved_slot + reserved_until) and persist.
- Background reaper clears expired reservations and persists.

**Acceptance tests**
- Disconnect, reconnect within grace â†’ same slot.
- Disconnect, wait past grace, new joiner can use freed slot.

**Estimated effort:** 1â€“2 days

### PR 5 â€” PlayerProfile persistence + join bootstrap (inventory/progression restored)

**Goal:** Server stores per-player profiles; client receives them on join and applies them.

**Protocol updates** (`network/protocol.py`)
- Add `MessageType.PLAYER_PROFILE`, `MessageType.PROFILE_UPDATE`, `MessageType.PROFILE_ACK`.
- Update `tests/unit/test_network_protocol.py` still passes uniqueness checks.

**Server changes** (`network/server.py`)
- Load or create profile on connect.
- Send `player_profile` after `server_hello` (before or alongside `game_start`).
- Ensure late joiners get `game_start` unicast.
- Determine `entry_hub_id = profile.last_safe_hub_id or default_hub_id`.
  - If `entry_hub_id != default_hub_id`, send an immediate `world_transition` to the new client so they spawn in the correct hub.
- Reset the server sim player for the slot (spawn at hub spawn) on join/rejoin (Â§7.7).
- Accept `profile_update` messages:
  - validate
  - persist
  - bump `profile_rev`
  - send `profile_ack`

**Client changes** (`network/client.py`)
- Add queues + poll helpers:
  - `poll_player_profile() -> dict | None`
  - `poll_profile_ack() -> dict | None`
- Track `last_acked_profile_rev`.

**Game integration** (`demo_game.py`)
- In lobby/bootstrap phase:
  - wait for `game_start`
  - wait for `player_profile` and apply it
  - if entry hub is not default hub, wait for the initial `world_transition` and apply it before starting gameplay
- Apply profile into:
  - `player_inventory` via `Inventory.from_dict(...)`
  - `campaign_data` sets (abilities, missions, defeated bosses, unlocked hubs/regions)
  - `story_manager` via `StoryManager.from_dict(...)`
  - `trading_manager` via `load_shops(profile.shops)`
  - `dialogue_manager` via `apply_persistent_state(profile.dialogue)` (added in PR 6)
- Add a periodic flush loop:
  - every 10s if dirty, or immediately on key state changes

**Acceptance tests**
- Join â†’ inventory layout preserved (slot order + equipped items).
- Disconnect/reconnect â†’ profile restored, spawn at hub spawn, and slot reservation works.

**Estimated effort:** 2â€“4 days

### PR 6 â€” NPC dialogue persistence (seen/choices persist)

**Goal:** Keep dialogue progress and related NPC flags across reconnect.

**Changes**
- `game/dialogue_system.py`
  - Add `get_persistent_state()` / `apply_persistent_state()`
  - Update persistent state in `start_dialogue`, `select_choice`, `advance`, `end_dialogue`
- Profile snapshot now includes `dialogue` and `npc_flags`.

**Estimated effort:** 1â€“2 days

### PR 7 â€” Gate state persistence (optional if only derived gates exist today)

**Goal:** Persist and re-apply stateful gates/doors using stable IDs.

- If gates are purely derived from abilities (current portal gating): you can defer this PR.
- If you add real â€œdoors/switchesâ€:
  - Add stable IDs to gate creation (do not use incrementing `gate_0`, `gate_1`)
  - Persist `{hub_id -> gate_id -> state}` in profile
  - Apply persisted state after hub regen

**Estimated effort:** 2â€“5 days (depends on how many gate types exist in-world)

### PR 8 â€” Tests, docs, and tooling

**Goal:** Make the system safe to change.

- Add integration test harness that starts a server coroutine in-process and connects lightweight clients.
- Add registry/profile unit tests (schema + atomic write + migration).
- Update docs: QUICK_START + multiplayer notes + reconnect grace semantics.

**Estimated effort:** 1â€“2 days

### Overall estimate (rough)

- Minimum â€œlate join fixâ€ (PR 1): 0.5â€“1 day
- Full persistence + rejoin grace (PR 1â€“5): ~5â€“10 days
- Dialogue + gates (PR 6â€“7): +3â€“7 days
- Tests/docs (PR 8): +1â€“2 days

---

## 12) Testing Strategy (Detailed)

### 12.1 Unit tests
- Registry load/save:
  - atomic write correctness
  - reservation expiry behavior
- Profile validation:
  - inventory slot layout schema validation
  - unknown item ids rejected/clamped
  - currency clamped to bounds
- Protocol encode/decode for new message types

### 12.2 Integration tests
- Start server coroutine in-process.
- Connect a client, ensure it receives:
  - `server_hello`
  - `player_profile`
  - `game_start`
- Connect a late joiner after the session started:
  - ensure it still receives `game_start` (unicast)
- Disconnect and reconnect within grace:
  - slot reused
  - profile_rev increases with updates
- Disconnect, wait past grace, connect another client:
  - slot can be claimed

### 12.3 Manual playtest
- Run dedicated server in one terminal.
- Join with two clients; buy/sell; complete mission; travel hubs; disconnect/reconnect.

---

## 13) Validation / Security (Pragmatic Baseline)

Even without auth, do basic sanity checks server-side:
- Clamp currency to reasonable maximum (reuse `systems/save_system.py` style limits).
- Reject negative quantities.
- Validate item ids exist in `data/items.json` (server can load it once at boot).
- Cap unlocked abilities count.
- Validate hub ids exist (or are in an allowlist) before using as reconnect target.

If validation rejects fields:
- accept the update with warnings and server-corrected values
- send `profile_ack` warnings back to the client for debugging

---

## 14) Risks and Mitigations

**Risk: Disk I/O blocks asyncio loop**
- Mitigation: do file writes via `asyncio.to_thread()` / executor and debounce writes.

**Risk: Inventory format mismatch causes silent loss**
- Mitigation: use `Inventory.to_dict()`/`from_dict()` in multiplayer profile only; add explicit schema validation.

**Risk: Gate IDs not stable**
- Mitigation: implement stable gate IDs early (PR 7), do not rely on auto increment.

**Risk: Cheating via PROFILE_UPDATE**
- Mitigation: server validation/clamping; later server-authoritative updates for currency/pickups.

---

## 15) Open Questions (Decide Before Coding)

1. Should shop stock be **per-player** (profile-based) or **shared world** (zone-based)?
2. What counts as a â€œhubâ€ for reconnect?
   - Only hubs known by `HubManager`?
   - If player disconnects in a mission, always restore to last safe hub?
3. Should the server allow multiple simultaneous connections with the same `player_id`?
   - Recommendation: no; kick old connection.

---

## 16) Developer Quick Checklist

- [ ] Late joiner always receives `GAME_START` (unicast if needed).
- [ ] Dedicated server runs without local pygame client.
- [ ] Client has persistent `player_id`.
- [ ] Server registry and profiles persist to disk and are crash-safe.
- [ ] Inventory layout preserved using `Inventory.to_dict()` format.
- [ ] Currency preserved and validated (no negatives, clamped max).
- [ ] Unlocked abilities/regions/hubs restored and mechanics re-synced (`sync_player_abilities` + hub gates).
- [ ] Profile update flow is debounced and acknowledged.
- [ ] Reconnect grace reserves slot and expires correctly.
- [ ] Reconnect always respawns at hub spawn (never restores x/y).
- [ ] Entry hub is default hub or last safe hub (server-driven) with an initial `WORLD_TRANSITION` when needed.
- [ ] Duplicate `player_id` connections handled (kick old or reject).
- [ ] Gate IDs are stable; persisted gate state re-applied on hub regen.
- [ ] NPC shop + dialogue state persists across reconnect.

