# Script et storyboard — BOT 2026-11-12 (Baruka, S20-4) — essai-interne

Généré depuis `video.json` (source unique ; ne pas modifier ce fichier à la main). Sans voix : la narration s'affiche en sous-titres.

## 1. intro — 0-2 s (2 s, type `intro`)

**Storyboard** : Intro 2 s (RESEAUX.md §4) : l'hexagone du logo se trace, le « S » apparaît, puis « SHADOW LEDGER » et le bandeau du mode.

## 2. titre — 2-6 s (4 s, type `titre`)

**Storyboard** : Titre : mode, boss et semaine, question du guide en sous-titre.

| t | FR | EN |
| --- | --- | --- |
| 0.3 | BOT Baruka, S20-4 : comment passer sous les 20 secondes ? | BOT Baruka, S20-4: how do you clear it in under 20 seconds? |

## 3. classement — 6-15 s (9 s, type `classement`)

**Storyboard** : Tableau 5 lignes : rang, joueur, chrono, origine du chrono. Étiquette « à vérifier » sur chaque ligne. Note en bas : seule run sûre.

| t | FR | EN |
| --- | --- | --- |
| 0.3 | Le top 5 provisoire tient en 0,4 seconde. Aucun de ces chronos n'est encore confirmé sur l'écran Results. | The provisional top 5 fits within 0.4 seconds. None of these times is confirmed on the Results screen yet. |

Sources : data/runs/2026-11-12/bot.json (passage du 26/11/2026)

## 4. phases — 15-25 s (10 s, type `phases`)

**Storyboard** : Barres horizontales empilées (phase 1, 2, 3) pour 2 runs, durées écrites dans chaque bloc. Écart de la phase 2 souligné.

| t | FR | EN |
| --- | --- | --- |
| 0.3 | Le combat a 3 phases. Les deux runs lues finissent la phase 1 vers 9,35 s : l'écart se fait en phase 2 (0,3 s). | The fight has 3 phases. Both runs read end phase 1 around 9.35 s: the gap is made in phase 2 (0.3 s). |

Sources : data/rotations/2026-11-12/_rapport.md (phases du Results) ; data/runs/2026-11-12/bot.json

## 5. timeline — 25-46 s (21 s, type `timeline`)

**Storyboard** : Timeline 0-20 s, une ligne par run. Losanges violets = SJW, ronds bleus = chasseur, triangles ambre = changement. Lignes pointillées aux fins de phase 1 et 2. Curseur qui avance au rythme du chrono, les marqueurs apparaissent à son passage.

| t | FR | EN |
| --- | --- | --- |
| 0.3 | Chaque marqueur est une compétence relevée automatiquement, placée sur le chrono du jeu. | Each marker is a skill detected automatically, placed on the in-game timer. |
| 7.0 | Chez 홀맨 et 크리스, les changements de chasseur tombent aux mêmes instants : 12,8 s, 15,4 s et 18,3 s, à 0,25 s près. | For 홀맨 and 크리스, hunter swaps land at the same moments: 12.8 s, 15.4 s and 18.3 s, within 0.25 s. |
| 15.0 | Le guide ralenti suit un autre ordre : on ne s'en sert qu'en appui. | The slowed-down guide follows another order: it is only used as support. |

Sources : data/rotations/2026-11-12/bot/*.json (SPEC_ROTATION v2.2, passage PC du 19/11/2026)

## 6. points — 46-59 s (13 s, type `points`)

**Storyboard** : 4 cartes numérotées qui apparaissent une à une (2,5 s chacune). La carte estimée porte l'étiquette « estimation ».

| t | FR | EN |
| --- | --- | --- |
| 0.3 | Quatre repères à retenir, tirés des runs réelles. Le dernier est une estimation. | Four markers to remember, taken from real runs. The last one is an estimate. |

Texte à l'écran :

- Ouverture : une compétence de SJW dans les 2,5 premières secondes (3 runs sur 3). / *Opener: an SJW skill within the first 2.5 seconds (3 runs out of 3).*
- Changements de chasseur à 12,8 s, à 15,4 s (juste après la fin de la phase 2, 14,5 s) et à 18,3 s (홀맨 et 크리스). / *Hunter swaps at 12.8 s, at 15.4 s (right after phase 2 ends, 14.5 s) and at 18.3 s (홀맨 and 크리스).*
- Ultime du chasseur à 15,9 s, dès le début de la phase 3 (홀맨). / *Hunter ultimate at 15.9 s, as soon as phase 3 starts (홀맨).*
- Ultime de SJW une seule fois, vers 13,7 s (estimation : chrono non lu). / *SJW ultimate used once, around 13.7 s (estimate: timer not read).*

Estimations : points[3]

Sources : data/rotations/2026-11-12/bot/YSJFLd_OXww.json ; data/rotations/2026-11-12/bot/znpyCNWml3I.json ; data/rotations/2026-11-12/bot/a-923ClD9Rc.json

## 7. build — 59-68 s (9 s, type `build`)

**Storyboard** : Deux colonnes (SJW, chasseur 1), une ligne par élément. Les éléments non lus en gris.

| t | FR | EN |
| --- | --- | --- |
| 0.3 | Les builds du top 3 ne sont pas encore lus. Voici le seul build relevé, sur une run confirmée plus lente. | The top 3 builds are not read yet. Here is the only build captured, from a slower confirmed run. |

Sources : data/builds/2026-11-12/bot/bot-2026-11-12-Bi5TrN5d1_E-1.json ; noms : data/db/artifact_sets.json, sjw_skills.json, blessings.json

## 8. limites — 68-76 s (8 s, type `points`)

**Storyboard** : 3 lignes avec icône « en attente ».

| t | FR | EN |
| --- | --- | --- |
| 0.3 | Prochaine version : chasseurs identifiés, équipe théorique et gain estimé. | Next version: identified hunters, theoretical team and estimated gain. |

Texte à l'écran :

- Chasseurs non identifiés : la meilleure équipe théorique n'est pas établie. / *Hunters not identified: the best theoretical team is not established.*
- Aucun chrono du top 5 confirmé sur l'écran Results. / *No top 5 time confirmed on the Results screen.*
- Gain de temps possible : non calculé. / *Possible time gain: not calculated.*

## 9. outro — 76-81 s (5 s, type `outro`)

**Storyboard** : Outro 5 s (RESEAUX.md §4) : logo à gauche, 2 emplacements vides à droite pour l'écran de fin YouTube, comptes et site en bas, crédits des joueurs.

Durée totale : 81 s.
