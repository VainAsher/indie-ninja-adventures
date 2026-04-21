# Java Setup Guide

Current runtime setup for `indie-ninja-adventures` (Java-first lane).

## Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Java JDK | 21+ | Required for client/server runtime |
| Gradle | Wrapper or local | `./gradlew` from repo root |
| Python | 3.11+ | Repo tooling only (`tools/*.py`) |

## Build and Test

From repository root:

```bash
python tools/check_version_sync.py
python tools/check_docs_freshness.py --emit-report
./gradlew :server:test :client:test --no-daemon
./gradlew :server:shadowJar :client:shadowJar --no-daemon
```

Build outputs:

- `ninja-server-all.jar`
- `ninja-client-all.jar`

## Run

```bash
java -jar ninja-server-all.jar
java -jar ninja-client-all.jar
```

Windows helper scripts:

- `run_java_server.bat`
- `run_java_client.bat`

## Notes

- Java runtime values in `PhysicsConstants` are authoritative in this repository.
- The legacy Pygame prototype lane has moved to `VainAsher/indie-ninja-prototype`.
- Migration ownership map: `docs/operations/PYGAME_MIGRATION_HANDOVER.md`.
