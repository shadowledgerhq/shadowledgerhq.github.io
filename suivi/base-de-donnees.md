# SUIVI — 9 Base de données — 2026-11-13
## Fait
- Schémas validés, `stats.json` (noms coréens), écrans documentés, règles par semaine (`data/rules/`).
- `patches.json` : 7 patchs détaillés (07/05 → 22/10/2026), URL Netmarble + version. Résumés extraits en lecture assistée : à contrôler sur l'URL.
- Versions (Uptodown, Android, rapprochées par date, non confirmées par Netmarble) : 22/10=1.5.15 · 17/09=1.4.55 · 27/08=1.4.46 · 30/07=1.4.35 · 02/07=1.4.26 · 04/06=1.4.16 · 07/05=1.4.08. Plusieurs builds le même jour (1.4.45, 1.4.05/06, 1.4.17 du 10/06, 1.5.16 du 23/10) : on a pris le dernier du jour.
- `artifact_sets.json` : 37 sets (12 complets, 15 armure, 13 bijoux) depuis le wiki Fandom (API MediaWiki, CC BY-SA), via `tools/parse_fandom_artifacts.py`.
- Décision d'Alexis (13/11) : wiki Fandom accepté comme source provisoire des sets (EN, non vérifié en jeu).
- `cores.json` : 18 noyaux (6 Mind, 6 Body, 6 Spirit) du wiki Fandom, via `tools/parse_fandom_cores.py` ; passif EN + 1re valeur par rareté (rare/heroic/legendary). FR, icônes, valeurs de stats par niveau vides. Niveau max 20 selon le wiki, 25 selon Netmarble (17/09).
## En cours
- Rien d'engagé. Reste : contrôle des sets d'artefacts : le wiki date de mai 2026 (modèle du 16/05) ; sets ajoutés depuis et équilibrages du 17/09, 30/07, 22/10 non reflétés.
## À faire
- Compléter/corriger les sets depuis slagate.com (pas de page lisible trouvée : /artefacts, /artifacts = 404 ; piste : API api.slagate.com) ou le jeu.
- FR des sets, emplacements et icônes des pièces, `main_stat_options`, rareté : vides.
- Saisir : hunters → weapons → shadows → successors → sjw_skills → blessings → subjugation_support → proof_modifiers.
- Script de contrôle (ids uniques, FR+EN, source, date, icône) : à demander à la discussion 8.
- Noms FR/EN officiels des stats. Les ids des `changes` de `patches.json` sont des slugs provisoires.
## Besoin d'Alexis
- Captures du GB ; règles POC/GB (05/11, 12/11) et HOTM 05/11 pour `data/rules/`.
- Trace écrite de l'autorisation de Sohoven (`ai-train=no`) : couvre-t-elle lecture automatisée et icônes ?
## Demandes de modif du skill
- rien
