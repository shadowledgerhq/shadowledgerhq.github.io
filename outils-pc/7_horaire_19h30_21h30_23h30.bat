@echo off
rem Passe la tache quotidienne a 19h30, 21h30 et 23h30 (toutes les 2 h pendant 5 h). A lancer une seule fois.
powershell -NoProfile -Command "$t = New-ScheduledTaskTrigger -Daily -At 19:30; $t.Repetition = (New-ScheduledTaskTrigger -Once -At 19:30 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Hours 5)).Repetition; Set-ScheduledTask -TaskName 'ShadowLedger PC quotidien' -Trigger $t | Out-Null; $x = Get-ScheduledTask -TaskName 'ShadowLedger PC quotidien'; $x.Triggers | Select-Object StartBoundary, @{n='Repetition';e={$_.Repetition.Interval + ' pendant ' + $_.Repetition.Duration}}; $x | Get-ScheduledTaskInfo | Select-Object NextRunTime"
echo.
pause
