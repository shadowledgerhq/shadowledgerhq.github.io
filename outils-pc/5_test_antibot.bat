@echo off
rem Anti-bot YouTube : essaie les reglages yt-dlp (aucun telechargement) et enregistre le premier qui marche dans pc_local.json.
rem A lancer si un passage affiche "anti-bot YouTube" avec 0 video traitee. Firefox : ouvrir YouTube (connecte) avant.
cd /d "%~dp0.."
python -m pip install -U "yt-dlp[default,curl-cffi]"
py -3 pipeline\pc.py ytdlp-test
echo.
pause
