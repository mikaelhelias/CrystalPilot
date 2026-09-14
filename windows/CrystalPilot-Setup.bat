@echo off
title CrystalPilot setup
rem Graphical installer (wizard). Scripted install:  powershell -ExecutionPolicy Bypass -File wizard.ps1 -Unattended -Config choices.json
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0wizard.ps1" %*
if not "%errorlevel%"=="0" (
    echo.
    echo The installer reported a problem. See the messages above.
    pause
)
