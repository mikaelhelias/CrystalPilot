@echo off
title CrystalPilot - stop
set WSL_UTF8=1
set "DISTRO=%CRYSTALPILOT_DISTRO%"
if exist "%~dp0crystalpilot.cfg" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0crystalpilot.cfg") do (
        if /i "%%a"=="DISTRO" if not defined DISTRO set "DISTRO=%%b"
    )
)
if defined DISTRO (
    wsl.exe -d %DISTRO% -e /usr/local/bin/crystalpilot stop
) else (
    wsl.exe -e /usr/local/bin/crystalpilot stop
)
rem short pause so the message can be read (works without a console too)
ping -n 3 127.0.0.1 >nul
