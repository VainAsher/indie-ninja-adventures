@echo off
REM Quick test script to verify Python installation

echo Testing Python installation...
echo.

REM Test 1: python command
echo Test 1: Checking 'python' command...
python --version 2>nul
if %errorlevel% equ 0 (
    where python | findstr /i "WindowsApps" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [OK] python command works
        python --version
        goto :TestVenv
    ) else (
        echo [FAIL] python is Windows Store stub
    )
) else (
    echo [FAIL] python command not found
)

REM Test 2: py launcher
echo.
echo Test 2: Checking 'py' launcher...
py --version 2>nul
if %errorlevel% equ 0 (
    echo [OK] py launcher works
    py --version
    goto :TestVenv
) else (
    echo [FAIL] py launcher not found
)

REM Test 3: python3
echo.
echo Test 3: Checking 'python3' command...
python3 --version 2>nul
if %errorlevel% equ 0 (
    echo [OK] python3 command works
    python3 --version
    goto :TestVenv
) else (
    echo [FAIL] python3 command not found
)

echo.
echo ========================================
echo [ERROR] No Python installation found!
echo ========================================
echo.
echo Please install Python from:
echo   - Microsoft Store: Search "Python 3.12"
echo   - Official site: https://www.python.org/downloads/
echo.
pause
exit /b 1

:TestVenv
echo.
echo ========================================
echo Python installation: OK
echo ========================================
echo.
echo Now testing virtual environment creation...
call setup.bat

echo.
echo ========================================
echo Test Complete!
echo ========================================
pause
