# Installation du script PC (Windows)

Le script `pipeline/pc.py` tourne sur le PC d'Alexis : sous-titres (yt-dlp), Whisper (facultatif), tris 3-4 (images : yt-dlp + ffmpeg + tesseract), classement, puis `git push`. Premier essai Windows le 13/11 (Python 3.15.2, Tesseract 5.5.3, ffmpeg 9.0.2) : corrections du 14/11 ci-dessous, **à re-tester**.

## Une seule fois
1. Installer Python (3.12 ou plus récent ; python.org, cocher « Add to PATH »), puis dans une invite de commandes : `py -3 -m pip install tzdata "yt-dlp[default,curl-cffi]"`.
   - **PATH de yt-dlp** : `pip` place `yt-dlp.exe` dans le dossier `Scripts` de Python, qui n'est pas dans le PATH. Avec Python 3.15 : ajouter `%LOCALAPPDATA%\Python\pythoncore-3.15-64\Scripts` au PATH (Paramètres → Système → Informations système → Paramètres système avancés → Variables d'environnement → `Path` de l'utilisateur → Nouveau), puis ouvrir une **nouvelle** invite de commandes. Test : `yt-dlp --version`.
2. Installer Git for Windows, ffmpeg (`winget install Gyan.FFmpeg`) et Tesseract (`winget install UB-Mannheim.TesseractOCR`).
   - **Installateur Tesseract** : à l'étape « Choose Components », déplier **Additional language data** et cocher **Korean** et **Japanese** (l'anglais est déjà là).
   - **PATH de Tesseract** : l'installateur ne l'ajoute pas. Ajouter `C:\Program Files\Tesseract-OCR` au PATH (même procédure que ci-dessus), nouvelle invite, puis `tesseract --list-langs` doit montrer eng, kor, jpn.
   - Se connecter à GitHub (Git Credential Manager le propose au premier `git push`).
3. Cloner le dépôt : `git clone https://github.com/shadowledgerhq/shadowledgerhq.github.io.git`
4. Essai à blanc (ne pousse rien) : `py -3 pipeline\pc.py daily --no-git --max 2` (voir « Tris 3-4 »).
5. Créer les tâches : PowerShell, dans le dossier du dépôt : `powershell -ExecutionPolicy Bypass -File pipeline\pc\installer_taches.ps1`
   - quotidien 20:30, hebdomadaire jeudi 01:15, « exécuter dès que possible si l'heure est manquée » ;
   - journal : `logs\pc.log` (non versionné).

## Whisper (facultatif, lent)
`py -3 -m pip install openai-whisper`, puis dans `pipeline/config/etape1.json` : `"pc": {"whisper_cmd": "whisper", …}` et lancer avec `--whisper`. Seules les vidéos de 15 minutes ou moins, sans sous-titres ni score, sont transcrites.

## Tris 3-4 (images)
- Tri 3 : 10 premières et 30 dernières secondes, 1 image / 2 s ; tri 4 (seulement si le tri 3 ne suffit pas) : vidéo entière, 1 image / 10 s. Vidéos de 30 min maximum. La vidéo est téléchargée en 720p max dans un dossier temporaire, puis supprimée.
- **`--max N` limite maintenant les sous-titres ET les images** (N vidéos de chaque). Sans `--max` : 300 vidéos de sous-titres et 15 d'images par passage (`pc.max_videos`, `pc.images.max_videos` dans `pipeline/config/etape1.json`).
- **Progression** : une ligne par vidéo (`[3/15] <id> « titre » : images`), puis le détail du tri (images, écrans lus, images trop lentes, durée). Dans une tâche planifiée, tout va dans `logs\pc.log`.
- **Enregistrement après chaque vidéo** : `_lectures.json` et `processed.json` sont écrits à chaque vidéo. Arrêt (Ctrl+C, PC éteint) = seule la vidéo en cours est perdue.
- **OCR plus rapide** :
  - langues selon le mode de la vidéo (BOT et GB : `eng` ; POC et HOTM : `kor+eng`) ;
  - tri 3 : OCR complet de **toutes** les images (10 premières et 30 dernières secondes) ; tri 4 : lecture rapide d'abord (image réduite à 960 px, `--psm 11`, 40 s maximum), puis lecture complète **seulement** si le texte ressemble à un écran RESULT ;
  - Guild Boss : quand le HUD montre un chrono de 15 s ou moins, les 30 secondes suivantes sont lues à 1 image/s jusqu'à l'écran `Results` ;
  - images identiques lues une seule fois ; image trop lente (90 s) ignorée, le passage continue ;
  - budget par vidéo (15 min : au-delà la vidéo est reprise au passage suivant, 2 essais puis abandon) et par passage (180 min) ;
  - `OMP_THREAD_LIMIT=1` pour tesseract (le multithread d'OpenMP le ralentit sous Windows).
  Réglages : `pc.images.*` et `pc.budget_minutes`. **Non mesuré sur vos images** : si c'est encore trop lent, `--garder-ocr` écrit le texte lu dans `logs\ocr\` pour voir ce qui est lu.
- **Erreur 429 de YouTube** : pause de 5 s entre les vidéos (`pc.pause_s`). En cas de 429, le passage s'arrête pour les sous-titres (ou les images), la vidéo n'est pas marquée et sera reprise au passage suivant. Si ça persiste : dans `pipeline/config/etape1.json`, mettre `"yt_dlp_options": ["--impersonate", "chrome"]` dans `pc` (demande `yt-dlp[default,curl-cffi]`).
- Les valeurs lues sont contrôlées (somme des phases, Final Score, Total Rage Count…) ; sans contrôle réussi, la lecture reste « à vérifier ». L'OCR lit l'**image entière** : les recadrages par zone attendent les images de référence.
- **Diagnostic partagé** : `--publier-essai` (comme `--garder-ocr`, puis copie les 6 images les mieux lues, en JPEG, et leurs textes dans `docs/essais/ocr/` et les pousse sur GitHub). `--video <id>` limite le passage à une vidéo ; ajouter `--refaire` pour la retraiter même si elle est déjà faite.
- Essai conseillé : `py -3 pipeline\pc.py daily --no-git --max 2 --garder-ocr`, puis lire `data/runs/<semaine>/_lectures.json`.

## Gel de la semaine
`pc.geler` reste `false` tant que l'OCR n'a pas été vérifié sur de vraies captures. Une fois `true` : le passage hebdomadaire gèle la semaine, rejette (`pas_de_score`) les vidéos sans aucun score après le tri 4, et marque « non vérifié » les lignes seulement provisoires.
