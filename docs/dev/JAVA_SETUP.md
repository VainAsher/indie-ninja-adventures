# Java Setup Guide — Indie Ninja Adventures

**Introduced in:** v0.10.0 (feature/java-server-phase-a)  
**Phase:** A — Java Netty Server (Python clients unchanged)

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Java JDK | 21+ LTS | [Adoptium](https://adoptium.net/) recommended |
| Gradle | via wrapper | `./gradlew` / `gradlew.bat` downloads automatically |
| Python | 3.11+ | Still needed for the game client (Pygame) |

Check your Java version:
```
java -version
```
Should show `openjdk 21` or higher.

---

## Project Layout

```
indie-ninja-adventures/
├── java/                        ← Java sub-project root
│   ├── settings.gradle.kts      ← Multi-module Gradle config
│   ├── build.gradle.kts         ← Shared build settings
│   ├── gradlew.bat              ← Windows Gradle wrapper
│   ├── core/                    ← Shared: physics, ECS, network DTOs
│   │   └── src/main/java/com/indieniinja/
│   │       ├── core/            ← EventBus, TickEvent, GameEvent
│   │       ├── physics/         ← PhysicsConstants, PhysicsSystem, CollisionSystem, SpatialHash
│   │       └── network/         ← MessageType, WireCodec, InputCommand, snapshot DTOs
│   ├── server/                  ← Netty authoritative server (headless)
│   │   └── src/main/java/com/indieniinja/server/
│   │       ├── NinjaGameServer.java        ← Entry point
│   │       ├── ServerProtocolHandler.java  ← Message routing
│   │       ├── ZoneSimulationLoop.java     ← 60 Hz zone sim thread
│   │       ├── ZoneInstance.java           ← Zone state
│   │       ├── GameSession.java            ← Session/lobby state
│   │       ├── PlayerRecord.java           ← Per-player state
│   │       └── DeltaEncoder.java           ← CRC32 delta encoding
│   └── client/                  ← libGDX client scaffold (Phase C)
├── run_java_server.bat          ← Windows run script
└── docs/dev/JAVA_SETUP.md       ← This file
```

---

## Building

### Build everything
```bat
cd java
gradlew.bat build
```

### Build server JAR only
```bat
cd java
gradlew.bat :server:shadowJar
```
Output: `java/server/build/libs/server-0.10.0-all.jar`

### Run tests
```bat
cd java
gradlew.bat test
```

---

## Running the Java Server

### Windows (quick start)
```bat
run_java_server.bat 7777 42
```
Or manually:
```bat
java -XX:+UseZGC -Xms128m -Xmx256m -jar java\server\build\libs\server-0.10.0-all.jar 7777 42
```

### Connect a Python client to the Java server
```bat
python demo_game.py --connect 127.0.0.1:7777
```
The Python client is **unchanged** — it speaks the same msgpack protocol (PROTOCOL_VERSION="2").

---

## Protocol Compatibility

The Java server is **wire-compatible** with the Python server and client:
- Same 4-byte big-endian length prefix format
- Same msgpack body structure
- Same `MessageType` string constants
- Same `PROTOCOL_VERSION = "2"`

If you update message types in Python's `network/protocol.py`, update  
`java/core/src/main/java/com/indieniinja/network/MessageType.java` to match.

---

## Physics Constants Parity

All physics constants in  
`java/core/src/main/java/com/indieniinja/physics/PhysicsConstants.java`  
**must exactly match** `config/physics_constants.py`.

Run the parity tests to verify:
```bat
cd java
gradlew.bat :server:test --tests "com.indieniinja.server.PhysicsParityTest"
```

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| A | **v0.10.0** | Java Netty server; Python clients unchanged |
| B | Planned | Java physics embedded in server; 60 Hz broadcast restored |
| C | Planned | libGDX client replaces Pygame |

---

## Troubleshooting

**"JAR not found"** — Build first with `cd java && gradlew.bat :server:shadowJar`

**"Protocol version mismatch"** — Java and Python must both use `PROTOCOL_VERSION = "2"`

**Port already in use** — Kill any running Python server first:
```bat
tasklist | findstr python
taskkill /F /PID <pid>
```

**OutOfMemoryError** — Increase heap: `-Xmx512m` in `run_java_server.bat`
