@echo off
rem Affiche les prochains passages des taches planifiees ShadowLedger (lecture seule).
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'ShadowLedger PC*' | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, NextRunTime | Format-Table -AutoSize"
echo.
pause
