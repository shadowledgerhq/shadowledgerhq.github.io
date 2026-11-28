---
name: "shadow-ledger"
description: "Conventions du Projet SLA (Shadow Ledger, Solo Leveling: Arise) : glossaire, formats JSON (runs, builds, rotations, base), SUIVI.md, règles de discussion et checklists de contrôle."
---

# Shadow Ledger — conventions du Projet SLA

Le contexte complet (décisions, étapes, calendrier) est dans le document CONTEXTE.md du projet (copie dans `docs/CONTEXTE.md` du dépôt). Ce skill donne les règles de forme communes à toutes les discussions.

## 1. Glossaire

| Terme | Sens |
| --- | --- |
| POC | Power Of Calamity. Depuis la refonte du 19/11/2026 : paliers, Rank Score = 1 000 000 × (palier − 1 + progression), les 2 équipes partagent les PV du boss (le score cumule les deux) ; ordre (28/11/2026) : palier, puis Goal Progress, puis Rank Score, égalité sur les trois = ex aequo ; score d'une équipe = son Total Contribution (jamais un critère) ; plus d'élément imposé (SPEC_ETAPE1 §9). Avant : dégâts max, une run = une équipe, total = équipe 1 + équipe 2. |
| BOT | Battlefield Of Time. Chrono le plus court (secondes) = dernière phase de l'écran `Results`. **Un seul classement** par semaine (Challenge retiré du jeu en mai 2026). Saison = 4 semaines de jeu (1 boss/semaine) + 1 semaine de calcul sans classement ; semaine de saison notée `S<n>-<w>`. |
| GB | Guild Boss. Classement : Rage Count le plus élevé ; **seules les runs filmées (écran Results) comptent** ; une run = un groupe (6 chasseurs + SJW), total = meilleure run filmée de chaque groupe ; égalité départagée par la somme des dégâts. Le `Personal Record` sert seulement à identifier le groupe. |
| HOTM | Hall Of The Monarchs. **Arrêté définitivement le 28/11/2026** (décision d'Alexis) : plus de classement, builds, vidéo, page ni post ; vidéo HOTM → `rejected` (`mode_arrete`). Données de 2026-11-12 gardées en archive. |
| RC | Rage Count, unité de score du GB. |
| SJW | Sung Jin Woo. |
| Joueur | Une chaîne YouTube, identifiée par `channel_id`. |
| Reset | Jeudi 01h00, heure de Paris, pour les modes suivis (POC, BOT, GB). |
| Semaine | Identifiée par la date du jeudi où elle commence : AAAA-MM-JJ. |
| Tri 1 à 4 | 1 titre/description/sous-titres · 2 miniature · 3 début (10 s) et fin (30 s), 1 img/2 s · 4 vidéo entière, 1 img/10 s. |
| Top 10 | Les 10 premiers de chaque mode, seuls analysés à l'étape 2. |

## 2. Fichiers et dossiers

- Les documents du dépôt (`docs/`, `data/`, `suivi/`) ne ressortent pas dans la recherche du Projet SLA : dans une discussion claude.ai, les lire en clonant le dépôt public `https://github.com/shadowledgerhq/shadowledgerhq.github.io` (ou via la source GitHub synchronisée du projet).
- Arborescence décrite dans CONTEXTE.md (section 6). Spécifications détaillées : `docs/SPEC_ETAPE1.md`, `docs/SPEC_ETAPE2.md`, `docs/SPEC_ROTATION.md` du dépôt (seules à faire foi ; plus de copie dans le Projet). Chaque spec = état actuel court ; l'historique des versions est dans `docs/archives/`, à ne lire qu'en cas de besoin.
- Toute spécification est poussée dans `docs/` du dépôt **avant** d'être envoyée à la discussion Code. Chaque discussion (1 à 9) pousse elle-même, **seulement dans sa zone** (CONTEXTE §7, « Droit de pousser »), sur une branche `claude/<discussion>-<sujet>` (fusion automatique dans `main`) ; accès par `add_repo` (push) ; hors de sa zone, message au propriétaire.
- Messages entre discussions : vers 1 à 7 → `claude/BOITE.md` du Projet ; vers 8 et 9 → `docs/BOITE.md` §8 ou §9 du dépôt ; depuis 8 et 9 → `docs/BOITE.md`, section du destinataire. **Chaque** message posé est annoncé à Alexis dans la même réponse, sans exception, mais **jamais recopié** : une seule ligne « Message de <X> pour <Y> dans <boîte> ». Commande « message ? » d'Alexis : relire les deux boîtes, traiter ce qui est adressé à la discussion, puis lister ses messages envoyés (destinataire, date, sujet en quelques mots, « en attente » ou « traité ») ; rien → « Aucun message » (exception : session sans accès au dépôt → message prêt à coller pour 8 ou 9). Message traité : retiré de `claude/BOITE.md` (la décision est dans la SPEC, CONTEXTE ou le SUIVI du destinataire) ; dans `docs/BOITE.md`, archivé par Code dans `docs/archives/`.
- Aucun relevé manuel : scores, builds, éléments autorisés et rotations sont relevés par le pipeline ; ne jamais écrire « à relever à la main ».
- Noms de fichiers en minuscules, sans accents ni espaces, mots séparés par `-`.
- Codes de mode dans les fichiers : `poc`, `bot`, `gb`.
- Dates au format AAAA-MM-JJ ; heures en heure de Paris, sauf dans les workflows (UTC).

## 3. Formats JSON

### Run (data/runs/<semaine>/<classement>.json, liste)

Fichiers : `poc.json`, `gb.json`, `bot.json`.

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

Unités : `rank_score` (POC depuis le 19/11/2026 ; `damage` avant), `seconds` (BOT), `rage_count` (GB).

- `channel_id` = clé du joueur. `video_id` = vidéo de la meilleure run ; `video_ids` = toutes les vidéos utilisées (les 2 runs POC/GB peuvent venir de 2 vidéos).
- `rank` : seulement pour les lignes `confidence: sur` ; sinon `null`. POC et GB : une seule run `sur` suffit pour être classé (note `une seule run`) ; la 2e run, trouvée plus tard, complète le total.
- Notes normalisées (champ `notes`) : `une seule run`, `compteur animé` (valeurs croissantes d'une animation, seule la finale compte).
- Seul l'écran RESULT donne un score sûr, **sans exception** (GB : le `Personal Record` identifie le groupe, il ne classe jamais une run non filmée). Détail : `docs/SPEC_ETAPE1.md` du dépôt (v30 au 17/11/2026).

Champs supplémentaires :
- `"bot_season_week"` (BOT uniquement) : semaine de saison lue dans le titre (`"S20-4"`) ou `null`.
- `"player_ingame"` (BOT uniquement) : pseudo en jeu lu dans le bandeau du bas, à titre d'information.
- `"runs_detail"` : liste d'un objet par run, dans le même ordre que `score.runs`. Champs communs :
  `{"video_id": "", "published_at": "", "t": 0, "stage": "", "team": null, "score_source": "", "exact": true}`
  (`t` = secondes dans la vidéo ; `stage` = libellé du boss ou du stage lu à l'écran ; `team` = POC : équipe 1, 2 ou `null` ; GB : groupe 1, 2 ou `null`).
  - POC et GB, en plus : `{"element": "light | fire | water | wind | dark | null", "element_source": ""}` — lu sur les chasseurs à l'écran, sinon dans le titre ; distingue les équipes/groupes quand `team` est inconnu. Deux runs d'une même ligne n'ont jamais de chasseur commun (sinon `a_verifier`). L'Excel affiche l'élément au lieu de « Groupe/Équipe 1/2 ».
  - POC, en plus : `{"sjw": 0, "successor": 0, "hunters": [0, 0, 0]}` ; contrôle : somme = score de la run.
  - GB, en plus : `{"damage": 0, "damage_exact": true, "damage_source": "results | record | hud"}` (`damage` = `Final Score` ; `damage_exact` = `false` si arrondi — `Personal Record` 17.28T, titre ou HUD — et `null` si aucun dégât lu ; `damage_source: record` = `Total Score` du Personal Record quand un seul groupe a joué ; `team` = groupe, connu aussi par `No history`) ; contrôle Results : `Player's Score` + 6 `Hunter Rank` = `Final Score` ; contrôle Personal Record : `Total Rage Count` = RC groupe 1 + RC groupe 2.
- Score POC = « 이번 기록 » de l'écran RESULT, jamais « 기존 기록 » ni l'écran de composition. Jamais le score de l'écran de composition, quel que soit le mode.

### Autres fichiers de l'étape 1 (détail : SPEC_ETAPE1.md §5)

| Fichier | Contenu |
| --- | --- |
| `data/runs/<semaine>/_lectures.json` | Toutes les lectures de score des tris, chacune avec `regles` (version des règles du tri 1 ; une lecture plus ancienne est refaite) ; entrée de `classement.py` |
| `data/runs/<semaine>/_videos.json` | Par vidéo : titre, chaîne, miniature, durée, `mode_guess` |
| `data/runs/<semaine>/_meta.json` | `{week, start_utc, end_utc, frozen, frozen_at}` |
| `data/runs/<semaine>/_boss.json` | Boss / stage de référence déduit (mode, gate, libellé, nombre de vidéos) |
| `data/runs/<semaine>/_rapport.md` | Rapport du dernier passage (quota, vidéos, `a_verifier`, alertes, erreurs) |
| `data/processed.json` | Par video_id : état du traitement ; `pc.sous_titres` et `pc.rotation` = `fait` \| `absent` \| `erreur` |
| `data/channels.json` | `{channel_id, name, uploads_playlist, added_at, source: manuel \| auto}` |

### Build (data/builds/<semaine>/<mode>/<run_id>-<n>.json)

Format complet : `docs/SPEC_ETAPE2.md` §1.2 du dépôt (fait foi ; version courante en tête du fichier). Points clés :
- un build = une run (`runs_detail[i]` → `<run_id>-<i+1>.json`) ;
- `status` : `build_complet | build_partiel | pas_de_build` ; `confidence` : `sur | a_verifier` ;
- identifiants = `id` de la base ; élément non reconnu = `null` ou `unmatched`, jamais inventé ni complété à la main ;
- POC et GB : `element` repris de la run ;
- `sjw.skills` : 6 emplacements `skill_1`, `skill_2`, `ultimate`, `qte_1`, `qte_2`, `qte_3` (`level` peut rester `null`) ;
- stats facultatives (jamais comptées dans le statut).

### Rotation (data/rotations/<semaine>/<mode>/<video_id>.json)

Relevé automatique de l'ordre des compétences (passage en recharge des boutons du HUD), fait sur le PC après les tris 3-4 ; top 3, BOT d'abord. Aucun relevé manuel.

Format complet : `docs/SPEC_ROTATION.md` §3 du dépôt (fait foi ; version courante en tête du fichier). Points clés : un objet par run dans `runs[]` (`run_start_t`, `run_end_t`, `duration_s`, `events`, `limites`) ; chaque événement a `t` (vidéo) et `t_run` (depuis le début de la run), `hunter` (`sjw`, id de la base ou `inconnu`), `slot`, `source`, `confidence` (`sur` | `a_verifier`). Rapport : `data/rotations/<semaine>/_rapport.md`.

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

Le suivi de la discussion (30 lignes maximum) est tenu à jour dans `suivi/<discussion>.md` du dépôt et poussé à chaque étape. Il **n'est pas affiché** à Alexis en fin de réponse ; il ne lui est donné qu'au message n = 15, dans le message prêt à coller pour la nouvelle discussion. Au-delà de 30 lignes, déplacer les anciennes lignes « Fait » dans `suivi/archives/<discussion>.md` et ne garder que les plus récentes :

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

Une section vide s'écrit `- rien`. Ne pas recopier l'historique : seulement l'état actuel. « Besoin d'Alexis » = seulement ce qu'Alexis seul peut faire (CONTEXTE.md §9).

## 5. Reprise d'une discussion

1. Compteur : chaque réponse commence par « Message n/15 » (n = numéro de la réponse précédente + 1). À partir de n = 15 : « ⚠ Discussion longue » et un seul message prêt à coller (ligne de rôle, qui dit d'emblée à la nouvelle discussion qu'elle a le droit de pousser dans sa zone avec `add_repo` (push) ; SUIVI lu dans `suivi/<discussion>.md` ; prochaine action).
2. Envoyer le prompt de démarrage de la discussion (PROMPTS_DISCUSSIONS.md) + le dernier SUIVI.md.
3. Reprendre à « En cours », sans refaire « Fait ».

## 6. Économie de crédits

- Réponses courtes. Pas de reformulation de la demande, pas de résumé de ce qui vient d'être fait.
- Pas de recherche web si l'information est dans le projet, le dépôt ou la base.
- Lire seulement les fichiers et la partie de la base utiles à la tâche ; jamais les archives (`docs/archives/`, `suivi/archives/`) sauf besoin précis.
- Ce qui se répète se code (Python, GitHub Actions) au lieu d'être fait à la main par Claude.
- Autonomie : ne jamais demander à Alexis une information trouvable (dépôt, Projet, slagate.com, forum Netmarble, vidéos via le pipeline, web). Introuvable → hypothèse la plus prudente, marquée « à vérifier » avec sa source. Décision → proposer un choix par défaut et avancer ; Alexis peut refuser.

## 7. Checklists de contrôle

### Classements (étape 1)
- [ ] Toutes les vidéos ont une date de publication postérieure au dernier reset.
- [ ] Le boss / la saison visible correspond à la semaine (GB `Personal Record` : `Time Left in Season` cohérent avec la date de publication ; BOT : `S<n>-<w>` du titre = semaine attendue, aucune run classée en semaine de calcul).
- [ ] Une seule ligne par chaîne ; pas de ré-upload en double.
- [ ] GB (et POC avant le 19/11/2026) : total = somme des runs (GB : une run par groupe ; POC : une run par équipe) ; une seule run sûre est classée avec la note `une seule run`.
- [ ] POC depuis le 19/11/2026 : Rank Score sûr seulement si les contrôles a/b/c passent (Rank Score = 1e6 × (palier − 1 + progression) à ±100 ; progression = Team 1 % + Team 2 % ; contributions = `Total Contribution`) ; « Tier N » d'un texte compte seulement avec une marque POC ; l'élément est informatif.
- [ ] GB : chaque run classée a un écran Results filmé. POC et GB : `element` renseigné ou `null` ; aucun chasseur commun entre les deux runs d'une ligne (GB ; POC avant le 19/11 seulement : depuis, un chasseur commun aux 2 équipes = note seulement).
- [ ] POC avant le 19/11 : chaque run = SJW + successeur + 3 chasseurs.
- [ ] BOT : phases croissantes, dernière phase = chrono du bandeau = `Play Time`. GB : `Player's Score` + 6 `Hunter Rank` = `Final Score` ; `Total Rage Count` = groupe 1 + groupe 2.
- [ ] BOT trié du plus court au plus long ; POC (depuis le 19/11) : palier, puis Goal Progress, puis Rank Score ; les autres du plus haut au plus bas (GB : égalité de RC départagée par les dégâts).
- [ ] BOT et GB : un écran au contrôle échoué ne donne jamais un score ; chrono incomplet = intervalle, phases incomplètes = borne basse, jamais un chrono. GB : un dégât non contrôlé ne départage jamais une égalité de RC. GB : un Personal Record contrôlé (Total Rage Count = groupe 1 + groupe 2) prime sur un Results **filmé** de la même vidéo dont le RC est en conflit : il confirme le RC de ce groupe ; il ne classe jamais une run non filmée (SPEC_ETAPE1 §4.7).
- [ ] Rejets : une actualité n'est rejetée que sans écran de jeu ; un rejet sur le titre seulement pour un autre jeu.
- [ ] Les scores `exact: false` ou `a_verifier` sont signalés.
- [ ] Aucun écart improbable sans vérification (BOT, GB : score provisoire < 70 % de la médiane des provisoires, dès 5 lignes ; ailleurs : ex. score 10 fois au-dessus du 2e).

### Builds (étape 2)
- [ ] 10 builds par mode (×2 runs pour POC et GB) ou raison de l'absence.
- [ ] Chaque identifiant existe dans la base de données.
- [ ] Statut cohérent avec le champ `found`.
- [ ] Éléments interdits absents (interdit = règle `false` ; `null` = inconnu, jamais interdit).
- [ ] Un PowerPoint par vidéo du top 10 et par langue (FR, EN).
- [ ] Aucun élément complété à la main.

### Base de données (étape 3a)
- [ ] Nom FR et EN renseignés.
- [ ] Source et date de vérification présentes.
- [ ] Icône présente pour chaque objet.
- [ ] Version du jeu à jour après chaque patch.

### Vidéos (étape 3b)
- [ ] Chaque choix justifié ; les estimations signalées comme telles.
- [ ] Script FR et EN de même contenu.
- [ ] Intro 2 s et outro 5 s exactement (écran de fin) ; clip vertical : outro 3 s.
- [ ] `video.json` = source unique ; `script.md` en est généré, jamais modifié à la main.
- [ ] Contenu différent des vidéos des semaines précédentes.

### Site (étape 5)
- [ ] Classement de la semaine en ligne après chaque passage.
- [ ] Liens vers les vidéos sources et crédits des joueurs.
- [ ] Pages FR et EN identiques.
- [ ] Liens réseaux sur chaque page.