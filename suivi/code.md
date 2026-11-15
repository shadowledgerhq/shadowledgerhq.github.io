# SUIVI — 8 Code — 2026-11-15
## Fait (sessions 4 à 7, 15/11)
- Images de composition : affinage 0,5 s puis 0,1 s par onglet (`composition._affiner`, `_affiner_onglet`), choix des plus stables (`choisir_stables`). Essai 5MI-RLj7FSk : images nettes, plateau trouvé. Détail : `git log -p suivi/code.md`.
- Verrou `logs/pc.lock` (un seul passage PC), rapport « Durée du passage », correctifs JSON abîmé / rebase (`donnees.lire_json`, écriture atomique, `Git.verifier_json`, `pipeline/verifier_json.py`, `pipeline/fusion_locale.py`). Incident du 15/11 résolu sans perte.
- Anti-bot YouTube levé : profil Chrome secondaire « Profile 1 » + Deno, réglage `pipeline/config/pc_local.json` (ignoré par git, `pc.py ytdlp-profil`). Jamais le profil « Default ».
- **Masques d'artefacts recalés (session 7)** : cause du 9/24 = masque mal placé (« +20 » est en bas-droite de l'icône, pas en haut ; bandeau `Lv.120` dès y 0,7, pas 0,62). `masques.artifact_pieces` = `[[0,0.7,1,1],[0.6,0.2,1,1]]`. Mesuré sur l'image 5MI (BOT) : SJW (Poison bleu du Concepteur, vérifié à l'œil) 5/8 → 7/8 (collier = chaîne fine, 0,54, reste non reconnu) ; sur v0tuXJNxudk (POC, autre image) : SJW 8/8 set « burning » (curse/greed/blessing voisins : [À VÉRIFIER] à l'œil), hunters cohérents. Scores 0,6–0,9 contre 0,45–0,75. Test `test_masques_artefacts.py` (2 vraies captures). Résidu : faux positifs possibles sur sets 4 pièces (ex. `beast-set` 0,55–0,66 sur la bague) → `seuil_sur` 0,65 les marque « a_verifier ».
- Bénédictions/noyaux : absents des images de 5MI (BOT, fenêtre `t_composition` [2, 8] s : le joueur n'ouvre pas ces onglets) ; **présents** dans v0tuXJNxudk (POC : `_compo_benedictions_0`, `_compo_noyaux_0`) et zones POC déjà calées. Pas de défaut de code constaté.
- Tests : 191 OK, 2 échecs déjà présents avant (`test_etape2_v4::test_18…`, `test_scores::test_v22_rage_dans_les_titres_gb`) : non traités ici.
## En cours
- Subjugation POC : écran codé, jamais lu par le vrai OCR (v0tuXJNxudk à relancer avec `--garder-ocr` pour caler `ecrans.subjugation.cartes`).
- Reconnaissance d'artefacts : essayer d'autres vidéos BOT/POC avec les nouveaux masques ; collier (chaîne fine) et faux positifs 4 pièces à surveiller ; piste : préférence pour le set dominant du personnage.
- Reste de l'ancien « En cours » : voir l'historique git (`git log -p suivi/code.md`).
## À faire
- Relance des 6 vidéos par Alexis (v17), puis bilan à la discussion 1.
- Essai réel des tris 3-4 sur le PC, puis recadrages par zone et `pc.geler = true` ; tri 2 (miniatures, daily). Pseudo en jeu et armes de SJW (BOT) : icônes, [EN ATTENTE]. POC : les 5 composants (3 chasseurs) non lus, donc jamais « sûr ».
## Besoin d'Alexis
- `git pull origin main`, puis (un seul passage à la fois) : `py -3 pipeline\pc.py builds --video 5MI-RLj7FSk --mode bot --garder-ocr` ; renvoyer le rapport (artefacts attendus nettement au-dessus de 9/24). Ensuite `py -3 pipeline\pc.py builds --video v0tuXJNxudk --mode poc --garder-ocr`.
- Relancer les 6 vidéos (v17), coller `docs/essais/ocr/_resume_6videos.json` à la discussion 1 avec `docs/MESSAGE_DISCUSSION_1_v17.md`.
## Demandes de modif du skill
- `.claude/skills/shadow-ledger/SKILL.md` et `docs/CONTEXTE.md` décrivent encore BOT « deux classements » (`bot-season`/`bot-challenge`, `bot-variante-inconnue`) : à aligner sur la v10 (discussion 1).
