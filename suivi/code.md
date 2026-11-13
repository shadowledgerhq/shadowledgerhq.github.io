# SUIVI — 8 Code — 2026-11-13
## Fait
- Étape 1 codée (scores, semaine, youtube, tri1, classement, etape1 daily/weekly, workflows `daily.yml`/`weekly.yml`) ; premier passage réel OK (clé valide, 1701 u.). Script PC `pipeline/pc.py` + `docs/PC_ALEXIS.md` (non testé sous Windows).
- **v3 codée d'après la liste de la demande** (le document v3 lui-même n'était pas accessible : `docs/SPEC_ETAPE1.md` reste en v2, à remplacer) :
  - tri 1 : premier candidat par source (titre > description > sous-titres) ; `hypothese_mots` exclus ; chapitres de description (≥ 2 lignes `mm:ss`) ignorés ; BOT `\d{1,3}[.;:,]\d{3}` = s.ms, plage 5–180 s ; `semaine_passee_mots` → note « semaine précédente ? » ; mots-clés de mode latins en mot entier.
  - BOT : variante d'après le titre (`bot_variante_mots`) ; HOTM : porte d'après le titre. Fichiers `*-inconnue` gardés.
  - Doublons : `doublon_modes = ["poc"]` ; BOT/HOTM : note « doublon possible », rien retiré ; POC : run en trop retirée, vidéo rejetée seulement sans aucune run.
  - GB : lu, jamais classé (`modes_classement`, plus de `gb.json`). `pc.geler = false` confirmé.
  - `etape1.py relire` : rejoue le tri 1 sur la semaine ; relance auto au prochain `daily` si `tri1_version` change. Semaine 2026-11-12 relue (titres) et reclassée.
- Tests : 35 (scores v3 avec les vrais cas : « Last Week … 133T (Can 150T) », « 19.558 バルカ », « 23;223s », chapitres).
## En cours
- 2 lectures de description (E4lHBPoZeKs « 00:32 », wFFdg1gcZpE « 35 sec ») non relues sans clé : le prochain `daily` (clé présente) les rejoue seul.
## À faire
- Tris 3-4 (OCR) dans `pc.py` puis `pc.geler = true` ; tri 2 (miniatures). [EN ATTENTE] images BOT/GB, recadrages.
## Besoin d'Alexis
- Remettre le document v3 dans le dépôt (`docs/SPEC_ETAPE1.md`) : je ne l'ai pas vu. Installer le PC (docs/PC_ALEXIS.md).
## Demandes de modif du skill
- Format Run : `runs_detail`, `video_ids`, `channel_id` ; fichiers internes `_lectures.json`, `_videos.json`, `processed[v].pc`.
- Listes de départ écrites par Code, à valider par la discussion 1 : `hypothese_mots`, `semaine_passee_mots`, `bot_variante_mots` (challenge prioritaire s'il est seul ; les deux = illisible).
