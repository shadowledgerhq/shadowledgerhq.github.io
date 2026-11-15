# Schéma de la base de données (data/db/)

Validé par Alexis le 12/11/2026. Un fichier JSON (liste d'objets) par catégorie.
Un champ inconnu reste `null` ou vide : ne jamais inventer une valeur de jeu.

## Socle commun (toutes les catégories)

| Champ | Règle |
| --- | --- |
| `id` | anglais, minuscules, `a-z0-9-`, stable |
| `name` | `{fr, en, ko}` ; `fr` et `en` obligatoires, `ko` facultatif |
| `rarity` | rareté officielle |
| `icon` | `data/icons/<categorie>/<id>.png` (PNG 128×128) |
| `source` | URL de la page d'origine |
| `verified_at` | AAAA-MM-JJ |
| `game_version` | version du jeu au moment de la vérification |
| `notes` | libre |

## Effets

`effects[]` structurés : `{stat, value, unit, target, condition}`.
Texte officiel conservé à côté : `text: {fr, en}`.
Valeur calculée et non lue dans le jeu : `"estimated": true`.

## Champs propres

| Fichier | Champs |
| --- | --- |
| `stats.json` | `kind` (`flat`/`percent`), `scope` |
| `hunters.json` | `role` (stacker/supporter/buster), `element`, `class`, `weapon_type`, `skills[]` (`type`, `effects`, `cooldown`, `values_by_level`), `passives[]`, `base_stats`, `advancement` |
| `weapons.json` | `hunter_id` (ou `null`), `weapon_type`, `element`, `base_stats`, `passive` |
| `artifact_sets.json` | `pieces[]` (slot, nom FR/EN, icône), `bonuses` (paliers 2/4/8), `main_stat_options` |
| `cores.json` | `slot`, `main_stat`, `effects`, `values_by_level` |
| `shadows.json` | `skills[]`, `passives`, `values_by_level` |
| `successors.json` | `skills[]`, `passives` |
| `sjw_skills.json` | `type`, `cooldown`, `effects`, `values_by_level` |
| `blessings.json` | `effects`, `conditions`, `values_by_level` |
| `subjugation_support.json` | `column` (1-3), `effects`, `condition` (rôle requis), `recommended` ; sert au POC |
| `proof_modifiers.json` | `effects`, `max_level`, `cost_per_level`, `boss` (si propre à un boss) ; sert au HOTM (« 단련의 증명 ») |
| `statues.json` | (proposé le 15/11/2026, demande discussion 2) `target` (`hunters` / `sung_jinwoo_successor`), `slots` (3), `grades` (E→S), `option_pool` (9 options), `unique_effect` (texte FR/EN, effet structuré, condition : 3 stats au rang B ou mieux), `values_by_grade` (vide : non relevé). Nom EN officiel Netmarble : « Figure ». |
| `gems.json` | (proposé le 15/11/2026, demande discussion 2) `kind` (`bonus_stat`, plus tard `color`), `color`, `levels`, `effects`, `values_by_level`. Seuls les types de bonus sont relevés (ATK %, DEF %, HP %, pénétration, DCC, précision, MPCR, PM supplémentaires, ATK/DEF/HP supplémentaires) ; couleurs et niveaux : à fournir (captures de l'écran de gemmes). |
| `patches.json` | `version`, `date`, `url` (notes Netmarble), `changes[]` (`category`, `id`, `change`) |

Les champs sont à confirmer sur la source avant la saisie de chaque catégorie.

## Éléments autorisés : par semaine, pas par objet

Les règles changent chaque semaine (ex. semaine du 05/11/2026 : BOT sans Sung Jin Woo, donc sans ses compétences ni bénédictions, mais avec ombres et successeur). Il n'y a donc **pas** de champ `allowed_modes` dans la base.
Proposition : `data/rules/<semaine>.json`, un bloc par mode :
`{"bot": {"sjw": false, "sjw_skills": false, "blessings": false, "shadows": true, "successor": true}}`
avec `source` et `verified_at`. Pour le HOTM, un bloc par sous-mode (`hotm_sjw`, `hotm_hunter`). À valider (voir SUIVI).

## Ordre de saisie

stats → patches → artifact_sets → cores → hunters → weapons → shadows → successors → sjw_skills → blessings → subjugation_support → proof_modifiers.
Les icônes sont ajoutées avec chaque catégorie.


## Noms JA et KO (15/11/2026)
`name.ja` et `name.ko` sont facultatifs ; renseignés seulement quand une source les donne (champ `name_ja_source` / `name_ko_source`). Chasseurs : depuis slagate.com (JA 38/66, KO 60/66, les autres n'étant pas localisés par le site). Armes, ombres, successeurs : aucune source bilingue citable pour l'instant : vides. Runes : JA/KO depuis `GET /api/references`.
