# Test des zones GB sur 6 vidéos — 14/11/2026 (discussion Code)

Commande : `py -3 pipeline\pc.py daily --no-git --video … (6 vidéos) --refaire --publier-essai`, code v14 (1424d14). Bilan brut : `docs/essais/ocr/_resume_6videos.json`. Images et textes : `docs/essais/ocr/<vidéo>_*`. Durée : 24 min.

| Vidéo | Joueur / client | Formats YouTube | Image lue | Écran Results lu | Résultat |
|---|---|---|---|---|---|
| `awb-GlVIa7Q` | Ahmad1195, anglais, 189 RC, 64.2 T | 144 p à **1440 p** | 1280×720 | oui (227 s, 9 images fusionnées) | `a_verifier` : conflit `rage_count` (189 ×5, 183 ×3, 1 ×1) |
| `nh2D7xZ7dOQ` | SlayOnLow, anglais, 165 RC | 144 p à 1080 p | 1280×720 | non | salon Guild Boss pris à tort pour un Results (corrigé) ; ffmpeg bloqué 900 s au tri 4 (corrigé) |
| `T5dR6iJAn-Y`, `Oj_-5x6700s` | RaidenShadow, **portugais** | 144 p à 1080 p | 1280×720 | non | HUD en portugais non reconnu |
| `vYtRCpFtSOk`, `MJ2iz5TFmvM` | Eden, **coréen** | 144 p à 1080 p | 1280×720 | non | fin de vidéo = menu des sculptures (조각상), pas de Results ; HUD coréen non reconnu |

## Résolution
Toutes les vidéos proposent 1080 p (une propose 1440 p), mais le script télécharge en 720 p maximum (`images.format_video`) : toutes les images lues font 1280×720. Le test en 1080 p (`--resolution 1080`) reste à faire.

## awb-GlVIa7Q (la seule avec un Results lu)
- Personal Record du salon, vu à 241 s : `Total Score 64,299,126,429,862`, `Total Rage Count 189`, `Group 1 189 · 64.29T`, `Group 2 No history`, `Time Left in Season 6d 22h`. C'est la source la plus lisible de la vidéo ; la lecture de ce record était écartée par la recherche de l'écran Results (corrigé).
- Results (images fusionnées, 227 à 242 s) : `Final Score` lu 64,299,126,425 (×5) et 64,299,126,429 (×3) : 11 chiffres au lieu de 14, la zone ou l'OCR tronque les nombres en billions ; `Player's Score` 795,244,088,074 ; Hunter Rank 1 à 6 lus mais instables (rang 1 : 88,332,559,253 ×4 contre 188,332,559,253 ×3). Les zones, réglées sur un `Final Score` de 1,6 milliard, ne conviennent pas aux nombres de 14 chiffres.
- HUD : dernière lecture à 200 s (chrono 12,78 s) : `Points` 56,127,069,781,883 pour un Final Score de 64,3 T. Pas de HUD à chrono ≤ 5 s : l'écart HUD / Final Score n'est pas mesurable ici.
- RC : 189 (×5), 183 (×3), 1 (×1) : la règle v14 donne un conflit. Le `Rage Count` pourrait s'animer pendant l'affichage (à vérifier sur les images).

## T5dR6iJAn-Y et Oj_-5x6700s (portugais)
HUD lu : `Pontos 7.884.144.289.064` à 0,80 s de la fin (titre : « Score : 7,9T ») ; `Número de Fúrias do Chefão 120` (titre : « Rage : 159 ») ; `Estátua de Pedra Gigante` ; `Equipe A` / `Equipe B` ; `WARNING`. Deuxième vidéo : `Pontos 3.087…` (titre : « Score : 3T »). Les `Pontos` du HUD correspondent donc au score du titre. Le `Número de Fúrias do Chefão` (120) ne correspond pas au RC du titre (159), comme le `Boss Rage Count` anglais. Libellés de l'écran Results en portugais : inconnus (images de fin de vidéo non publiées ce jour).

## vYtRCpFtSOk et MJ2iz5TFmvM (coréen)
Les 30 dernières secondes montrent le menu des sculptures (`조각상`), pas l'écran Results. La run est ailleurs dans la vidéo (7 min). Libellés coréens du HUD et du Results : inconnus.

## nh2D7xZ7dOQ
La vidéo commence par le salon Guild Boss : `Personal Record` `Total Score 32,842,054,460,310`, `Total Rage Count 332`, `Group 1 167 · 17.28T`, `Group 2 165 · 15.55T`, `Time Left in Season 6d 9h`. Le bouton `Rage Rewards` du salon a fait reconnaître un Results partiel : lecture parasite RC 3 (corrigé : « Rage Rewards » seul ne suffit plus). Au tri 4, ffmpeg est resté bloqué 900 s : la vidéo n'a pas été analysée (corrigé : `-nostdin`, délai 300 s, une nouvelle tentative).

## RaidenShadow et Eden (somme groupe 1 + groupe 2)
Non vérifiable : aucun écran Results lu pour ces 4 vidéos.

## À décider (discussion 1)
1. Libellés du HUD et du Results en **portugais** et **coréen** (images à publier au prochain essai).
2. Nombres à 14 chiffres (billions) : zones plus larges, ou lecture du `Total Score` du Personal Record (lisible, exact) comme source du Final Score.
3. Le Personal Record (RC et Total Score) lu dans le salon reste la source la plus fiable de ces vidéos : confirmer qu'il prime quand le Results est conflictuel.
