# Crée les 2 tâches du Planificateur de tâches Windows (à lancer une fois, dans PowerShell, depuis le dossier du dépôt).
# Heure locale du PC = heure de Paris. « Exécuter dès que possible si l'heure est manquée » = StartWhenAvailable.
$bat = Join-Path $PSScriptRoot "lancer_pc.bat"
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 6)

Register-ScheduledTask -TaskName "ShadowLedger PC quotidien" -Force -Settings $reglages `
  -Action (New-ScheduledTaskAction -Execute $bat -Argument "daily") `
  -Trigger (New-ScheduledTaskTrigger -Daily -At 20:30)

Register-ScheduledTask -TaskName "ShadowLedger PC hebdomadaire" -Force -Settings $reglages `
  -Action (New-ScheduledTaskAction -Execute $bat -Argument "weekly") `
  -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At 01:15)

Write-Host "Tâches créées. Test immédiat : Start-ScheduledTask -TaskName 'ShadowLedger PC quotidien'"
