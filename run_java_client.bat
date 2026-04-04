@echo off
REM Indie Ninja Adventures — Java libGDX client launcher
REM Usage: run_java_client.bat [host] [port]
REM  host  default: 127.0.0.1
REM  port  default: 7777

set HOST=%~1
set PORT=%~2
if "%HOST%"=="" set HOST=127.0.0.1
if "%PORT%"=="" set PORT=7777

set JAR=java\client\build\libs\ninja-client-all.jar
if not exist "%JAR%" (
    echo [ERROR] Client JAR not found: %JAR%
    echo Run: cd java ^&^& gradlew.bat :client:shadowJar
    exit /b 1
)

java -XX:+UseZGC -Xms128m -Xmx512m -jar "%JAR%" %HOST% %PORT%
