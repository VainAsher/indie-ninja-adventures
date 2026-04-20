---
doc_type: current_state
status: living
owner: core-team
last_updated: 2026-04-19
version_anchor: v0.11.70
replaces: docs/HANDOVER.md
---

# Current State

Canonical runtime and handover snapshot for the active Java stack.

## Baseline

- Date baseline: 2026-04-19
- Version baseline: v0.11.68
- Platform baseline: Windows desktop
- Engine stack: Java 21 + libGDX + Netty
- Source of truth for release metadata: `version.json`

## Product State

- Product direction: campaign-first single-player with optional multiplayer overlay.
- Active execution plan: [`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`](plans/implementing/PLAN_SHADOW_ASCENT.md)
- Current milestone lane: P0 stabilization and onboarding/runtime evidence hardening.
- Next release candidate: v0.11.69 (combat feel / balance iteration — engine platform D is now live).
- Latest release verification (`2026-04-19`):
  - Tests green locally (BUILD SUCCESSFUL — all modules)
  - Tag target: v0.11.68

## Runtime Reality (Implemented)

- Authoritative server loop, zone simulation, and snapshot replication are active.
- Client rendering/UI loop is on libGDX desktop runtime.
- Mission lifecycle tracing and session-correlation logging are active.
- Siren-first onboarding flow and objective/mission affordances are active.
- NPC runtime dimensions are now authoritative over the wire (`NPCState.width/height`) and used by client render/debug hitbox overlays.
- Map input now follows explicit tap/hold semantics: `Tab` tap toggles quick map, `Tab` hold opens full map while held.
- Animation integration: stance-coupled posture readability (Yin unarmed / Yang armed) is enforced client-side — `EntityRenderer` routes animation key prefix from `stanceMode` directly (GDD §3.3), so Yin always renders unarmed and Yang always renders armed regardless of desync or offline state. Ledge corner hang-climb context and water-bank exit traversal bridge are also implemented with playtest log events.
- Solo/multiplayer campaign unification is live: `handleSoloPortalTravel()` now applies the same ability-gate + zone-migration logic as the server's `handlePortalTravel()`. Player state (health, level, xp, currency, inventory, abilities) is preserved across hub transitions; hub seeds are derived deterministically from the session seed via `HubRegistry.hubSeed()`. Campaign experience is identical whether played solo or co-op (drop-in/drop-out up to 4 players).
- Portal travel blocker fixes (v0.11.65): start-room portals removed from `LevelLayout` (exit-rooms only), render-loop race condition fixed (`refreshSoloWorldRoomCache` + `camera.snapTo` now called in `pollZoneTransition` handler). Portal travel is now stable.
- Stance animation fix (v0.11.65): `EntityRenderer` uses `hasAnyWithPrefix("player_sword_")` for Yang so all locomotion states (idle/walk/jump/crouch) display correct armed posture when sword sheets are registered.
- F9 debug ability toggle active (v0.11.65): solo mode only — cycles all abilities granted/cleared; HUD toast feedback.
- Mode select updated (v0.11.65): Sandbox retired, CAMPAIGN maps to solo ID, DEVELOPER replaces old solo card.
- Runtime keybinding ingestion is now live from `user_data/settings/settings.json` (`keybindings` block plus legacy `key_*` fallback), and map/debug/mission hotkeys consume the same binding table as input polling.
- Direct posture hot-swap input is now active (`select_weapon_1` / `select_weapon_2`, default `1`/`2`) with Yin-lock to unarmed and persistent Yang posture preference for runtime readability testing.
- `F1` controls overlay now renders active live bindings instead of a static key legend.
- Interaction affordance readability bridge is now active: lever/button/echo-trigger and pickup interactions queue short explicit animation feedback with `[Playtest][Interaction]` traces.
- Release/version parity gate is enforced through `tools/check_version_sync.py`.
- Solo replay playback is now routed through the Java client (`ninja-client-all.jar`) via `-Dninja.replayPath`; `ninja_dash.exe` / `demo_game.py` is no longer invoked for any launcher-initiated game operation.
- **Engine Platform Phases A–C complete (2026-04-19)**: Content definition system (`ContentLoader`, `ContentRegistry`, JSON-schema-validated definitions), `GameConfig` balance constants, animation manifest + hot-reload, Tiled TMX room loader (4 templates), Yarn Spinner dialogue format (23 files), in-game DevConsole (backtick toggle, 14 commands), Gradle `buildAssets` pipeline (436 files, SHA-256). Module extraction: `:shadowascent` module created — `sim.*` and `world.*` moved out of `:core`; `EntityTypeRegistry` + `ShadowAscentEntityTypeBootstrap` added; `:core` published as `engine-core` Maven artifact to GitHub Packages. All server tests pass.
- **Engine Platform Phase D complete (2026-04-19)**: Save checksums (`savegame.sha256` SHA-256 sidecar, verified on load with corrupt-save fallback). Perf regression gate (`TickDurationRegressionTest` — 2000-tick run, 5 ms ceiling, `perf_baseline.json`). Multi-slot save support (`user_data/saves/slot_N/`, `SlotSelectScreen`, legacy single-slot auto-migration). `tools/validate_animation_manifest.py` validates manifest against registry at authoring time.

## Canonical Documentation Set

- [INDEX.md](INDEX.md) - top-level documentation routing
- [ROADMAP.md](ROADMAP.md) - milestone sequencing and current targets
- [CHANGELOG.md](CHANGELOG.md) - release-facing version history
- [PLAYER_EXPECTATIONS.md](PLAYER_EXPECTATIONS.md) - launcher-first playtest contract
- [GDD.md](GDD.md) - design intent and narrative/mechanics contracts
- [RELEASE_VERSION_SYNC_CHECKLIST.md](RELEASE_VERSION_SYNC_CHECKLIST.md) - release metadata gate

## Repository Process Defaults

- Plan-embedded tasks are canonical for implementation tracking.
- `docs/TASK_LIST.md` is historical and archived.
- Retired/stale docs move immediately to `docs/archive/retired/`.
- Archive ZIP snapshots are kept in `docs/archive/zips/` and mirrored to release assets.
- Docs freshness checks are warning-only in CI unless explicitly run in strict mode.
