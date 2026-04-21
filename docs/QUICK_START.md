# Quick Start (Java Lane)

This repository now ships a Java-first runtime.

## 1) Validate metadata and docs

```bash
python tools/check_version_sync.py
python tools/check_docs_freshness.py --emit-report
```

## 2) Run Java test gates

```bash
./gradlew :server:test :client:test --no-daemon
```

## 3) Build runnable jars

```bash
./gradlew :server:shadowJar :client:shadowJar --no-daemon
```

## 4) Launch

```bash
java -jar ninja-server-all.jar
java -jar ninja-client-all.jar
```

Windows shortcuts:

- `run_java_server.bat`
- `run_java_client.bat`

## Prototype Migration Note

Legacy Pygame prototype code has been extracted out of this repository.

- Prototype repo: `https://github.com/VainAsher/indie-ninja-prototype`
- Migration handover: `operations/PYGAME_MIGRATION_HANDOVER.md`
