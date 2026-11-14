@echo off
rem Lance un passage du PC : lancer_pc.bat daily   |   lancer_pc.bat weekly
rem Appelé par le Planificateur de tâches (voir installer_taches.ps1). Journal : logs\pc.log
cd /d "%~dp0\..\.."
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
echo ===== %date% %time% passage %1 >> logs\pc.log
py -3 pipeline\pc.py %1 >> logs\pc.log 2>&1
exit /b %errorlevel%
