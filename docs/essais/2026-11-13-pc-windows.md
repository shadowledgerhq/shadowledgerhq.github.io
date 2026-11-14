# Essai pc.py sous Windows — 13/11/2026

- Commande : `py -3 pipeline\pc.py daily --no-git --max 2` (semaine 2026-11-12), durée ≈ 5 h.
- Environnement : Windows 11, Python 3.15.2, yt-dlp 2026.10.26 (+ curl-cffi installé après l'essai), Tesseract 5.5.3 (eng, jpn, kor), ffmpeg 9.0.2.
- Lectures : `2026-11-13-pc-windows-lectures.json` (copie de `data/runs/2026-11-12/_lectures.json` après l'essai). **Aucune lecture issue des images** : 12 lectures, toutes `titre` ou `description`.

Sortie de la console :
```
Semaine 2026-11-12 : 2 vidéo(s) traitée(s).
- 37 vidéo(s) reportée(s) au prochain passage (limite 2)
- lGDbzyIJcjY : yt-dlp code 1 : then see  https://github.com/yt-dlp/yt-dlp#impersonation  for information on installing the required dependencies
ERROR: Unable to download video subtitles for 'fr': HTTP Error 429: Too Many Requests
- 24 vidéo(s) reportée(s) pour les images (limite 15)
- Aqj1crEcrD4 : durée PT35M2S hors limite (30 min), images non traitées
- SDMrcxG50LI : durée PT37M45S hors limite (30 min), images non traitées
- a-923ClD9Rc : images : Command ['tesseract', 'C:\\Users\\…\\Temp\\tmpvveuzca4\\f1_0001.png', 'stdout', '-l', 'eng+kor+jpn', '--psm', '6'] timed out after 120 seconds
- 34 vidéo(s) restent en_cours (tris 3-4 : OCR sur l'image entière, recadrages [EN ATTENTE])
```
