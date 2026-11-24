@echo off
rem Traite UNE video (test). Demande son identifiant (11 caracteres).
cd /d "%~dp0.."
set /p ID=Identifiant de la video : 
py -3 pipeline\pc.py daily --video %ID%
echo.
pause
