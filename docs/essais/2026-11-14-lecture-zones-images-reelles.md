# Lecture des zones GB sur images réelles — 14/11/2026 (discussion Code)

Essai fait avec Tesseract 5.3 et ffmpeg sur les images publiées dans `docs/essais/ocr/` (1080p : `awb-GlVIa7Q_recherche_231_gb_results.jpg` et `…_244_gb_record.jpg` ; 720p : `nh2D7xZ7dOQ_tri3_2_gb_results_partiel.jpg` et `lGDbzyIJcjY_recherche_253.jpg`). Code : `pc.lire_zones_results` puis `ocr_ecrans.lectures_depuis_texte`, `pc.fusionner_ecrans` et `classement.calculer`.

## Vérité terrain (image `awb-GlVIa7Q` à 231 s, 1080p)
Player's Score 795 244 088 074 · Hunter Rank 1 à 6 : 58 388 332 559 253 · 2 330 503 854 251 · 1 290 407 426 593 · 734 202 919 145 · 508 571 686 524 · 251 863 896 022 · Final Score 64 299 126 429 862 · Rage Count 189. Leur somme (Player's Score + 6 Hunter Rank) vaut exactement le Final Score : le contrôle de la spec §3.2 est vérifié sur cette capture.

## Ce que les zones lisent
- **Résultat avant correction** (zones de la v13, un seul prétraitement) : `Rage Count` 183 au lieu de 189 (le « 9 » lu « 3 »), `Final Score` 64 299 126 425 (zone trop étroite à droite), Hunter Rank 1 à 3 tronqués à gauche.
- **Corrections** : zones élargies à toute la case (spec v15), nombres aux groupes de 3 chiffres incomplets rejetés, trois prétraitements (agrandissement ×2 ou ×3, avec ou sans seuil de binarisation) puis vote. Sur 15 lectures de contrôle (Rage Count, Final Score, Player's Score, Total Score, Total Rage Count, RC de groupe, Challenge Count), le vote donne 15 lectures justes ; le meilleur prétraitement seul en donne 12.
- **Hunter Rank** : 4 rangs sur 6 lus justes (2, 4, 5, 6), les rangs 1 et 3 perdent leur premier chiffre (le portrait du chasseur empiète sur le nombre : `58,388,…` lu `98,388,…`, `1,290,…` lu `90,…`). Conséquence : sur cette capture, le contrôle « somme des 6 Hunter Rank = Final Score » échoue, et le contrôle sans les 6 Hunter Rank (rangs lus décroissants) aussi (rang 3 lu 90 milliards, plus petit que le rang 4).
- **Personal Record du salon** (nouvelles zones `config.gb.zones_record`) : `Time Left in Season`, `Total Score`, `Total Rage Count`, `Challenge Count`, RC et dégâts des deux groupes, `No history`. Lus justes sur les deux salons (`awb` 1080p, `nh2D` 720p). Un recoupement s'ajoute : `Total Score` ≈ somme des dégâts affichés des groupes (arrondi ou tronqué), sinon le total est écarté.

## Classement obtenu sur ces images réelles (semaine 2026-11-12)
- `nh2D7xZ7dOQ` (SlayOnLow) : Personal Record 167 + 165 = 332 → **classé 332, rang 1, `sur`**.
- `awb-GlVIa7Q` (Ahmad1195) : Personal Record (groupe 1, RC 189, `Group 2 No history`, dégâts = `Total Score` 64 299 126 429 862 exacts) → **classé 189, `sur`**. Le Results (Hunter Rank 1, 3 erronés) est écarté : le Personal Record contrôlé prime. L'alerte « publiée juste après le reset » est levée (`Time Left in Season` 6j 22h : capture du 12/11, bonne semaine).
- `lGDbzyIJcjY` : classé 19 (essai précédent).

## Limites
- Les rangs 1 et 3 de l'écran Results restent mal lus : la lecture 4/6 est celle d'un seul écran 1080p. À revoir sur d'autres captures ; en attendant, c'est le Personal Record qui fait foi quand il est lu.
- Les coordonnées des zones ont été réglées sur une capture 1080p et une capture 720p du même écran : à confirmer sur d'autres vidéos (spec : [À CONFIRMER] sur 3 autres vidéos).
- Les écrans HUD et Results en portugais et en coréen restent à voir (images de fin de vidéo à publier).

## Écrans Results en portugais et en coréen (images publiées le 14/11, passage v15)
Captures : `T5dR6iJAn-Y_recherche_232.jpg` (portugais, 1080p) et `MJ2iz5TFmvM_recherche_221.jpg` (coréen, 1080p).
- **Portugais** : `Resultado` · boss `Estátua Gigante` · `Pontuação do Jogador` · `Rank do Caçador` · `Novo Recorde Quebrado!` · `Pontuação Final` · `Número de Fúrias` (= Rage Count) · `Tempo de Progresso` (= Play Time) · `Tentar de Novo` · `Sair`. HUD : `Pontos`, `Número de Fúrias do Chefão`, `Equipe A/B`. Valeurs : Player's Score 4 254 332 623 094, Hunter Rank 2 719 877 951 535 · 473 844 449 049 · 199 639 030 058 · 131 808 903 549 · 90 867 324 225 · 36 903 017 574, Final Score 7 907 273 299 084, Rage Count **156** (le titre de la vidéo annonce 159). La somme Player's Score + 6 Hunter Rank = Final Score est exacte.
- **Coréen** : titre `RESULT` (en anglais) · boss `거대 석상` · `플레이어 스코어` · **`계승자 스코어` (ligne Successor Score, valeur 0, absente des écrans anglais vus)** · `헌터 순위` · `신기록 달성!` · `최종 스코어` · `격노 횟수` · `진행 시간` · animation `격노 보상` / `화면을 눌러 계속`. HUD : `POINT`, `보스 격노 횟수`, `A팀`. Valeurs : Player's Score 5 576 463 862 754, Successor Score 0, Hunter Rank 3 686 927 733 236 · 873 686 133 825 · 302 730 549 509 · 125 782 887 452 · 52 090 149 391 · 43 356 454 581, Final Score 10 661 037 770 748, Rage Count 160. **La somme Player's Score + Successor Score + 6 Hunter Rank = Final Score est exacte** : le Successor Score entre dans la somme quand la ligne existe.
- **Mise en page avec Successor Score** : les Hunter Rank 1 à 6 sont décalés vers le bas (y ≈ 0,54 à 0,88 au lieu de 0,40 à 0,74) : `config.gb.zones_successeur`.
- Lecture des zones sur ces deux images (Tesseract 5.3) : Final Score, Rage Count (156 et 160 avec la zone relevée) et 4 à 6 Hunter Rank sur 6 justes ; Player's Score instable (le portrait du joueur empiète sur le nombre).
