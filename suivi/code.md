# SUIVI — 8 Code — 2026-11-13
## Fait
- `docs/SPEC_ETAPE1.md` : déjà identique à la v2 du projet (rien à recopier).
- `pipeline/scores.py` (+ `tests/test_scores.py`) : milliers (, . espaces), K/M/B/bn/T, 만/억/조, 万/億/亿/兆, chronos BOT, pt ; ignore dates, années, Lv, puissance, portes, 4K/fps, durées hors BOT ; plages de `config`.
- `pipeline/config/etape1.json` : requêtes, mots-clés, plages, quota 6000, créneaux, [À CONFIRMER] listés.
- `semaine.py` (zoneinfo, été/hiver testés), `youtube.py` (playlists, search ≤ 2 pages, videos.list, lives, plafond + réserve 100 u. pour les détails, quotaExceeded), `tri1.py`, `donnees.py`.
- `classement.py` (+ tests) : POC équipe 1 + équipe 2 (jamais 2 runs d'une équipe), GB 2 meilleures, BOT `bot-season`/`bot-challenge`, HOTM `hotm-gate-<n>` (gate entier), égalité, provisoire remplacé, doublons, boss (`_boss.json`), rejets, `channels.json` auto. Idempotent, semaine gelée = rien.
- `etape1.py daily|weekly|classement` : créneau Paris, passage du jour dans `_meta.json`, rapport `_rapport.md`.
- §8 : `analyse_porte_mode.py` lit `hotm-gate-*.json` (gate entier) ; `submode` absent du code et du skill. `.gitignore` (pycache retirés du dépôt).
- `daily.yml` (crons 18:00Z et 19:00Z) et `weekly.yml` (mer. 23:00Z et jeu. 00:00Z) : le créneau Paris et le passage du jour sont vérifiés par `etape1.py` (simulé été/hiver : un seul cron travaille, l'autre sort). Commit `data/` + `git pull --rebase` + push sur `main` ; concurrence partagée ; lancement manuel avec option « force ». **Jamais exécutés sur GitHub.**
## En cours
- rien
## À faire
- Script PC (yt-dlp sous-titres, Whisper, tris 3-4, gel, ouverture de semaine) + Planificateur Windows.
- Tri 2 (miniatures) et OCR des tris 3-4 : [EN ATTENTE] recadrages ; BOT/GB écrans [EN ATTENTE] (vidéo reste en_cours).
## Besoin d'Alexis
- Vérifier le secret `YOUTUBE_API_KEY`, puis lancer `daily.yml` à la main (Actions > Passage quotidien > Run workflow, « force » coché) et lire `data/runs/<semaine>/_rapport.md`.
- Rien d'autre pour ce code. Images de référence OCR toujours attendues.
## Demandes de modif du skill
- Ajouter à §6 du CONTEXTE/skill les fichiers internes créés : `runs/<semaine>/_lectures.json` (scores lus par les tris, entrée du classement) et `_videos.json` (titre, chaîne, miniature).
- À trancher en discussion 1 : BOT variante illisible → `bot-variante-inconnue.json`, HOTM porte illisible → `hotm-gate-inconnue.json` (rank null) ; doublon au HOTM sur score identique risqué (scores ronds) → désactivable via `config.doublon_modes` ; doublon = run retirée, vidéo rejetée seulement si plus aucune run.
