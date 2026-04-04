@echo off
REM Indie Ninja Adventures — Java Authoritative Server (Phase A)
REM Usage: run_java_server.bat [port] [seed]
REM Default: port=7777  seed=42

set PORT=%1
set SEED=%2
if "%PORT%"=="" set PORT=7777
if "%SEED%"=="" set SEED=42

set JAR=java\server\build\libs\server-0.10.0-all.jar

if not exist "%JAR%" (
    echo [ERROR] Server JAR not found: %JAR%
    echo Run: cd java ^&^& gradlew.bat :server:shadowJar
    exit /b 1
)

echo Starting Ninja Java Server on port %PORT% with seed %SEED%
java -XX:+UseZGC -Xms128m -Xmx256m -jar "%JAR%" %PORT% %SEED%
