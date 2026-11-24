@echo off
rem Affiche les 40 dernieres lignes du journal du PC.
cd /d "%~dp0.."
powershell -command "Get-Content logs\pc.log -Tail 40"
echo.
pause
