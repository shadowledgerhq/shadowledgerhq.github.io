# SUIVI — 8 Code — 2026-11-13
## Fait
- Étape 1 codée (scores, semaine, youtube, tri1, classement, etape1 daily/weekly, workflows `daily.yml`/`weekly.yml`) ; premier passage réel OK (clé valide, 1701 u.). Script PC `pipeline/pc.py` + `docs/PC_ALEXIS.md` (non testé sous Windows).
- **v3 codée d'après `docs/SPEC_ETAPE1.md` (v3, lue en entier)** :
  - tri 1 : premier candidat par source, priorité titre > description > sous-titres ; `hypothese_mots` = liste de la spec (can, could, possible, up to, max, ~, 가능, 可能, 目標, target) ; chapitres de description (ligne qui commence par un horodatage ; ≥ 2 horodatages croissants ; au BOT tout `m:ss` sans millièmes) ; BOT `\d{1,3}[.;:,]\d{3}` = s.ms, plage 5–180 s ; « semaine passée » dans le titre seulement → note ; mots-clés latins de mode en mot entier.
  - BOT : variante d'après le titre (`challenge`… / `S\d+-\d`, `season \d+`, `시즌 \d+`, `シーズン\d+`), note « variante d'après le titre ». HOTM : porte d'après le titre seulement. Fichiers `*-inconnue` gardés.
  - Doublons : `doublon_modes = ["poc"]` ; BOT/HOTM : note `doublon possible : <video_id>`, rien retiré ; POC : run en trop retirée, vidéo rejetée seulement sans aucune run.
  - GB lu, jamais classé (pas de `gb.json`). Gel : `pc.geler = false` ; même à true, jamais de gel si toutes les lignes sont provisoires.
  - `etape1.py relire` (rejoue le tri 1 ; relance auto au prochain `daily` si `tri1_version` change). Semaine 2026-11-12 relue (titres) et reclassée.
- **v4-v6 codée d'après `docs/SPEC_ETAPE1.md` v6** (CONTEXTE, skill et spec déjà remplacés dans `main` par la discussion 6) :
  - GB remis au classement (`modes_classement`, `gb.json`) : RC groupe 1 + groupe 2 (une run par groupe, jamais 2 du même), meilleure run = RC puis dégâts, égalité de RC départagée par la somme des dégâts (`Total Score` exact si les 2 runs viennent du même Personal Record), puis §4.2. `runs_detail[i].damage` (+ `damage_exact`), `team` = groupe.
  - `scores.py` : Rage Count (`165 RC`, `RC 167`, `332RC`, `Rage Count 165`), plage 1–500 ; libellés coréens/japonais dans `rage_count_mots` (vide, [À CONFIRMER]).
  - `gb.py` : rattachement des runs Results au groupe du Personal Record (même RC + dégâts arrondis, ou RC égal + dégâts supérieurs = nouveau record), contrôle `Time Left in Season` (capture = reset − temps restant ; après `published_at` + 60 min de marge → `semaine_precedente`), illisible → a_verifier.
  - `ecrans.py` (OCR [EN ATTENTE], fonctions prêtes) : `lecture_bot` (phases croissantes, dernière phase = chrono, Play Time tronqué, `player_ingame`, variante d'après les armes de SJW, l'écran prime sur le titre), `lecture_gb_results` (Player's Score + 6 Hunter Rank = Final Score), `lectures_gb_record` (Total RC = G1 + G2).
  - `player_ingame` sur les lignes BOT ; « doublon possible » limité à BOT/HOTM. Semaine 2026-11-12 relue : `gb.json` (2 lignes provisoires).
  - Test de l'exemple §4.7 (167 + 165 = 332, puis Results 165 RC / 15 763 121 797 048 : remplace le groupe 2, total 332) : OK. 45 tests.
- **v8 codée** (spec v9 du dépôt la confirme) : `regles` dans chaque lecture, relecture auto des vidéos `en_cours` lues avec une version plus ancienne (`a_relire`, `relire`), indices `season` (`S\d+(-\d+)?`, `season`, `시즌`, `シーズン`), dégâts GB du titre (`damage_exact` false), alerte « publiée juste après le reset » (3 h, sans effet sur le statut).
- **v9 codée (§4.6, `pipeline/bot_saison.py`)** : `S(\d+)-(\d)` en mot entier (semaine 1-7) → champ `bot_season_week` (lecture et ligne BOT). `config.bot.saison_ref` (S20-4 = 2026-11-12, 7 semaines/saison, saisons enchaînées). Semaine attendue → note « semaine confirmée (titre) » et alerte reset levée ; semaine précédente → rejeté `semaine_precedente` (detail `S<n>-<w>`) ; autre écart → `a_verifier` + note, jamais de rejet ; rapport : section « Semaine BOT » (≥ 2 vidéos au même écart = référence à corriger). `tri1_version` = 9. Cas a-923ClD9Rc et Lt84IhMjBvM : S20-4, confirmée. Le numéro de saison n'est jamais lu comme un score (testé). Semaine 2026-11-12 relue (sans clé) et reclassée. 65 tests (`test_bot_saison.py`).
- Acquis v7 : marge `Time Left in Season` par unité (h 60 min, j 24 h, min 1 min), mot-clé `gb` (jamais après un chiffre), `damage_exact` null sans dégâts.
- **Tris 3-4 codés dans `pc.py`** (jamais lancés sur de vraies images : tesseract/yt-dlp absents ici, textes OCR synthétiques tirés de la spec) : `segments_tri` (tri 3 : 10 s + 30 s, 1 img/2 s ; tri 4 : 1 img/10 s), `Outils.telecharger/images/ocr` (yt-dlp 720p → ffmpeg → tesseract eng+kor+jpn, image entière), `ocr_ecrans.py` (détection des écrans BOT, GB Results/Record, HOTM, POC par leurs libellés → valeurs → `ecrans.py`), tri 4 seulement si le tri 3 ne suffit pas (BOT/HOTM 1 lecture sûre ; POC/GB 2), lectures d'écran remplaçant celles du texte, une lecture par écran distinct, idempotent. Au gel (`pc.geler`) : `pas_de_score` + « non vérifié ». `docs/PC_ALEXIS.md` à jour (Tesseract).
- Tests v3 (vrais cas du 1er passage : « Last Week … 133T (Can 150T) », « 19.558 バルカ », « 23;223s », chapitres).
- Non codé (v3) : critère « 5 nombres du détail identiques » du doublon POC (attend l'OCR) ; au gel avec OCR : `pas_de_score`, lignes provisoires archivées « non vérifié ».
## En cours
- 2 lectures de description (E4lHBPoZeKs « 00:32 », wFFdg1gcZpE « 35 sec ») non relues sans clé : le prochain `daily` (clé présente) relit les 39 vidéos de la semaine (1 unité par 50).
## À faire
- Essai réel des tris 3-4 sur le PC, puis recadrages par zone et `pc.geler = true` ; tri 2 (miniatures, daily). Pseudo en jeu et armes de SJW (BOT) : icônes, [EN ATTENTE]. POC : les 5 composants (3 chasseurs) non lus, donc jamais « sûr ».
## Besoin d'Alexis
- Installer le PC (docs/PC_ALEXIS.md, avec Tesseract) et lancer `py -3 pipeline\\pc.py daily --no-git --max 2` ; me coller le début de `_lectures.json` ou une capture mal lue.
## Demandes de modif du skill
- rien
