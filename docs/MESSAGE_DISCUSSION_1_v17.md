Discussion « Étape 1 — Classements ». Ton rôle : définir et contrôler les règles des classements des 4 modes (recherche YouTube, tris 1 à 4, calcul des scores, dédoublonnage, fichiers runs/rejected). Tu ne codes pas : tu rédiges les spécifications pour la discussion Code et tu vérifies les classements produits.

Demande (de la discussion Code, v17 codée, dernier état dans suivi/code.md et docs/essais/2026-11-14-*.md) : valide ou corrige les points suivants, puis donne la spec v17.

1. Libellés PT/KO : confirme les libellés de `config.gb.libelles.pt|ko` (Results : Pontuacao do Jogador / Pontuacao Final / 플레이어 스코어 / 계승자 스코어 / 헌터 순위, y compris les formes espacées `진 행 시간`) et la ligne `Successor Score` (coréen) : Player's Score + Successor + 6 Hunter Rank = Final Score (vérifié sur 10 661 037 770 748).
2. Fiabilité du Player's Score : lu par zone, il est souvent en conflit entre images (nh2D, MJ2iz5TFmvM). v17 : si les 6 Hunter Rank sont lus mais que la somme est fausse, ou si le Player's Score est illisible, repli sur le contrôle « sans Hunter Rank » (RC identique sur ≥ 2 images, Final Score confirmé par le HUD [Points ; ×1,02] ou 2 images, rangs décroissants). Player's Score illisible n'est toléré que si le HUD confirme le Final Score. D'accord ?
3. Total Score de nh2D mal lu : le Total Score du Personal Record ne concorde pas avec les dégâts des groupes ; conserve-t-on « Total Score = Final Score, a_verifier si incohérent » ?
4. RaidenShadow et Eden : lignes en `a_verifier` (somme des groupes ≠ Total, Points HUD 10 375 790 058 jamais un score). Faut-il les laisser ainsi jusqu'à relecture manuelle ?
5. RC 156 contre 159 dans le titre : le RC lu à l'écran (156, 3 images) prime sur le titre (159) ? Confirme la règle et la note à afficher.
6. Points HUD KO/PT (v17) : rejetés s'ils sont hors [1e9 ; 1e14] ou sans groupes de 3 chiffres (`gb.hud_points_groupes` = ko, pt). Valide ces seuils.
7. Décision sur `pc.geler` : reste `false` ? Critères pour passer à `true` (nombre de vidéos relues sans erreur, 1080p confirmé sur combien de vidéos) ?

Résultats à venir : Alexis relance les 6 vidéos (awb-GlVIa7Q, nh2D7xZ7dOQ, T5dR6iJAn-Y, Oj_-5x6700s, vYtRCpFtSOk, MJ2iz5TFmvM) avec le code v17 ; il te colle le bilan `docs/essais/ocr/_resume_6videos.json`.
