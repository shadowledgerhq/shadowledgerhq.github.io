# Crée les 2 tâches du Planificateur de tâches Windows (à lancer une fois, dans PowerShell, depuis le dossier du dépôt).
# Heure locale du PC = heure de Paris. « Exécuter dès que possible si l'heure est manquée » = StartWhenAvailable.
# Les tâches tournent sous ton compte, session ouverte (Git, yt-dlp et Tesseract utilisent ton PATH et tes identifiants).
# Une tâche déjà en cours n'est pas relancée (IgnoreNew). Journal : logs\pc.log
$bat = Join-Path $PSScriptRoot "lancer_pc.bat"
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 6)

Register-ScheduledTask -TaskName "ShadowLedger PC quotidien" -Force -Settings $reglages `
  -Action (New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`" daily") `
  -Trigger (New-ScheduledTaskTrigger -Daily -At 20:30) | Out-Null

Register-ScheduledTask -TaskName "ShadowLedger PC hebdomadaire" -Force -Settings $reglages `
  -Action (New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`" weekly") `
  -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At 01:15) | Out-Null

Get-ScheduledTask -TaskName "ShadowLedger PC*" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime | Format-Table -AutoSize
Write-Host "Tâches créées. Test immédiat : Start-ScheduledTask -TaskName 'ShadowLedger PC quotidien' (puis lire logs\pc.log)"
