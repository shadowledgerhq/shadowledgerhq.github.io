# Crée les 2 tâches du Planificateur de tâches Windows (à lancer une fois, dans PowerShell, depuis le dossier du dépôt).
# Heure locale du PC = heure de Paris. « Exécuter dès que possible si l'heure est manquée » = StartWhenAvailable.
# Les tâches tournent sous ton compte, session ouverte (Git, yt-dlp et Tesseract utilisent ton PATH et tes identifiants).
# Une tâche déjà en cours n'est pas relancée (IgnoreNew). Journal : logs\pc.log
$bat = Join-Path $PSScriptRoot "lancer_pc.bat"
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 6)

# 19:30, 21:30 et 23:30 (répétition toutes les 2 h pendant 5 h ; choix d'Alexis, 26/11)
$declencheurQuotidien = New-ScheduledTaskTrigger -Daily -At 19:30
$declencheurQuotidien.Repetition = (New-ScheduledTaskTrigger -Once -At 19:30 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Hours 5)).Repetition
Register-ScheduledTask -TaskName "ShadowLedger PC quotidien" -Force -Settings $reglages `
  -Action (New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`" daily") `
  -Trigger $declencheurQuotidien | Out-Null

Register-ScheduledTask -TaskName "ShadowLedger PC hebdomadaire" -Force -Settings $reglages `
  -Action (New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`" weekly") `
  -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At 01:15) | Out-Null

Get-ScheduledTask -TaskName "ShadowLedger PC*" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime | Format-Table -AutoSize
Write-Host "Tâches créées. Test immédiat : Start-ScheduledTask -TaskName 'ShadowLedger PC quotidien' (puis lire logs\pc.log)"
