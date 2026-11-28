# SUIVI — 8 Code — 2026-11-28 (fin session 20, message 15)
## Fait
- Détail archivé : `suivi/archives/code_2026-11-15_a_20.md`, `code_2026-11-22_a_26.md`, `code_2026-11-26_a_27.md` (sessions 17-19 : specs « état actuel » v42, horaires PC 19:30/21:30/23:30, gel 2026-11-19, midi v43, site privé).
- (27/11) `data/runs/index.json` (`donnees.mettre_a_jour_index`) ; Pages coupé (site 404) ; `pipeline/post_x.py` (Réseaux ; pas d'image sans ligne sûre) ; rendu vidéo dans `pipeline/video/` ; rotation : « phases incomplètes ».
- (27/11) Passage GitHub daily avancé à **18:00** (`daily.yml` 16:00Z/17:00Z, créneau 18:00-23:59) : Actions a 45 min de retard. Relance du soir indépendante de celle du weekly ; relance lancée > 2 h après son heure = annulée.
- (27/11) **SPEC_ETAPE2 v8 + v9** (top 10 mixte, classée rang 1-10 garde son build, `config.spec_version`) ; **SPEC_ETAPE1 v43** (texte POC : marque de mode, intervalle, palier + %, borne 0) ; **POC 2026-11-19 corrigé** (`pipeline/corriger_poc_v43.py`, titres seulement). 512 tests OK.
- (27/11 22:30) Anti-bot : sous-titres en 429 (formats OK) ; `tester_ytdlp` teste aussi les sous-titres ; test réel d'Alexis : AUCUN réglage ne passe (défaut, Chrome imité, cookies Firefox : 429 ; Edge : DPAPI ; Brave : absent). Adresse limitée.
## En cours
- (28/11 ~15:00) Passage manuel : 65 min, 13 vidéos traitées (semaine 2026-11-26), 43 `en_cours`, arrêt au 429 de téléchargement (f9amFMYyuZQ) ; relance 15:51. Budget respecté.
- (28/11 14:00) Relances de 12:46, 13:16, 13:46 : toutes « reporté : passage GitHub du jour absent » (le daily GitHub n'a lieu qu'à 18:00) → garde-fou v42 limité à 18:00+ (`pc.lancer`), test `test_relance_de_jour_avant_18h_jamais_reportee`. À vérifier : prochaine relance de jour traite bien des vidéos.
- (28/11) **HOTM arrêté (décision d'Alexis)** : `modes_actifs`/`modes_classement` sans hotm (etape1.json), `youtube.modes_actifs/filtrer_modes_actifs` (requêtes coupées, vidéos HOTM seules rejetées `mode_arrete`), pas d'onglet HOTM dans l'Excel ; UbSotwy18tk rejetée ; Prompt, Classements, Builds, Théorycraft, Réseaux, Site prévenus. Réactivation : « hotm » dans les 2 listes. 527 tests OK.
- (27/11, s.20) **v10 SPEC_ETAPE2 codée** : `equipe.label` sur 5 onglets, `lire_equipe`/`filtrer_par_equipe`/`ecarter_fondus` (composition.py), notes du fournisseur reprises par `builds.calculer` ; `test_etape2_v10.py`. OCR réel de l'équipe à confirmer sur le PC (pas de tesseract ici). Builds prévenu (BOITE §2).
- (27/11, s.20) **pc.py : sous-titres 429 n'arrêtent plus les images** (`st_429`/`img_429`) ; un 429 au téléchargement arrête toujours les images ; `test_soustitres_429_images.py`. 523 tests OK.
- (28/11) Passage manuel 23:20 du 27/11 : premier passage avec le correctif 429 : **5 vidéos traitées** (images continuent), 44 `en_cours` (31 candidates top 10) ; mais durée **666 min** (PC en veille en pleine vidéo, budget 100 min jamais vu) → `pc.empecher_veille()` (Windows, SetThreadExecutionState) ajouté ; actif après `git pull` sur le PC. Passages 21:30 (anti-bot, 0 vidéo) et 23:30 (refusé : verrou, passage manuel en cours).
- Passages PC du 27/11 avant correctif : 0 vidéo traitée, 48 `en_cours`. Bilan v39/v40 (BOITE §1) et 28 rejets « mecharashi » (2026-11-12) : à faire après le prochain passage PC réussi.
- (28/11) v45 POC codée (palier, Goal Progress, Rank Score). Mes messages en attente : Classements (v45 codée, §1) ; Prompt (réponse anti-bot 28/11, BOITE §6) ; Classements (v43 codée, BOITE §1), Builds (v10, BOITE §2), Tâche planifiée (BOITE §7), Réseaux/Theorycraft/Site (§3-5).
## À faire
- Relectures posées jamais faites (`3y8yRhcSq4Y`…), gel de 2026-11-26 le 03/12 01:15 (`pc.geler`), relance PC des builds 2026-11-12 (Alexis), vidéos verticales 608x1080 (accord donné, à régler sur une vraie vidéo).
- `pc.py` (2000+ lignes) : le scinder à la prochaine spec qui le touche.
## Besoin d'Alexis
- Attendre 1 à 2 h puis relancer `outils-pc\5_test_antibot.bat` (Firefox ouvert sur YouTube, connecté), puis `3_passage_complet.bat`.
## Demandes de modif du skill
(aucune)
