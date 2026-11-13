# Installation du script PC (Windows)

Le script `pipeline/pc.py` tourne sur le PC d'Alexis : sous-titres (yt-dlp), Whisper (facultatif), tris 3-4 (OCR : **pas encore codés**), classement, puis `git push`. Non testé sous Windows à ce jour.

## Une seule fois
1. Installer Python 3.12 (python.org, cocher « Add to PATH »), puis dans une invite de commandes : `py -3 -m pip install tzdata yt-dlp`.
2. Installer Git for Windows et ffmpeg (ex. `winget install Gyan.FFmpeg`). Se connecter à GitHub (Git Credential Manager le propose au premier `git push`).
3. Cloner le dépôt : `git clone https://github.com/shadowledgerhq/shadowledgerhq.github.io.git`
4. Essai à blanc (ne pousse rien) : `py -3 pipeline\pc.py daily --no-git`
5. Créer les tâches : PowerShell, dans le dossier du dépôt : `powershell -ExecutionPolicy Bypass -File pipeline\pc\installer_taches.ps1`
   - quotidien 20:30, hebdomadaire jeudi 01:15, « exécuter dès que possible si l'heure est manquée » ;
   - journal : `logs\pc.log` (non versionné).

## Whisper (facultatif, lent)
`py -3 -m pip install openai-whisper`, puis dans `pipeline/config/etape1.json` : `"pc": {"whisper_cmd": "whisper", …}` et lancer avec `--whisper`. Seules les vidéos de 15 minutes ou moins, sans sous-titres ni score, sont transcrites.

## Gel de la semaine
`pc.geler` reste `false` tant que l'OCR n'est pas codé : le passage hebdomadaire traite la semaine écoulée mais ne la gèle pas.
