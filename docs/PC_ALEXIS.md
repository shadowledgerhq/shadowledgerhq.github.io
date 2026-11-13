# Installation du script PC (Windows)

Le script `pipeline/pc.py` tourne sur le PC d'Alexis : sous-titres (yt-dlp), Whisper (facultatif), tris 3-4 (images : yt-dlp + ffmpeg + tesseract), classement, puis `git push`. Non testé sous Windows ni sur de vraies captures à ce jour.

## Une seule fois
1. Installer Python 3.12 (python.org, cocher « Add to PATH »), puis dans une invite de commandes : `py -3 -m pip install tzdata yt-dlp`.
2. Installer Git for Windows, ffmpeg (`winget install Gyan.FFmpeg`) et Tesseract (`winget install UB-Mannheim.TesseractOCR`, puis ajouter les langues **kor** et **jpn** à l'installation ; `tesseract --list-langs` doit montrer eng, kor, jpn). Se connecter à GitHub (Git Credential Manager le propose au premier `git push`).
3. Cloner le dépôt : `git clone https://github.com/shadowledgerhq/shadowledgerhq.github.io.git`
4. Essai à blanc (ne pousse rien) : `py -3 pipeline\pc.py daily --no-git`
5. Créer les tâches : PowerShell, dans le dossier du dépôt : `powershell -ExecutionPolicy Bypass -File pipeline\pc\installer_taches.ps1`
   - quotidien 20:30, hebdomadaire jeudi 01:15, « exécuter dès que possible si l'heure est manquée » ;
   - journal : `logs\pc.log` (non versionné).

## Whisper (facultatif, lent)
`py -3 -m pip install openai-whisper`, puis dans `pipeline/config/etape1.json` : `"pc": {"whisper_cmd": "whisper", …}` et lancer avec `--whisper`. Seules les vidéos de 15 minutes ou moins, sans sous-titres ni score, sont transcrites.

## Tris 3-4 (images)
- Tri 3 : 10 premières et 30 dernières secondes, 1 image / 2 s ; tri 4 (seulement si le tri 3 ne suffit pas) : vidéo entière, 1 image / 10 s. Vidéos de 30 min maximum, 15 vidéos par passage (`pc.images` dans `pipeline/config/etape1.json`). La vidéo est téléchargée en 720p max dans un dossier temporaire, puis supprimée.
- L'OCR lit l'**image entière** : les recadrages par zone attendent les images de référence. Les valeurs lues sont contrôlées (somme des phases, Final Score, Total Rage Count…) ; sans contrôle réussi, la lecture reste « à vérifier ».
- Premier essai conseillé : `py -3 pipeline\pc.py daily --no-git --max 2`, puis lire `data/runs/<semaine>/_lectures.json`.

## Gel de la semaine
`pc.geler` reste `false` tant que l'OCR n'a pas été vérifié sur de vraies captures. Une fois `true` : le passage hebdomadaire gèle la semaine, rejette (`pas_de_score`) les vidéos sans aucun score après le tri 4, et marque « non vérifié » les lignes seulement provisoires.
