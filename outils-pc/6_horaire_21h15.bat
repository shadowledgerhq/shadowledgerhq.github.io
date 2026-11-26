@echo off
rem Passe la tache planifiee quotidienne du PC a 21h15 (apres le passage GitHub de 20h). A lancer une seule fois.
powershell -NoProfile -Command "Set-ScheduledTask -TaskName 'ShadowLedger PC quotidien' -Trigger (New-ScheduledTaskTrigger -Daily -At 21:15); Get-ScheduledTask -TaskName 'ShadowLedger PC quotidien' | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime"
echo.
pause
