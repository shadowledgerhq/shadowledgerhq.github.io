# SUIVI — 9 Base de données — 2026-11-13
## Fait
- Schémas validés (`data/db/_schema.md`), `stats.json` (noms coréens), écrans documentés, règles par semaine (`data/rules/`).
- `patches.json` : patch du 22/10/2026 saisi en détail (notes 14/109985 + équilibrage 32/109983) ; 6 patchs précédents (17/09 → 07/05) en liste, `changes` vides.
- Forum Netmarble lisible en scrape avec `waitFor` ; liste des mises à jour : `forum.netmarble.com/slv_en/list/14/1`.
## En cours
- Sets d'artefacts : aucune source lue. Les notes Netmarble ne donnent pas leurs valeurs (ni numéro de version).
## À faire
- Détailler les 6 patchs en liste (au besoin, à la demande).
- Saisir : artifact_sets → cores → hunters → weapons → shadows → successors → sjw_skills → blessings → subjugation_support → proof_modifiers.
- Script de contrôle (ids uniques, FR+EN, source, date, icône) : à demander à la discussion 8.
- Noms FR/EN officiels des stats. Les ids des `changes` sont des slugs provisoires à aligner sur les futures entrées.
## Besoin d'Alexis
- Sets d'artefacts : captures d'écran ou pages publiques de slagate.com (source à choisir).
- Numéro de version du jeu (absent des notes) : le donner ou valider `null`.
- Captures du GB ; règles POC/GB (05/11, 12/11) et HOTM 05/11 pour `data/rules/`.
- Trace écrite de l'autorisation de Sohoven (`ai-train=no`) : couvre-t-elle lecture automatisée et icônes ?
## Demandes de modif du skill
- rien
