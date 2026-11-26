@echo off
rem Remet la repetition de la tache quotidienne : 21h15, 23h15 et 01h15 (toutes les 2 h pendant 5 h). A lancer une seule fois.
powershell -NoProfile -Command "$t = New-ScheduledTaskTrigger -Daily -At 21:15; $t.Repetition = (New-ScheduledTaskTrigger -Once -At 21:15 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Hours 5)).Repetition; Set-ScheduledTask -TaskName 'ShadowLedger PC quotidien' -Trigger $t | Out-Null; $x = Get-ScheduledTask -TaskName 'ShadowLedger PC quotidien'; $x.Triggers | Select-Object StartBoundary, @{n='Repetition';e={$_.Repetition.Interval + ' pendant ' + $_.Repetition.Duration}}; $x | Get-ScheduledTaskInfo | Select-Object NextRunTime"
echo.
pause
