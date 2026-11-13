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
| `patches.json` | `version`, `date`, `url` (notes Netmarble), `changes[]` (`category`, `id`, `change`) |

Les champs sont à confirmer sur la source avant la saisie de chaque catégorie.

## Éléments autorisés : par semaine, pas par objet

Les règles changent chaque semaine (ex. semaine du 05/11/2026 : BOT sans Sung Jin Woo, donc sans ses compétences ni bénédictions, mais avec ombres et successeur). Il n'y a donc **pas** de champ `allowed_modes` dans la base.
Proposition : `data/rules/<semaine>.json`, un bloc par mode :
`{"bot": {"sjw": false, "sjw_skills": false, "blessings": false, "shadows": true, "successor": true}}`
avec `source` et `verified_at`. À valider (voir SUIVI).

## Ordre de saisie

stats → patches → artifact_sets → cores → hunters → weapons → shadows → successors → sjw_skills → blessings → subjugation_support.
Les icônes sont ajoutées avec chaque catégorie.
