@echo off
chcp 65001 >nul
rem Installation en un double-clic : met le dépôt à jour, crée les tâches du Planificateur de tâches, lance un test.
rem À faire une fois (et après chaque mise à jour des scripts). Journal des passages : logs\pc.log
cd /d "%~dp0\..\.."
echo.
echo === Shadow Ledger : installation du PC ===
echo.
echo [1/4] Remise à zéro des données locales d'essai...
git checkout -- data
if errorlevel 1 goto erreur_git
echo [2/4] Récupération de la dernière version...
git pull origin main
if errorlevel 1 goto erreur_git
echo [3/4] Création des tâches planifiées...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_taches.ps1"
if errorlevel 1 goto erreur
echo [4/4] Lancement d'un passage de test (il tourne en arrière-plan, plusieurs heures possibles)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-ScheduledTask -TaskName 'ShadowLedger PC quotidien'"
if errorlevel 1 goto erreur
echo.
for /f "delims=" %%i in ('powershell -NoProfile -Command "(Get-ScheduledTaskInfo -TaskName 'ShadowLedger PC hebdomadaire').NextRunTime.ToString('dddd dd/MM/yyyy HH:mm')"') do set HEBDO=%%i
echo ========================================================================
echo  Tâches créées. Test lancé maintenant.
echo  Passages quotidiens : tous les soirs à 19:30, 21:30 et 23:30 (PC allumé, session ouverte).
echo  Prochain passage hebdomadaire : %HEBDO%
echo  Journal : logs\pc.log    Rapport poussé : data\runs\^<semaine^>\_rapport.md
echo ========================================================================
echo.
pause
exit /b 0
:erreur_git
echo.
echo ERREUR git : copie ce message à Claude (discussion Code). Rien n'a été installé.
pause
exit /b 1
:erreur
echo.
echo ERREUR pendant l'installation : copie ce message à Claude (discussion Code).
pause
exit /b 1
