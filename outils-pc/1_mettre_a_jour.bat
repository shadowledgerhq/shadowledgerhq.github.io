@echo off
rem Recupere le code et les donnees du depot, puis met yt-dlp a jour.
cd /d "%~dp0.."
git pull origin main
python -m pip install -U "yt-dlp[default,curl-cffi]"
yt-dlp --version
echo.
echo Termine.
pause
