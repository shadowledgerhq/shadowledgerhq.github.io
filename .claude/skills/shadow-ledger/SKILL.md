---
name: "shadow-ledger"
description: "Conventions du Projet SLA (Shadow Ledger, Solo Leveling: Arise) : glossaire, formats JSON, SUIVI.md, économie de crédits et checklists. À utiliser dans toute discussion du Projet SLA."
---

# Shadow Ledger — conventions du Projet SLA

Le contexte complet (décisions, étapes, calendrier) est dans le document CONTEXTE.md du projet (copie dans `docs/CONTEXTE.md` du dépôt). Ce skill donne les règles de forme communes à toutes les discussions.

## 1. Glossaire

| Terme | Sens |
| --- | --- |
| POC | Power Of Calamity. Classement : dégâts max ; une run = une équipe, total = équipe 1 + équipe 2. |
| BOT | Battlefield Of Time. Chrono le plus court (secondes) = dernière phase de l'écran `Results`. **Un seul classement** par semaine (Challenge retiré du jeu en mai 2026). Saison = 4 semaines de jeu (1 boss/semaine) + 1 semaine de calcul sans classement ; semaine de saison notée `S<n>-<w>`. |
| GB | Guild Boss. Classement : Rage Count le plus élevé ; une run = un groupe (6 chasseurs + SJW), total = groupe 1 + groupe 2 ; égalité départagée par la somme des dégâts. Écran `Personal Record` accepté comme source. |
| HOTM | Hall Of The Monarchs. Un classement **par porte** (제 n관문 / 第n関門) : points les plus élevés. 1 run par porte. |
| RC | Rage Count, unité de score du GB. |
| SJW | Sung Jin Woo. |
| Joueur | Une chaîne YouTube, identifiée par `channel_id`. |
| Reset | Jeudi 01h00, heure de Paris, pour les 4 modes. |
| Semaine | Identifiée par la date du jeudi où elle commence : AAAA-MM-JJ. |
| Tri 1 à 4 | 1 titre/description/sous-titres · 2 miniature · 3 début (10 s) et fin (30 s), 1 img/2 s · 4 vidéo entière, 1 img/10 s. |
| Top 10 | Les 10 premiers de chaque mode, seuls analysés à l'étape 2. |

## 2. Fichiers et dossiers

- Les documents du dépôt (`docs/`, `data/`, `suivi/`) ne ressortent pas dans la recherche du Projet SLA : dans une discussion claude.ai, les lire en clonant le dépôt public `https://github.com/shadowledgerhq/shadowledgerhq.github.io` (ou via la source GitHub synchronisée du projet).
- Arborescence décrite dans CONTEXTE.md (section 6). Spécification détaillée de l'étape 1 : SPEC_ETAPE1.md (projet et `docs/` du dépôt).
- Toute spécification est poussée dans `docs/` du dépôt **avant** d'être envoyée à la discussion Code. Code pousse toujours sur une branche `claude/…` (fusion automatique dans `main`).
- Noms de fichiers en minuscules, sans accents ni espaces, mots séparés par `-`.
- Codes de mode dans les fichiers : `poc`, `bot`, `gb`, `hotm`.
- Dates au format AAAA-MM-JJ ; heures en heure de Paris, sauf dans les workflows (UTC).

## 3. Formats JSON

### Run (data/runs/<semaine>/<classement>.json, liste)

Fichiers : `poc.json`, `gb.json`, `bot.json`, `hotm-gate-<n>.json`.

```json
{
  "run_id": "poc-2026-11-12-dQw4w9WgXcQ",
  "week": "2026-11-12",
  "mode": "poc",
  "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
  "player": "nom de la chaîne",
  "channel": "nom de la chaîne",
  "video_id": "dQw4w9WgXcQ",
  "video_ids": ["dQw4w9WgXcQ"],
  "published_at": "2026-11-13T18:02:00+01:00",
  "lang": "ko",
  "score": {"total": 4268000000, "runs": [2134000000, 2134000000], "unit": "damage"},
  "score_source": "titre | description | sous-titres | miniature | debut-fin | video-complete | record",
  "exact": true,
  "confidence": "sur | a_verifier",
  "rank": 1,
  "notes": ""
}
```

Unités : `damage` (POC), `seconds` (BOT), `rage_count` (GB), `points` (HOTM).

- `channel_id` = clé du joueur. `video_id` = vidéo de la meilleure run ; `video_ids` = toutes les vidéos utilisées (les 2 runs POC/GB peuvent venir de 2 vidéos).
- `rank` : seulement pour les lignes `confidence: sur` ; sinon `null`.
- `score_source: record` = écran `Personal Record` du GB (seul cas où un écran autre que RESULT donne un score sûr).

Champs supplémentaires :
- `"gate"` (HOTM uniquement) : numéro de la porte, **entier** (`3` pour 제 3관문 / 第3関門).
- `"hunter_mode"` (HOTM uniquement) : `false`, `true` (run sans SJW) ou `null`.
- `"bot_season_week"` (BOT uniquement) : semaine de saison lue dans le titre (`"S20-4"`) ou `null`.
- `"player_ingame"` (BOT uniquement) : pseudo en jeu lu dans le bandeau du bas, à titre d'information.
- `"runs_detail"` : liste d'un objet par run, dans le même ordre que `score.runs`. Champs communs :
  `{"video_id": "", "published_at": "", "t": 0, "stage": "", "team": null, "score_source": "", "exact": true}`
  (`t` = secondes dans la vidéo ; `stage` = libellé du boss ou du stage lu à l'écran ; `team` = POC : équipe 1, 2 ou `null` ; GB : groupe 1, 2 ou `null`).
  - POC, en plus : `{"sjw": 0, "successor": 0, "hunters": [0, 0, 0]}` ; contrôle : somme = score de la run.
  - HOTM, en plus : `{"clear": 0, "proof_bonus": 0, "proof_level": null}` ; contrôle : clear + proof_bonus = score.
  - GB, en plus : `{"damage": 0, "damage_exact": true}` (`damage` = `Final Score` ; `damage_exact` = `false` si arrondi — `Personal Record` 17.28T ou titre — et `null` si aucun dégât lu ; `team` = groupe) ; contrôle Results : `Player's Score` + 6 `Hunter Rank` = `Final Score` ; contrôle Personal Record : `Total Rage Count` = RC groupe 1 + RC groupe 2.
- Score POC et HOTM = « 이번 기록 » de l'écran RESULT, jamais « 기존 기록 » ni l'écran de composition. Jamais le score de l'écran de composition, quel que soit le mode.

### Autres fichiers de l'étape 1 (détail : SPEC_ETAPE1.md §5)

| Fichier | Contenu |
| --- | --- |
| `data/runs/<semaine>/hotm-gate-inconnue.json` | Runs dont la porte HOTM est illisible ; `rank: null`, **jamais publié** |
| `data/runs/<semaine>/_lectures.json` | Toutes les lectures de score des tris, chacune avec `regles` (version des règles du tri 1 ; une lecture plus ancienne est refaite) ; entrée de `classement.py` |
| `data/runs/<semaine>/_videos.json` | Par vidéo : titre, chaîne, miniature, durée, `mode_guess` |
| `data/runs/<semaine>/_meta.json` | `{week, start_utc, end_utc, frozen, frozen_at}` |
| `data/runs/<semaine>/_boss.json` | Boss / stage de référence déduit (mode, gate, libellé, nombre de vidéos) |
| `data/runs/<semaine>/_rapport.md` | Rapport du dernier passage (quota, vidéos, `a_verifier`, alertes, erreurs) |
| `data/processed.json` | Par video_id : état du traitement ; `pc.sous_titres` = `fait` \| `absent` \| `erreur` |
| `data/channels.json` | `{channel_id, name, uploads_playlist, added_at, source: manuel \| auto}` |

### Build (data/builds/<semaine>/<mode>/<run_id>-<n>.json)

```json
{
  "run_id": "poc-2026-11-12-dQw4w9WgXcQ",
  "run_index": 1,
  "status": "build_complet | build_partiel | pas_de_build",
  "hunters": [{"id": "", "weapon": "", "artifact_sets": [], "cores": [], "stats": {}}],
  "shadows": [],
  "successor": null,
  "sjw": {"skills": [], "blessings": []},
  "found": {"hunters": true, "shadows": false},
  "found_at": {"hunters": "tri-3"},
  "sources": []
}
```

Les identifiants (`id`, `weapon`…) sont ceux de la base de données. Stats : principales uniquement.

`sjw.skills` = liste de 6 objets `{"slot": "", "id": "", "level": null}` (`level` peut rester `null`), slots : `skill_1`, `skill_2`, `ultimate`, `qte_1`, `qte_2`, `qte_3`.

### Objet de la base (data/db/<categorie>.json, liste)

```json
{
  "id": "identifiant-stable",
  "name": {"fr": "", "en": "", "ko": ""},
  "rarity": "",
  "effects": [],
  "conditions": [],
  "values_by_level": {},
  "icon": "data/icons/<categorie>/<id>.png",
  "source": "url",
  "verified_at": "AAAA-MM-JJ",
  "game_version": ""
}
```

Un champ inconnu reste vide : ne jamais inventer une valeur de jeu.

Champs propres à chaque catégorie : voir `data/db/_schema.md` dans le dépôt, qui complète ce format commun.

## 4. SUIVI.md

Chaque réponse de travail se termine par le suivi de la discussion, 30 lignes maximum, enregistré dans `suivi/<discussion>.md` :

```
# SUIVI — <discussion> — AAAA-MM-JJ
## Fait
- ...
## En cours
- ...
## À faire
- ...
## Besoin d'Alexis
- ...
## Demandes de modif du skill
- (vide si rien)
```

Une section vide s'écrit `- rien`. Ne pas recopier l'historique : seulement l'état actuel.

## 5. Reprise d'une discussion

1. Ouvrir une discussion neuve quand l'actuelle devient longue.
2. Envoyer le prompt de démarrage de la discussion (PROMPTS_DISCUSSIONS.md) + le dernier SUIVI.md.
3. Reprendre à « En cours », sans refaire « Fait ».

## 6. Économie de crédits

- Réponses courtes. Pas de reformulation de la demande, pas de résumé de ce qui vient d'être fait.
- Pas de recherche web si l'information est dans le projet, le dépôt ou la base.
- Lire seulement les fichiers et la partie de la base utiles à la tâche.
- Ce qui se répète se code (Python, GitHub Actions) au lieu d'être fait à la main par Claude.
- Une question à Alexis seulement si la réponse change ce qu'on fait.

## 7. Checklists de contrôle

### Classements (étape 1)
- [ ] Toutes les vidéos ont une date de publication postérieure au dernier reset.
- [ ] Le boss / la saison visible correspond à la semaine (GB `Personal Record` : `Time Left in Season` cohérent avec la date de publication ; BOT : `S<n>-<w>` du titre = semaine attendue, aucune run classée en semaine de calcul).
- [ ] Une seule ligne par chaîne (HOTM : par porte) ; pas de ré-upload en double.
- [ ] POC et GB : 2 runs présentes, total = somme (POC : une run par équipe ; GB : une run par groupe).
- [ ] POC : chaque run = SJW + successeur + 3 chasseurs. HOTM : clear + bonus de preuve = score.
- [ ] BOT : phases croissantes, dernière phase = chrono du bandeau = `Play Time`. GB : `Player's Score` + 6 `Hunter Rank` = `Final Score` ; `Total Rage Count` = groupe 1 + groupe 2.
- [ ] BOT trié du plus court au plus long ; les autres du plus haut au plus bas (GB : égalité de RC départagée par les dégâts).
- [ ] Les scores `exact: false` ou `a_verifier` sont signalés.
- [ ] Aucun écart improbable (ex. score 10 fois au-dessus du 2e) sans vérification.

### Builds (étape 2)
- [ ] 10 builds par mode (×2 runs pour POC et GB) ou raison de l'absence.
- [ ] Chaque identifiant existe dans la base de données.
- [ ] Statut cohérent avec le champ `found`.
- [ ] Éléments interdits dans le mode absents.
- [ ] Un PowerPoint par vidéo du top 10.

### Base de données (étape 3a)
- [ ] Nom FR et EN renseignés.
- [ ] Source et date de vérification présentes.
- [ ] Icône présente pour chaque objet.
- [ ] Version du jeu à jour après chaque patch.

### Vidéos (étape 3b)
- [ ] Chaque choix justifié ; les estimations signalées comme telles.
- [ ] Script FR et EN de même contenu.
- [ ] Intro et outro de 5 s max.
- [ ] Contenu différent des vidéos des semaines précédentes.

### Site (étape 5)
- [ ] Classement de la semaine en ligne après chaque passage.
- [ ] Liens vers les vidéos sources et crédits des joueurs.
- [ ] Pages FR et EN identiques.
- [ ] Liens réseaux sur chaque page.
