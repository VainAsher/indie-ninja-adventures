#!/usr/bin/env bash
# build-local.sh — Bash companion to build-local.bat for OneDrive environments.
#
# Clears Gradle output directories that OneDrive commonly locks, then builds
# the client fat JAR and copies it to the repo root.
#
# Usage:
#   bash tools/build-local.sh                 — build client shadowJar
#   bash tools/build-local.sh :client:test    — run client tests
#   bash tools/build-local.sh :server:test    — run server tests
#
# If Gradle still fails with "Unable to delete directory", run again —
# OneDrive releases locks within a few seconds of a file being written.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JAVA_DIR="$REPO_ROOT/java"

echo "[build-local] Clearing OneDrive-locked Gradle output dirs..."
for module in core shadowascent server client; do
    rm -rf "$JAVA_DIR/$module/build/classes" "$JAVA_DIR/$module/build/resources" 2>/dev/null || true
done

cd "$JAVA_DIR"

if [ -z "$1" ]; then
    echo "[build-local] Building client shadowJar..."
    ./gradlew.bat :client:shadowJar --no-daemon
    # Copy JAR to repo root (copyJarToRoot may fail if OneDrive locks root — do it manually)
    JAR_SRC="$LOCALAPPDATA/indie-ninja-builds/client/libs/ninja-client-all.jar"
    if [ -f "$JAR_SRC" ]; then
        cp "$JAR_SRC" "$REPO_ROOT/ninja-client-all.jar"
        echo "[build-local] JAR copied to repo root."
    else
        # Fallback: JAR in standard build dir (non-OneDrive machine)
        cp "$JAVA_DIR/client/build/libs/ninja-client-all.jar" "$REPO_ROOT/ninja-client-all.jar" 2>/dev/null && \
            echo "[build-local] JAR copied to repo root." || \
            echo "[build-local] Warning: could not locate built JAR to copy to root."
    fi
else
    echo "[build-local] Running: gradlew.bat $*"
    ./gradlew.bat "$@" --no-daemon
fi

echo "[build-local] Done."
