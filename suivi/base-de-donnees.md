# SUIVI — 9 Base de données — 2026-11-12
## Fait
- Schémas validés par Alexis ; `data/db/_schema.md`, `stats.json` et `patches.json` (vides) créés.
- Sondage de slagate.com : site SPA, données servies par api.slagate.com. Les routes `/api/codex/*` et `/api/game/hunters` testées renvoient 404 (non exploitables telles quelles).
## En cours
- Choix de la méthode de récupération des données (voir « Besoin d'Alexis »).
## À faire
- Saisir `stats`, `patches`, puis `artifact_sets`, `cores`, `hunters`, `weapons`, `shadows`, `successors`, `sjw_skills`, `blessings`.
- Script de contrôle (ids uniques, FR+EN, source, date, icône) à demander à la discussion 8.
## Besoin d'Alexis
- Trace écrite de l'autorisation de Sohoven : son `robots.txt` indique `ai-train=no`. Confirmer que l'autorisation couvre la lecture automatisée de l'API et la reprise des icônes.
- Méthode : (a) Sohoven fournit un export ou les routes à utiliser, (b) saisie à partir des pages publiques /builds, /guides, /tier-list, (c) captures d'écran fournies par toi.
- Liste des éléments autorisés par mode (pour `allowed_modes`).
## Demandes de modif du skill
- Format « Objet de la base » : ajouter les champs par catégorie (voir `data/db/_schema.md`).
