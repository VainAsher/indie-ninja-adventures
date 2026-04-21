---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Replay and Input Recording (Java)

## Scope

Input recording and playback for deterministic validation in solo and server simulation paths.

## Primary Java owners

- Input log write:
  - `java/shadowascent/src/main/java/com/indieniinja/sim/InputRecorder.java`
- Input log playback:
  - `java/shadowascent/src/main/java/com/indieniinja/sim/ReplayPlayer.java`
- Solo wiring:
  - `java/client/src/main/java/com/indieniinja/client/GameScreen.java`
  - `java/client/src/main/java/com/indieniinja/client/NinjaGameClient.java`
  - `java/client/src/main/java/com/indieniinja/client/DesktopLauncher.java`
- Server recording wiring:
  - `java/server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java`

## File format

- NDJSON line format.
- Header line includes seed and entry count.
- Data lines store tick, slot, and full command booleans.

## Runtime flow

- Record path:
  - Enabled by `-Dninja.record=true`.
  - Recorder captures per-tick commands and writes `user_data/replays/*.ndjson`.
- Replay path:
  - Pass replay file path via `-Dninja.replayPath=<abs-or-rel-path>`.
  - `GameScreen` loads replay and drives input from `ReplayPlayer` instead of keyboard sampling.

## Method-level call graphs

- Solo recording graph:
  - Launch with `-Dninja.record=true` -> `GameScreen.initializeSoloSimulation(..., startRecording=true)` -> `soloRecorder.startRecording(seed)`
  - Tick path -> `GameScreen.render(...)` -> `soloRecorder.record(localFrame, slot, cmd)`
  - Flush path -> `GameScreen.flushSoloReplay()` -> `soloRecorder.stopRecording(path)`
- Server recording graph:
  - `ZoneSimulationLoop.run()` with `Boolean.getBoolean("ninja.record")` -> `recorder.startRecording(zone.seed)`
  - `ZoneSimulationLoop.simulateTick()` -> `recorder.record(tickCount, slot, cmd)`
  - Shutdown -> `recorder.stopRecording(replayPath)`
- Replay playback graph:
  - Launch with `-Dninja.replayPath=...` -> `ReplayPlayer.load(path)`
  - Tick input source -> `GameScreen.render(...)` -> `soloReplay.inputsForTick(localFrame)` (instead of `InputPoller.poll()`)
  - Completion check -> `soloReplay.isDone(localFrame)`

## Contracts

- Replay determinism depends on fixed-tick simulation and stable content assumptions.
- Input commands are the canonical replay source of truth, not raw key events.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/REPLAY.md`
