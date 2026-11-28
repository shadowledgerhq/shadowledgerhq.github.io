# GABARIT — vidéos de guide Shadow Ledger — v2 (2026-11-28 : gabarits POC et GB)

Demandeur : discussion 3 (Theorycraft & vidéos). Code : discussion 8. Vidéos 100 % schémas (CONTEXTE §4, étape 3b) : aucune image de tiers, tout est dessiné.

## 1. Fichiers par vidéo : `videos/<semaine>/<mode>/`
| Fichier | Rôle |
| --- | --- |
| `video.json` | **Source unique** : scènes, durées, texte FR/EN, storyboard, sources, estimations. Écrit par la discussion 3. |
| `script.md` | Généré depuis `video.json` (`pipeline/video/script_md.py`) : minutage, storyboard, narration FR/EN côte à côte. Jamais modifié à la main. |
| `<mode>-<semaine>-<fr|en>[-vertical].mp4` | Rendu (`pipeline/video/rendu.py`). **Pas dans le dépôt** (poids) : gardé sur le PC ; envoi YouTube en « Privé » seulement avant le lancement. |

Modes : `poc`, `bot`, `gb` (HOTM arrêté le 28/11/2026, décision d'Alexis : plus de vidéo HOTM).

**Clip vertical** (TikTok, Shorts, Reels ; `--vertical`) : 1080 × 1920, scènes listées dans `video.json["vertical"]["scenes"]` (par défaut intro 2 s, timeline, outro 3 s). Zone sûre (`docs/reseaux/RESEAUX.md` §4) : rien dans les 20 % du bas ni le long du bord droit ; titre, bandeau et sources en haut, sous-titres juste au-dessus de la zone du bas. Intro sans son, la voix commence après l'intro.

## 2. Structure type BOT (≈ 75-90 s)
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

### 2.1 POC (≈ 2-3 min) — refonte du 19/11/2026 (`docs/SPEC_ETAPE1.md` §9)
| # | Scène (`type`) | Durée | Contenu |
| --- | --- | --- | --- |
| 1 | `intro` | 2 s | Bandeau `POC · Semaine du JJ/MM` |
| 2 | `titre` | 3-4 s | Boss / saison POC, palier record de la semaine |
| 3 | `tableau` | 10-12 s | Top 5 dans l'ordre du classement : **palier**, puis **Goal Progress**, puis **Rank Score** ; ex aequo affichés au même rang ; « à vérifier » si non `sûr` |
| 4 | `barres` | 10 s | « Qui fait tomber le boss » : par joueur du top 3, barre 0-100 % des PV du palier = Team 1 % + Team 2 % + reste (contrôle b : Goal Progress = Team 1 + Team 2) |
| 5 | `barres` | 10 s | Contributions d'une équipe : Player (SJW) + Successor + Hunter 1-3 = Total Contribution (si lues ; sinon scène omise). Total Contribution = information, **jamais un critère** |
| 6 | `timeline` | 20-30 s | Une ligne par équipe de la meilleure run (`run_index` 1 et 2), puis 2e joueur |
| 7 | `points` | 10-15 s | Repères (estimations signalées) |
| 8 | `build` | 10-15 s | 2 colonnes : équipe 1, équipe 2 (élément informatif) |
| 9 | `team` (à venir) | 20-30 s | Deux équipes théoriques sans chasseur commun ; gain estimé en % de PV, calcul cité |
| 10 | `points` (limites) | 5-8 s | |
| 11 | `outro` | 5 s | |

### 2.2 GB (≈ 2-3 min)
| # | Scène (`type`) | Durée | Contenu |
| --- | --- | --- | --- |
| 1 | `intro` | 2 s | Bandeau `GB · Semaine du JJ/MM` |
| 2 | `titre` | 3-4 s | Boss de guilde, attributs variables de la semaine (si lus) |
| 3 | `tableau` | 10-12 s | Top 5 : RC total, RC groupe 1, RC groupe 2, dégâts (départage) ; seules les runs **filmées** (Results) comptent |
| 4 | `barres` | 10 s | RC par groupe pour le top 3 (groupe 1 + groupe 2 = total) |
| 5 | `barres` | 10 s | Final Score d'un groupe = Player's Score + 6 Hunter Rank (si lus ; sinon scène omise) |
| 6 | `timeline` | 20-30 s | Une ligne par groupe (`run_index` 1 et 2) |
| 7 | `points` | 10-15 s | |
| 8 | `build` | 10-15 s | 2 colonnes : groupe 1, groupe 2 (6 chasseurs + SJW chacun) |
| 9 | `team` (à venir) | 20-30 s | Deux groupes théoriques sans chasseur commun ; RC estimé, calcul cité |
| 10 | `points` (limites) | 5-8 s | |
| 11 | `outro` | 5 s | |

Clip vertical POC et GB : intro, `barres` (scène 4), `timeline`, outro 3 s.

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
 "scenes": [{"id": "", "type": "intro | titre | classement | phases | tableau | barres | timeline | points | build | outro",
   "duration": 0, "title": {"fr": "", "en": ""},
   "narration": [{"t": 0.3, "fr": "", "en": ""}],
   "storyboard": "", "sources": [], "estimates": []}]}
```
Champs propres à chaque type : voir `videos/2026-11-12/bot/video.json` (exemple complet). `timeline.rows[].file` pointe vers le relevé de rotation ; un `t_game` absent est interpolé sur `t_run` et dessiné creux (estimation).

### 4.1 Types génériques (v2, pour POC et GB ; BOT peut les utiliser aussi)
- **`tableau`** : `columns: [{"key": "", "head": {"fr": "", "en": ""}, "fmt": "texte | entier | pct | chrono | rank_score | rc | degats", "accent": false}]`, `rows: [{"rang": 1, "<key>": valeur, "etat": "sur | a_verifier", "note": {"fr": "", "en": ""}}]`, `footnote`. Rang identique = ex aequo. Formats : `pct` 2 décimales + « % » ; `rank_score` et `entier` avec séparateurs (espace fine en FR, virgule en EN) ; `degats` abrégé (T, B) avec « ≈ » si `exact: false` ; `rc` = « 332 RC ».
- **`barres`** : `axis_max` (100 pour des %, sinon la plus grande somme), `unit`, `rows: [{"label": "", "sub": {"fr": "", "en": ""}, "segments": [{"value": 0, "label": {"fr": "", "en": ""}, "color": "sjw | hun | tag | ok | muted | warn", "est": false}], "total": {"fr": "", "en": ""}}]`. Segments empilés de gauche à droite, valeur écrite dans le segment s'il est assez large ; `est: true` = hachuré + étiquette ESTIMATION ; animation : croissance de gauche à droite, une ligne après l'autre.
- **`timeline`** : `rows[].run_index` (défaut : dernière run du fichier) choisit l'entrée de `runs[]` (POC : équipe ; GB : groupe).
- **`build`** : nombre de colonnes libre (POC/GB : 2).

Exemples à données **fictives** (pour tester le rendu, jamais publiés) : `videos/_exemples/poc/video.json`, `videos/_exemples/gb/video.json`.
