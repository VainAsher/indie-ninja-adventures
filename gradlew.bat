@echo off
setlocal

set "ROOT_DIR=%~dp0"
pushd "%ROOT_DIR%java" >nul
call ".\gradlew.bat" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

endlocal & exit /b %EXIT_CODE%
