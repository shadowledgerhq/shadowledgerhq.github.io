# SUIVI — 8 Code — 2026-11-13
## Fait
- Étape 1 codée (scores, semaine, youtube, tri1, classement, etape1 daily/weekly, workflows `daily.yml`/`weekly.yml`) ; premier passage réel OK (clé valide, 1701 u.). Script PC `pipeline/pc.py` + `docs/PC_ALEXIS.md` (non testé sous Windows).
- **v3 codée d'après `docs/SPEC_ETAPE1.md` (v3, lue en entier)** :
  - tri 1 : premier candidat par source, priorité titre > description > sous-titres ; `hypothese_mots` = liste de la spec (can, could, possible, up to, max, ~, 가능, 可能, 目標, target) ; chapitres de description (ligne qui commence par un horodatage ; ≥ 2 horodatages croissants ; au BOT tout `m:ss` sans millièmes) ; BOT `\d{1,3}[.;:,]\d{3}` = s.ms, plage 5–180 s ; « semaine passée » dans le titre seulement → note ; mots-clés latins de mode en mot entier.
  - BOT : variante d'après le titre (`challenge`… / `S\d+-\d`, `season \d+`, `시즌 \d+`, `シーズン\d+`), note « variante d'après le titre ». HOTM : porte d'après le titre seulement. Fichiers `*-inconnue` gardés.
  - Doublons : `doublon_modes = ["poc"]` ; BOT/HOTM : note `doublon possible : <video_id>`, rien retiré ; POC : run en trop retirée, vidéo rejetée seulement sans aucune run.
  - GB lu, jamais classé (pas de `gb.json`). Gel : `pc.geler = false` ; même à true, jamais de gel si toutes les lignes sont provisoires.
  - `etape1.py relire` (rejoue le tri 1 ; relance auto au prochain `daily` si `tri1_version` change). Semaine 2026-11-12 relue (titres) et reclassée.
- Tests : 35 (vrais cas du 1er passage : « Last Week … 133T (Can 150T) », « 19.558 バルカ », « 23;223s », chapitres).
- Non codé (v3) : critère « 5 nombres du détail identiques » du doublon POC (attend l'OCR) ; au gel avec OCR : `pas_de_score`, lignes provisoires archivées « non vérifié ».
## En cours
- 2 lectures de description (E4lHBPoZeKs « 00:32 », wFFdg1gcZpE « 35 sec ») non relues sans clé : le prochain `daily` (clé présente) les rejoue seul.
## À faire
- Tris 3-4 (OCR) dans `pc.py` puis `pc.geler = true` ; tri 2 (miniatures). [EN ATTENTE] images BOT/GB, recadrages.
## Besoin d'Alexis
- Installer le PC (docs/PC_ALEXIS.md).
## Demandes de modif du skill
- Format Run : `runs_detail`, `video_ids`, `channel_id` ; fichiers internes `_lectures.json`, `_videos.json`, `processed[v].pc`.
- `gb` n'est pas dans `mode_keywords` (« GB » = aussi gigaoctet) : à décider par la discussion 1 si le mot court `gb` doit servir d'indice.
