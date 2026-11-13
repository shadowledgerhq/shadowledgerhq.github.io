# SUIVI — 9 Base de données — 2026-11-13
## Fait
- Schémas validés (`data/db/_schema.md`) : catégories hunters, weapons, artifact_sets, cores, shadows, successors, sjw_skills, blessings, subjugation_support (POC), proof_modifiers (HOTM), stats, patches ; champs `ja` et `role` ajoutés.
- `stats.json` : 10 stats + 5 attributs (obligatoires) + puissance de combat (info). Noms coréens lus ; FR/EN vides.
- Écrans lus : stats, BOT, POC, HOTM (avec et sans SJW) → `docs/REFERENCE_ECRANS_*.md`.
- Règles par semaine : `data/rules/2026-11-05.json` (BOT) et `2026-11-12.json` (BOT, HOTM sans restriction). CONTEXTE §3 et §6 corrigés.
- Sondage de slagate.com : SPA, données sur api.slagate.com ; routes `/api/codex/*` testées en 404. Pas d'export de Sohoven possible.
- Décision : le lien porte ↔ mode avec/sans SJW au HOTM sera établi par les données du pipeline (messages donnés pour les discussions 8 et 2).
## En cours
- Rien d'engagé. Prochaine étape : `patches` (notes Netmarble), puis sets d'artefacts.
## À faire
- Saisir : patches → artifact_sets → cores → hunters → weapons → shadows → successors → sjw_skills → blessings → subjugation_support → proof_modifiers.
- Script de contrôle (ids uniques, FR+EN, source, date, icône) : à demander à la discussion 8.
- Noms FR/EN officiels des stats.
## Besoin d'Alexis
- Captures du GB.
- Règles de POC et GB (05/11 et 12/11) et HOTM du 05/11, pour `data/rules/`.
- Trace écrite de l'autorisation de Sohoven (`robots.txt` : `ai-train=no`) : couvre-t-elle la lecture automatisée et les icônes ?
- Source de données pour les sets d'artefacts : captures d'écran ou pages publiques de slagate.com.
## Demandes de modif du skill
- rien (demandes intégrées au skill par 6 — Prompt le 13/11/2026)
