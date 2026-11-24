@echo off
rem Passage quotidien complet (comme la tache planifiee). Le verrou refuse un 2e passage en meme temps.
cd /d "%~dp0.."
py -3 pipeline\pc.py daily
echo.
pause
