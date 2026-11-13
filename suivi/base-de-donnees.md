# SUIVI — 9 Base de données — 2026-11-13
## Fait
- Schémas, `stats.json` (noms coréens), écrans documentés, règles par semaine (`data/rules/`).
- Les 12 catégories de `data/db/` existent. Sources : wiki Fandom (EN, CC BY-SA, non vérifié en jeu, scripts `tools/parse_fandom_*.py`), notes Netmarble, captures d'Alexis, slagate (voir décisions).
- `patches.json` : 7 patchs (07/05→22/10) avec URL Netmarble ; versions Uptodown 1.4.08…1.5.15 rapprochées par date (non confirmées). Résumés en lecture assistée, à contrôler.
- Effectifs : hunters 66, weapons 115, artifact_sets 40 (+pièces), cores 18, shadows 15, successors 3, sjw_skills 12+89 runes, blessings 59, subjugation_support 18, proof_modifiers 17.
- Noms FR/KO/JA et icônes depuis slagate (`apply_fr_names*.py`, `fetch_icons.py`) : hunters 66/66, noyaux 18/18, ombres 15/15, runes 77, pierres 59/59, sets 32/40 (+172 pièces), armes de SJW 29/115. 436 PNG 128×128 (`data/icons/`, crédits dans `CREDITS.md`).
- Décisions d'Alexis (13/11) : wiki Fandom accepté ; lecture de pages et routes GET publiques de slagate OK (pas `/api/query`, pas d'images en masse sauf icônes autorisées) ; icônes autorisées.
- Soutien de subjugation : semaine 12/11 (capture) ; preuves HOTM : semaine 05/11 seulement.
- `docs/REFERENCE_ECRANS_BOT.md` : section « Écran de résultat (client anglais, capture du 13/11/2026) » ajoutée (phases cumulées, score = chrono de la dernière phase).
- Recoupement avec le patch du 22/10 (`tools/crosscheck_patches.py`, champs `patch_adjustments`) : 8 chasseurs et 2 armes exclusives déjà à jour sur le wiki (pages ≥ 22/10) ; 4 chasseurs (portée de burst) non vérifiables ; 9 chefs d'ombre : valeurs du wiki = avant patch, valeurs après patch ajoutées (rang General ; Iron/Tank = effet en plus). Plafonds de niveau ajoutés : noyaux 25, armes 130, ombres 195. Pierres : 7 valeurs du wiki ≠ texte FR de l'API (Lightning Speed, Intuit, Irresistible Force, Sandbag, Double-edged Sword, Chains of Blood, Irreversible Road) : wiki périmé, cohérent avec les buffs de juin.
## En cours
- Rien d'engagé.
## À faire
- Valeurs de sets d'artefacts : rééquilibrés 4 fois (04/06→22/10) sans valeurs publiées : texte du wiki (mai) possiblement périmé, à vérifier en jeu. Chasseurs rééquilibrés en juin/juillet/août non recoupés (patchs peu détaillés).
- 7 pierres du 17/09 + 29 runes récentes : effets/valeurs à saisir (captures du jeu).
- 6 rapprochements wiki↔slagate de chasseurs à confirmer : Jerim Yung, Baek Beast, Sian Halat (Igris), Holy Go Gun Hee, Lim Taegyu, Esil Radir. 6 pierres sans nom EN officiel.
- 4 chasseurs sans compétences sur le wiki (Go Gunhee, Park Heejin, Song Chiyul, Yoo Jinho) ; 43 Striker/Breaker sans `role` (type dans `type_en`).
- Vides : `main_stat_options` des sets, `weapon_type` des chasseurs, valeurs par niveau, stats FR/EN, 86 armes de SJW sans FR/icône, 8 sets d'événement.
- Script de contrôle (ids uniques, FR+EN, source, date, icône) : à demander à la discussion 8.
## Besoin d'Alexis
- Une capture par semaine du soutien de subjugation et des preuves HOTM (pas de preuves 12/11 : Alexis n'en a pas).
- Captures du GB ; règles POC/GB (05/11, 12/11) et HOTM 05/11 pour `data/rules/`.
## Demandes de modif du skill
- rien
