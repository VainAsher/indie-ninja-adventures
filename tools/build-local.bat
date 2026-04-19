@echo off
REM build-local.bat — Local dev build helper for OneDrive environments.
REM
REM Clears Gradle output directories that OneDrive commonly locks, then builds
REM the client and server fat JARs and copies them to the repo root.
REM
REM Usage:
REM   tools\build-local.bat              — build client + server JARs
REM   tools\build-local.bat :client:test — run client tests
REM   tools\build-local.bat :server:test — run server tests
REM
REM If Gradle still fails with "Unable to delete directory", run this script
REM again — OneDrive releases locks within a few seconds of a file being
REM written, so a second attempt usually succeeds.

setlocal

set REPO_ROOT=%~dp0..
set JAVA_DIR=%REPO_ROOT%\java

echo [build-local] Clearing OneDrive-locked Gradle output dirs...
for %%M in (core shadowascent server client) do (
    if exist "%JAVA_DIR%\%%M\build\classes"   rmdir /s /q "%JAVA_DIR%\%%M\build\classes"   2>nul
    if exist "%JAVA_DIR%\%%M\build\resources"  rmdir /s /q "%JAVA_DIR%\%%M\build\resources"  2>nul
)

if "%~1"=="" (
    echo [build-local] Building client + server JARs...
    cd /d "%JAVA_DIR%"
    gradlew.bat buildAll --no-daemon
) else (
    echo [build-local] Running: gradlew.bat %*
    cd /d "%JAVA_DIR%"
    gradlew.bat %* --no-daemon
)

if errorlevel 1 (
    echo.
    echo [build-local] Build failed. If you see "Unable to delete directory",
    echo               OneDrive still has a lock - wait 5s and run again.
    exit /b 1
)

echo [build-local] Done.
endlocal
