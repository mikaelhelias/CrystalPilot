@echo off
title CrystalPilot
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" %*
if not "%errorlevel%"=="0" (
    echo.
    echo CrystalPilot could not start. See the messages above.
    pause
)
