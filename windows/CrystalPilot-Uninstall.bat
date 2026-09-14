@echo off
title Remove CrystalPilot
rem Removes CrystalPilot from this computer (the Apps & features entry does the same).
rem Your projects live in the Linux runtime; you are asked whether to keep it.
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0CrystalPilot-Uninstall.ps1" %*
