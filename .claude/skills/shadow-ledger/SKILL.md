---
name: shadow-ledger
description: Conventions du Projet SLA (Shadow Ledger, Solo Leveling: Arise) : glossaire, formats JSON, SUIVI.md, économie de crédits et checklists. À utiliser dans toute discussion du Projet SLA.
---

# Shadow Ledger — conventions du Projet SLA

Le contexte complet (décisions, étapes, calendrier) est dans `docs/CONTEXTE.md`. Ce skill donne les règles de forme communes à toutes les discussions.

## 1. Glossaire

| Terme | Sens |
| --- | --- |
| POC | Power Of Calamity. Classement : dégâts max ; une run = une équipe, total = équipe 1 + équipe 2. |
| BOT | Battlefield Of Time. Chrono le plus court (secondes). Deux classements : `season` (時の戦場, 49 j, SJW autorisé) et `challenge` (時の戦場チャレンジ, 7 j, chasseurs uniquement). |
| GB | Guild Boss. Classement : Rage Count le plus élevé, somme des 2 runs. Non classé tant que ses écrans ne sont pas définis. |
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

- Arborescence décrite dans `docs/CONTEXTE.md` (section 6).
- Noms de fichiers en minuscules, sans accents ni espaces, mots séparés par `-`.
- Codes de mode dans les fichiers : `poc`, `bot`, `gb`, `hotm`.
- Dates au format AAAA-MM-JJ ; heures en heure de Paris, sauf dans les workflows (UTC).

## 3. Formats JSON

### Run (data/runs/<semaine>/<classement>.json, liste)

Fichiers : `poc.json`, `gb.json`, `bot-season.json`, `bot-challenge.json`, `hotm-gate-<n>.json`.

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
  "score_source": "titre | description | sous-titres | miniature | debut-fin | video-complete",
  "exact": true,
  "confidence": "sur | a_verifier",
  "rank": 1,
  "notes": ""
}
```

Unités : `damage` (POC), `seconds` (BOT), `rage_count` (GB), `points` (HOTM).

- `channel_id` = clé du joueur. `video_id` = vidéo de la meilleure run ; `video_ids` = toutes les vidéos utilisées (les 2 runs POC/GB peuvent venir de 2 vidéos).
- `rank` : seulement pour les lignes `confidence: sur` ; sinon `null`.

Champs supplémentaires :
- `"gate"` (HOTM uniquement) : numéro de la porte, **entier** (`3` pour 제 3관문 / 第3関門).
- `"hunter_mode"` (HOTM uniquement) : `false`, `true` (run sans SJW) ou `null`.
- `"bot_variant"` (BOT uniquement) : `"season"`, `"challenge"` ou `null`.
- `"runs_detail"` : liste d'un objet par run, dans le même ordre que `score.runs`. Champs communs :
  `{"video_id": "", "published_at": "", "t": 0, "stage": "", "team": null, "score_source": "", "exact": true}`
  (`t` = secondes dans la vidéo ; `stage` = libellé du boss ou du stage lu à l'écran ; `team` = POC 1, 2 ou `null`).
  - POC, en plus : `{"sjw": 0, "successor": 0, "hunters": [0, 0, 0]}` ; contrôle : somme = score de la run.
  - HOTM, en plus : `{"clear": 0, "proof_bonus": 0, "proof_level": null}` ; contrôle : clear + proof_bonus = score.
- Score POC et HOTM = « 이번 기록 » de l'écran RESULT, jamais « 기존 기록 » ni l'écran de composition.

### Autres fichiers de l'étape 1 (détail : SPEC_ETAPE1.md §5)

| Fichier | Contenu |
| --- | --- |
| `data/runs/<semaine>/bot-variante-inconnue.json`, `hotm-gate-inconnue.json` | Runs dont la variante BOT ou la porte HOTM est illisible ; `rank: null`, **jamais publiés** |
| `data/runs/<semaine>/_lectures.json` | Toutes les lectures de score des tris ; entrée de `classement.py` |
| `data/runs/<semaine>/_videos.json` | Par vidéo : titre, chaîne, miniature, durée, `mode_guess` |
| `data/runs/<semaine>/_meta.json` | `{week, start_utc, end_utc, frozen, frozen_at}` |
| `data/runs/<semaine>/_boss.json` | Boss / stage de référence déduit (mode, gate, libellé, nombre de vidéos) |
| `data/runs/<semaine>/_rapport.md` | Rapport du dernier passage (quota, vidéos, `a_verifier`, alertes, erreurs) |
| `data/processed.json` | Par video_id : état du traitement ; `pc.sous_titres` = `fait` \| `absent` \| `erreur` |
| `data/channels.json` | `{channel_id, name, uploads_playlist, added_at, source: manuel \| auto}` |

GB : **non classé** tant que ses écrans ne sont pas définis (lectures gardées dans `_lectures.json`, pas de `gb.json`).

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

Champs propres à chaque catégorie : voir `data/db/_schema.md`, qui complète ce format commun.

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
2. Envoyer le prompt de démarrage de la discussion (`docs/PROMPTS_DISCUSSIONS.md`) + le dernier SUIVI.md.
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
- [ ] Le boss / la saison visible correspond à la semaine.
- [ ] Une seule ligne par chaîne (HOTM : par porte ; BOT : par variante) ; pas de ré-upload en double.
- [ ] POC et GB : 2 runs présentes, total = somme (POC : une run par équipe).
- [ ] POC : chaque run = SJW + successeur + 3 chasseurs. HOTM : clear + bonus de preuve = score.
- [ ] BOT trié du plus court au plus long ; les autres du plus haut au plus bas.
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
