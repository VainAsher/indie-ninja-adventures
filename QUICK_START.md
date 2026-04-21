# Quick Start

Java runtime quick start for `indie-ninja-adventures`.

## Prerequisites

- Java 21
- Gradle 8.7 (or use wrapper where available)
- Python 3.11+ (only for repo tooling scripts)

## Build and Test

```bash
python tools/check_version_sync.py
python tools/check_docs_freshness.py --emit-report
cd java && gradle :server:test :client:test --no-daemon
cd java && gradle :server:shadowJar :client:shadowJar --no-daemon
```

## Run

From repository root:

```bash
java -jar ninja-server-all.jar
java -jar ninja-client-all.jar
```

Windows helpers:

```text
run_java_server.bat
run_java_client.bat
```

## Where To Go Next

- Runtime/handover truth: [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
- Canonical docs index: [docs/INDEX.md](docs/INDEX.md)
- Java setup details: [docs/dev/JAVA_SETUP.md](docs/dev/JAVA_SETUP.md)

## Prototype Lane

The legacy Pygame prototype runtime has been extracted from this repository.

- Prototype repo: `https://github.com/VainAsher/indie-ninja-prototype`
- Migration handover: [docs/operations/PYGAME_MIGRATION_HANDOVER.md](docs/operations/PYGAME_MIGRATION_HANDOVER.md)
