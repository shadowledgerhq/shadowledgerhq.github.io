# SUIVI — 9 Base de données — 2026-11-13
## Fait
- Schémas validés, `stats.json` (noms coréens), écrans documentés, règles par semaine (`data/rules/`).
- `patches.json` : 7 patchs détaillés (07/05 → 22/10/2026), URL Netmarble + version. Résumés extraits en lecture assistée : à contrôler sur l'URL.
- Versions (Uptodown, Android, rapprochées par date, non confirmées par Netmarble) : 22/10=1.5.15 · 17/09=1.4.55 · 27/08=1.4.46 · 30/07=1.4.35 · 02/07=1.4.26 · 04/06=1.4.16 · 07/05=1.4.08. Plusieurs builds le même jour (1.4.45, 1.4.05/06, 1.4.17 du 10/06, 1.5.16 du 23/10) : on a pris le dernier du jour.
- `artifact_sets.json` : 37 sets (12 complets, 15 armure, 13 bijoux) depuis le wiki Fandom (API MediaWiki, CC BY-SA), via `tools/parse_fandom_artifacts.py`.
- Décision d'Alexis (13/11) : wiki Fandom accepté comme source provisoire des sets (EN, non vérifié en jeu).
- `cores.json` : 18 noyaux (6 Mind, 6 Body, 6 Spirit) du wiki Fandom, via `tools/parse_fandom_cores.py` ; passif EN + 1re valeur par rareté (rare/heroic/legendary). FR, icônes, valeurs de stats par niveau vides. Niveau max 20 selon le wiki, 25 selon Netmarble (17/09).
- `hunters.json` : 66 chasseurs (wiki Fandom, `tools/parse_fandom_hunters.py`) : rareté, élément, type, classe, arme exclusive, compétences (EN), passif, avancement A1–A5, stats lv1/max. `successors.json` : 3 successeurs (Myro, Velvet, Monarch of Shadows), même source. Pages de wiki de juin à novembre 2026 : certaines sont antérieures au rééquilibrage du 22/10.
- `weapons.json` : 115 armes (55 de Sung Jin Woo, 60 de chasseurs ; `tools/parse_fandom_weapons.py`) ; 12 sans passif sur le wiki. Armes exclusives liées aux chasseurs par `hunter_id`.
- Décision d'Alexis (13/11) : pas d'appels à l'API interne de slagate (Sohoven refuse). Sources : wiki Fandom + notes Netmarble ; slagate seulement en lecture de pages.
## En cours
- Rien d'engagé. Reste : contrôle des sets d'artefacts : le wiki date de mai 2026 (modèle du 16/05) ; sets ajoutés depuis et équilibrages du 17/09, 30/07, 22/10 non reflétés.
## À faire
- Sets d'artefacts : wiki de mai 2026 ; compléter à partir des notes Netmarble ou du jeu (slagate : pas de page lisible, API exclue).
- FR des sets, emplacements et icônes des pièces, `main_stat_options`, rareté : vides.
- Hunters : 4 sans compétences sur le wiki (Go Gunhee SSR Water, Park Heejin, Song Chiyul, Yoo Jinho) ; 3 sans avancement. Noms FR, icônes, `weapon_type`, valeurs par niveau : vides. `role` (stacker/supporter/buster) rempli pour 23 ; les 43 Striker/Breaker restent `null` (type wiki dans `type_en`).
- Saisir : shadows → sjw_skills → blessings → subjugation_support → proof_modifiers (successors : fait, 3 entrées).
- Script de contrôle (ids uniques, FR+EN, source, date, icône) : à demander à la discussion 8.
- Noms FR/EN officiels des stats. Les ids des `changes` de `patches.json` sont des slugs provisoires.
## Besoin d'Alexis
- Captures du GB ; règles POC/GB (05/11, 12/11) et HOTM 05/11 pour `data/rules/`.
- Trace écrite de l'autorisation de Sohoven (`ai-train=no`) : couvre-t-elle lecture automatisée et icônes ?
## Demandes de modif du skill
- rien
