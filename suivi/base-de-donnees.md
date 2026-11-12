# SUIVI — 9 Base de données — 2026-11-12
## Fait
- Schémas validés par Alexis ; `data/db/_schema.md`, `stats.json` et `patches.json` (vides) créés.
- Sondage de slagate.com : site SPA, données servies par api.slagate.com. Les routes `/api/codex/*` et `/api/game/hunters` testées renvoient 404 (non exploitables telles quelles).
- Captures BOT lues : `docs/REFERENCE_ECRANS_BOT.md`. Champ `ja` ajouté au schéma.
- Alexis valide : `data/rules/<semaine>.json` créé (BOT 05/11 et 12/11), CONTEXTE §3 et §6 corrigés. Écran de stats lu : `docs/REFERENCE_ECRANS_STATS.md`.
## En cours
- Choix de la méthode de récupération des données (voir « Besoin d'Alexis »).
## À faire
- Saisir `stats`, `patches`, puis `artifact_sets`, `cores`, `hunters`, `weapons`, `shadows`, `successors`, `sjw_skills`, `blessings`.
- Script de contrôle (ids uniques, FR+EN, source, date, icône) à demander à la discussion 8.
## Besoin d'Alexis
- Trace écrite de l'autorisation de Sohoven : son `robots.txt` indique `ai-train=no`. Confirmer que l'autorisation couvre la lecture automatisée de l'API et la reprise des icônes.
- Méthode : (a) Sohoven fournit un export ou les routes à utiliser, (b) saisie à partir des pages publiques /builds, /guides, /tier-list, (c) captures d'écran fournies par toi.
- Captures des 3 autres modes (POC, GB, HOTM) + onglet stats principales des persos.
- Quelles stats sont les « stats principales » à relever dans un build (liste complète de l'écran de stats, lignes sous « 피해량 증가 » comprises) ?
- Règles de POC, GB, HOTM pour les semaines du 05/11 et du 12/11 (à remplir dans `data/rules/`).
## Demandes de modif du skill
- Format « Objet de la base » : ajouter les champs par catégorie (voir `data/db/_schema.md`).
