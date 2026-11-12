# SUIVI — 9 Base de données — 2026-11-12
## Fait
- Lecture de CONTEXTE.md, du skill et de CLAUDE.md.
- Schémas par catégorie et ordre de saisie proposés (en attente de validation).
## En cours
- Validation des schémas par Alexis. Aucun fichier `data/db/` créé.
## À faire
- Valider le schéma, puis créer `data/db/_schema.md` + `stats.json` + `patches.json`.
- Lister les catégories et les champs réels sur slagate.com avant la saisie (les champs proposés sont à confirmer).
- Saisir dans l'ordre : stats → patches → sets d'artefacts → noyaux → chasseurs → armes → ombres → successeurs → compétences SJW → bénédictions.
- Script de contrôle (id uniques, FR+EN, source, date, icône) à demander à la discussion 8.
## Besoin d'Alexis
- Valider les choix par défaut : ids en anglais minuscules `a-z0-9-`, icônes PNG 128×128, coréen facultatif.
- Liste des éléments autorisés par mode (utile pour un champ `allowed_modes`).
## Demandes de modif du skill
- Le format « Objet de la base » est générique : ajouter les champs par catégorie (voir `data/db/_schema.md` une fois validé).
