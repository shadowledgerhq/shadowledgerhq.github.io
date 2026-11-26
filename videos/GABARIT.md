# GABARIT —  vidéos de guide Shadow Ledger — v1 (2026-11-26)

Demandeur : discussion 3 (Theorycraft & vidéos). Code : discussion 8. Vidéos 100 % schémas (CONTEXTE §4, étape 3b) : aucune image de tiers, tout est dessiné.

## 1. Fichiers par vidéo : `videos/<semaine>/<mode>/`
| Fichier | Rôle |
| --- | --- |
| `video.json` | **Source unique** : scènes, durées, texte FR/EN, storyboard, sources, estimations. Écrit par la discussion 3. |
| `script.md` | Généré depuis `video.json` (`videos/_prototype/script_md.py`, à reprendre par Code dans `pipeline/`) : minutage, storyboard, narration FR/EN côte à côte. Jamais modifié à la main. |
| `<mode>-<semaine>-<fr|en>[-vertical].mp4` | Rendu (`videos/_prototype/rendu_video.py`, idem). **Pas dans le dépôt** (poids) : gardé sur le PC ; envoi YouTube en « Privé » seulement avant le lancement. |

HOTM : `<mode>` = `hotm-gate-<n>`.

**Clip vertical** (TikTok, Shorts, Reels ; `--vertical`) : 1080 × 1920, scènes listées dans `video.json["vertical"]["scenes"]` (par défaut intro 2 s, timeline, outro 3 s). Zone sûre (`docs/reseaux/RESEAUX.md` §4) : rien dans les 20 % du bas ni le long du bord droit ; titre, bandeau et sources en haut, sous-titres juste au-dessus de la zone du bas. Intro sans son, la voix commence après l'intro.

## 2. Structure type (≈ 75-90 s pour le BOT, jusqu'à 3 min pour POC/GB/HOTM)
| # | Scène (`type`) | Durée | Contenu |
| --- | --- | --- | --- |
| 1 | `intro` | 2 s | Logo B qui se trace + bandeau du mode (`docs/reseaux/RESEAUX.md` §4) |
| 1b | `titre` | 3-4 s | Mode, boss, semaine (BOT : `S<n>-<w>`), question du guide |
| 2 | `classement` | 8-10 s | Top 5 : joueur, score, origine du score ; « à vérifier » si non confirmé |
| 3 | `phases` (BOT) | 8-10 s | Phases du Results des meilleures runs, où se fait l'écart |
| 4 | `timeline` | 15-25 s | Rotation relevée (`data/rotations/`), une ligne par run du top 3, curseur au rythme du chrono |
| 5 | `points` | 10-15 s | 3-5 repères ; chaque estimation porte l'étiquette ESTIMATION |
| 6 | `build` | 8-12 s | Composition et stuff (`data/builds/`) ; non lu = grisé, jamais complété |
| 7 | `team` (à venir) | 15-30 s | Meilleure équipe théorique : chaque choix justifié, gain estimé et calcul cité |
| 8 | `points` (limites) | 5-8 s | Ce que la vidéo ne dit pas encore |
| 9 | `outro` | 5 s exactement | Support de l'écran de fin YouTube : logo à gauche, 2 emplacements vides de 420 × 236 px à droite (x 900 et 1380, y 230 ; à vérifier dans l'éditeur YouTube au 1er envoi en « Privé »), comptes et site, crédits des joueurs (RESEAUX.md §4) |

## 3. Règles
- Narration FR et EN de **même contenu**, au plus ≈ 15 caractères par seconde de scène (lisible en sous-titres, à dire en voix).
- Sans voix : la narration s'affiche en sous-titres. Avec voix (clone d'Alexis) : une piste audio par langue, les sous-titres restent en option.
- Toute donnée non observée = estimation, signalée à l'écran (étiquette ESTIMATION, marqueur creux sur la timeline).
- Chaque scène cite ses sources (fichiers du dépôt, base de données).
- Avant le lancement : bandeau « ESSAI INTERNE · DONNÉES PROVISOIRES » sur chaque scène, données provisoires marquées « à vérifier ».
- Crédits : chaîne YouTube de chaque run utilisée, en outro (et en description de la vidéo).
- Charte (RESEAUX.md §1) : fond `#0B0D17`, violet `#7C5CFF` (SJW), bleu glace `#4FD1FF` (chasseur), texte `#EDEBFF`, police Inter ; en plus pour les schémas : ambre (changement de chasseur), vert (confirmé), rouge (à vérifier). Logo : `logo-b-sceau.svg` (champ `logo` de `video.json`).
- 1920×1080, 30 i/s, H.264 ; piste audio muette tant qu'il n'y a pas de voix.

## 4. Format de `video.json`
```json
{"gabarit": 1, "week": "2026-11-12", "mode": "bot", "boss": "Baruka", "season_week": "S20-4",
 "status": "essai-interne | final",
 "badge": {"fr": "...", "en": "..."}, "logo": "docs/reseaux/logo-b-sceau.svg", "size": [1920, 1080], "fps": 30,
 "scenes": [{"id": "", "type": "intro | titre | classement | phases | timeline | points | build | outro",
   "duration": 0, "title": {"fr": "", "en": ""},
   "narration": [{"t": 0.3, "fr": "", "en": ""}],
   "storyboard": "", "sources": [], "estimates": []}]}
```
Champs propres à chaque type : voir `videos/2026-11-12/bot/video.json` (exemple complet). `timeline.rows[].file` pointe vers le relevé de rotation ; un `t_game` absent est interpolé sur `t_run` et dessiné creux (estimation).
