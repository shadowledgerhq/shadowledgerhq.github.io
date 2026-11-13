# Spécification — Pipeline étape 1 (classements)

Version 2 — 13/11/2026 — discussion 1 (Classements). Destinataire : discussion 8 (Code).
Références : `docs/CONTEXTE.md` §3-4, skill shadow-ledger §3, `docs/REFERENCE_ECRANS_*.md`, `pipeline/hotm_ecran.py`.
Marqueurs : **[À CONFIRMER]** = hypothèse à coder en paramètre, modifiable sans toucher au code ; **[EN ATTENTE]** = bloqué par une info manquante, à coder en « non géré » propre (la vidéo reste `en_cours`, jamais une valeur inventée).

---

## 0. Principes

- Une **semaine** = de jeudi 01h00 (Europe/Paris) au jeudi suivant 01h00 (exclu). Identifiant = date du jeudi de début (`2026-11-12`).
- **Joueur = chaîne YouTube** (clé `channel_id`). Le pseudo en jeu n'est pas lu.
- Seul l'**écran RESULT** donne un score `exact: true`. Tout le reste (titre, description, sous-titres, légendes incrustées, miniature sans écran RESULT) = score provisoire, `exact: false`, `confidence: a_verifier`.
- Seules les runs `confidence: sur` reçoivent un `rank`. Les autres figurent dans le fichier avec `rank: null`.
- Tout paramètre réglable (requêtes, plages plausibles, budget, horaires) va dans `pipeline/config/etape1.json`, pas dans le code.

## 1. Recherche YouTube

### 1.1 Fenêtre de dates
- `debut` = dernier jeudi 01:00:00 Europe/Paris ≤ maintenant, converti en UTC (hiver : mercredi→jeudi 00:00Z ; été : mercredi 23:00Z). Utiliser `zoneinfo("Europe/Paris")`, jamais un décalage fixe.
- `fin` = maintenant (passage quotidien) ou l'instant du reset (passage hebdomadaire).
- Une vidéo publiée avant `debut` n'est jamais rattachée à la semaine en cours. Une vidéo publiée après le reset ne compte jamais pour la semaine précédente.

### 1.2 Sources (dans cet ordre)
1. **Chaînes suivies** (`data/channels.json`) : `playlistItems.list` sur la playlist d'uploads (`UU…`), `maxResults=50`, pages suivantes tant que le dernier élément est publié après `debut`. Coût : 1 unité/page.
2. **Recherche** : `search.list` avec `part=snippet`, `type=video`, `order=date`, `publishedAfter=debut`, `publishedBefore=fin`, `maxResults=50`, `q=<requête>`. Page 2 seulement si le dernier résultat de la page 1 est encore dans la fenêtre. Maximum 2 pages par requête. Coût : 100 unités/page.
3. **Détails** : `videos.list` par lots de 50 ids, `part=snippet,contentDetails,liveStreamingDetails`. Coût : 1 unité/lot.

### 1.3 Filtres
- Exclure `liveBroadcastContent` ≠ `none` (live en cours ou à venir).
- Exclure les rediffusions de live (présence de `liveStreamingDetails.actualStartTime`) → `rejected`, raison `live`.
- **Shorts inclus.**
- Toutes langues, toutes régions (pas de `relevanceLanguage` ni de `regionCode`).

### 1.4 Requêtes initiales (`config.queries`, par mode)
Noms coréens et japonais : sources inven.co.kr et gamewith.jp/altema.jp (13/11/2026). Les noms anglais ne sont pas vérifiés.

| Mode | Requêtes |
| --- | --- |
| poc | `solo leveling arise power of calamity` · `solo leveling arise POC` · `나혼렙 재앙의 권좌` · `나 혼자만 레벨업 재앙의 권좌` · `재왕의 권좌` (ancien nom) · `俺アラ 災厄` **[À CONFIRMER : nom japonais]** |
| bot | `solo leveling arise battlefield of time` · `solo leveling arise BOT` · `나혼렙 시간의 전장` · `俺アラ 時の戦場` |
| gb | `solo leveling arise guild boss` · `나혼렙 길드 보스` · `俺アラ ギルドボス` **[À CONFIRMER]** |
| hotm | `solo leveling arise hall of the monarchs` **[À CONFIRMER : nom anglais]** · `solo leveling arise HOTM` · `나혼렙 군주의 회랑` · `俺アラ 君主の回廊` |

- Une vidéo trouvée par plusieurs requêtes = une seule entrée. Le mode issu de la requête n'est qu'un indice (`mode_guess`). Le mode définitif vient de l'écran (§3.1).
- Une chaîne qui obtient au moins une run classée est ajoutée automatiquement à `data/channels.json`.

### 1.5 Quota
- Plafond codé : `config.quota_max_units = 6000` par passage, sur les 10 000 unités/jour de l'API. Le compteur d'unités est écrit dans le rapport (§5.4).
- Répartition indicative : 17 requêtes × 1 page = 1 700 unités, + pages 2 éventuelles ≤ 1 700, + playlists et détails < 100.
- Erreur `quotaExceeded` : arrêter les recherches, continuer les autres étapes et signaler dans le rapport.

## 2. Tri 1 — texte

### 2.1 Où chercher
1. Titre et description (API).
2. Sous-titres : **yt-dlp sur le PC** (`--skip-download --write-subs --write-auto-subs --sub-langs "ko.*,ja.*,en.*,fr.*,zh.*"`). L'API `captions.download` ne marche que pour le propriétaire de la vidéo.
3. Whisper (sur le PC) : seulement si aucun sous-titre n'existe et qu'aucun score n'est trouvé aux étapes 1 et 2.

### 2.2 Formats de nombres (module commun `pipeline/scores.py`, testé)
| Forme | Exemples | Valeur |
| --- | --- | --- |
| Séparateurs de milliers | `131,449,789,393,717` · `131 449 789 393 717` (espace, insécable, fine) · `131.449.789.393.717` | entier |
| Suffixes latins (casse indifférente) | `K` 1e3 · `M` 1e6 · `B`/`bn` 1e9 · `T` 1e12 ; décimale `.` ou `,` (`2.1B`, `2,1B`, `132T`) | arrondi → `exact: false` |
| Coréen | `만` 1e4 · `억` 1e8 · `조` 1e12, cumulables (`131조 4497억`) | idem |
| Japonais / chinois | `万` 1e4 · `億`/`亿` 1e8 · `兆` 1e12, cumulables | idem |
| Chrono (BOT) | `00:19.558` · `0:19` · `19.558s` · `19초` · `19秒` | secondes, 3 décimales |
| Points (HOTM) | `94,600pt` · `94600 points` | entier |

- Une virgule ou un point suivi d'exactement 3 chiffres (et répété) = séparateur de milliers. Sinon = séparateur décimal.
- **Nombres ignorés** : dates, années, `Lv.`/`niv.`, puissance (`CP`, `전투력`, `戦闘力`, `power`, `puissance`), numéros de porte, durées hors BOT.
- **Plage plausible** par mode (`config.plausible`) : POC 1e12–1e16, HOTM 1 000–200 000, BOT 5–600 s, GB [EN ATTENTE]. Valeurs de départ **[À CONFIRMER]** ; un nombre hors plage est ignoré.
- Plusieurs candidats plausibles : garder le plus fort (le plus court au BOT) comme provisoire et lister les autres dans `notes`.

### 2.3 Statut
- Tout score du tri 1 est **provisoire** : `exact: false`, `confidence: a_verifier`, `score_source` = `titre` / `description` / `sous-titres`. Une légende de l'auteur (« Same strat get 132T ») est traitée de la même façon.
- La vidéo passe toujours aux tris suivants jusqu'à lecture de l'écran RESULT.

## 3. Tris 2 à 4 — image (cadre seulement)

Les recadrages OCR sont **[EN ATTENTE]** des images de référence (à régler sur de vraies images).
- Tri 2 : miniature (`maxresdefault`, sinon `hqdefault`). Si l'OCR reconnaît un écran RESULT et que le contrôle (§3.2) passe → `sur`.
- Tri 3 : 10 premières secondes + 30 dernières, 1 image / 2 s. Tri 4 : vidéo entière, 1 image / 10 s.
- **Ne pas s'arrêter au premier écran RESULT** : une vidéo peut en contenir plusieurs (POC : 2 runs ; compilations). Chaque écran RESULT distinct = une run candidate, avec horodatage `t` (secondes).

### 3.1 Mode de l'écran
- POC : titre RESULT `재앙의 권좌` (vu), libellés `플레이어 스코어`, `계승자 스코어`, `이번 기록`.
- HOTM : libellés `클리어`, `증명 보너스`, `합산 결과` (le titre RESULT est le nom du stage, ex. `기만자의 무대`). Porte et `hunter_mode` lus sur l'écran de composition par `hotm_ecran.py`.
- BOT : **[EN ATTENTE]** écran RESULT. Avant ça, ne jamais utiliser le « record » de l'écran de composition : run en `a_verifier`.
- GB : **[EN ATTENTE]** tous les écrans.
- Japonais et autres langues : libellés RESULT **[À CONFIRMER]** (seul le coréen est vu pour POC et HOTM).

### 3.2 Contrôles
- POC : `이번 기록` = SJW + successeur + chasseurs 1, 2 et 3. Si égal → `exact: true`, `sur`. Sinon ou illisible → `a_verifier`.
- HOTM : `클리어` + `증명 보너스` = `합산 결과` = `이번 기록`. Si égal → `sur`. `증명 보너스` = niveau × 100 : contrôle d'alerte seulement (`notes`), jamais un motif de rejet.
- Jamais `기존 기록`, jamais le score de l'écran de composition.

## 4. Calcul du classement (`pipeline/classement.py`, idempotent)

### 4.1 Une ligne par joueur
- Clé : `channel_id` (+ `gate` au HOTM).
- On rassemble toutes les runs `sur` du joueur dans la semaine, **toutes vidéos confondues**.
- BOT : meilleur chrono (le plus court), **par variante** (§4.6). HOTM : meilleur score **par porte** (un fichier par porte).
- POC et GB : total = **somme des 2 meilleures runs distinctes**, prises dans 1 ou 2 vidéos.
  - POC (confirmé par Alexis) : **une run = une équipe**. Total = meilleure run de l'équipe 1 (`1팀`) + meilleure run de l'équipe 2 (`2팀`). Si l'équipe n'est pas lisible : les 2 meilleures runs, en `a_verifier`. Deux runs de la même équipe ne s'additionnent jamais.
  - GB : 2 meilleures runs distinctes ; notion d'équipe **[EN ATTENTE]**.
  - Une seule run trouvée → la ligne existe, `confidence: a_verifier`, `rank: null`.

### 4.2 Égalité
1. Le joueur dont le score a été **complet le plus tôt** passe devant : on compare le `published_at` le plus récent des vidéos utilisées.
2. En dernier recours : `channel_id` par ordre alphabétique (ordre stable).

### 4.3 Arrondis
- Un score provisoire est remplacé dès qu'une run exacte du même joueur est lue. Il n'est jamais additionné à une run exacte.

### 4.4 Doublons et ré-uploads
- Même score exact, même mode (même porte au HOTM) = même run.
  - Même chaîne : compter la run une seule fois.
  - Chaînes différentes : la run revient à la vidéo **la plus ancienne**. L'autre vidéo → `rejected`, raison `doublon`, avec `detail` = video_id d'origine.

### 4.5 Boss / semaine (option b : déduit des données)
- Pour chaque mode (et chaque porte HOTM), lire le libellé du boss ou du stage (`stage`) sur l'écran.
- Libellé de référence de la semaine = le plus fréquent parmi les runs `sur`, s'il y a **au moins 3 vidéos** (`config.boss_min_videos`). Il est écrit dans `data/runs/<semaine>/_boss.json` (mode, gate, libellé, nombre de vidéos).
- Run avec un autre libellé → `a_verifier` + note `boss différent : <libellé>`. Si ce libellé est la référence de la semaine précédente → `rejected`, raison `semaine_precedente`.
- Moins de 3 vidéos : pas de contrôle, note `boss non contrôlé`.

### 4.6 BOT : deux variantes classées séparément (décision d'Alexis)
- `season` : 時の戦場, saison de 49 jours, SJW autorisé. `challenge` : 時の戦場チャレンジ, 7 jours, mode chasseurs uniquement (source : altema.jp, à vérifier en jeu).
- Les deux sont classées **chaque semaine**, dans deux fichiers séparés. On ne compare jamais une variante à l'autre.
- Lecture de la variante sur l'écran : **[EN ATTENTE]** des écrans BOT. Indices utiles : libellé `チャレンジ` / équivalent coréen dans le titre ; absence de SJW = indice de `challenge`, mais pas une preuve.
- Variante illisible → `a_verifier`, `rank: null`.

## 5. Fichiers de sortie

### 5.1 `data/runs/<semaine>/<mode>.json` (POC, GB), `bot-season.json`, `bot-challenge.json`, `hotm-gate-<n>.json`
Format du skill §3, avec ces précisions :
- `channel_id` (nouveau, clé du joueur) ; `player` = nom de la chaîne ; `channel` = idem.
- `video_id` = vidéo de la meilleure run ; `video_ids` (nouveau) = toutes les vidéos utilisées.
- `runs_detail` : un objet par run, dans l'ordre de `score.runs`, avec en plus `video_id`, `published_at`, `t` (secondes dans la vidéo), `stage`, `score_source`, `exact`, `team` (POC : 1, 2 ou `null`).
- `gate` (HOTM) = **entier**. `hotm_ecran.py` renvoie `{"number", "points"}` : n'enregistrer que `number`. `points` est le score de l'écran de composition, jamais utilisé.
- `bot_variant` (BOT) : `season` | `challenge` | `null`.
- `hunter_mode` (HOTM, booléen ou `null`) ; **supprimer `runs_detail.submode`** (doublon).
- Liste triée : runs classées par rang, puis runs `rank: null`.

### 5.2 `data/rejected/<semaine>.json` (liste)
`{"video_id", "channel_id", "title", "published_at", "mode_guess", "reason", "detail", "last_tri", "date"}`
Codes `reason` : `hors_fenetre` · `live` · `pas_de_score` (après tri 4) · `semaine_precedente` · `doublon` · `hors_sujet` (pas Solo Leveling: Arise) · `semaine_gelee`.
Une vidéo rejetée n'est jamais réanalysée.

### 5.3 `data/processed.json` (objet indexé par video_id, toutes semaines)
`{"week", "channel_id", "published_at", "first_seen", "updated_at", "last_tri": 0-4, "status": "en_cours | termine | rejete", "modes": [], "pc_needed": true}`
- `en_cours` : reprise au passage suivant, là où elle s'est arrêtée.
- `termine` / `rejete` : jamais retraitée.

### 5.4 Autres
- `data/channels.json` (nouveau) : `{"channel_id", "name", "uploads_playlist", "added_at", "source": "manuel | auto"}`.
- `data/runs/<semaine>/_meta.json` : `{"week", "start_utc", "end_utc", "frozen": false, "frozen_at": null}`.
- `data/runs/<semaine>/_rapport.md` : réécrit à chaque passage. Contenu : unités de quota, vidéos nouvelles / traitées / rejetées, runs `a_verifier`, alertes boss, erreurs. Lu par la tâche planifiée (discussion 7).

## 6. Horaires et passages

GitHub Actions fonctionne en UTC et peut avoir du retard. Chaque workflow a donc **2 crons** (heure d'été et heure d'hiver). Le script vérifie l'heure de Paris et sort sans rien faire si ce n'est pas le bon créneau ou si le passage du jour est déjà fait (champ dans `_meta.json`).

| Passage | Où | Créneau Paris | Rôle |
| --- | --- | --- | --- |
| `daily.yml` | Actions | 20:00 (accepté jusqu'à 23:59) | Ouvrir la semaine si besoin (`_meta.json`) → recherche (§1) → tri 1 sur titre et description → tri 2 (miniatures) → mise à jour de `processed`/`rejected` → `classement.py` → rapport → commit → mise à jour du site |
| PC quotidien | PC d'Alexis (planificateur, « exécuter dès que possible si l'heure est manquée ») | 20:30 | `git pull` → sous-titres (yt-dlp) + Whisper → tris 3-4 sur les vidéos `pc_needed` et `en_cours` → `classement.py` → rapport → `git push` |
| `weekly.yml` | Actions | jeudi 01:00 (accepté jusqu'à 04:59) | Dernière recherche avec `fin` = instant du reset → tris 1-2 → commit. **Ne gèle pas** : les tris 3-4 ne sont pas faits. |
| PC hebdomadaire | PC | jeudi 01:15 | Tris 3-4 des vidéos restantes de la semaine écoulée → `classement.py` → **gel** (`frozen: true`) → ouverture de la nouvelle semaine → `git push` |

- PC éteint : rien n'est perdu. Le passage suivant traite tout ce qui est `en_cours`. La semaine reste « en attente de gel » jusqu'au passage du PC, et le rapport du daily le signale.
- Après le gel, une vidéo de la semaine gelée découverte en retard → `rejected`, raison `semaine_gelee`.
- PC et Actions écrivent dans les mêmes fichiers : `git pull --rebase` avant chaque écriture, et une seule tentative de fusion automatique. En cas de conflit, arrêter et le signaler dans le rapport.

## 7. Points ouverts (ne bloquent pas le codage)
1. POC équipe 1 + équipe 2 : **réglé** (§4.1).
2. BOT deux variantes : **réglé** (§4.6) ; lecture de la variante à l'écran [EN ATTENTE].
3. **[EN ATTENTE]** BOT : écran RESULT. GB : tous les écrans et le format du Rage Count.
4. **[À CONFIRMER]** noms anglais des modes ; nom japonais du POC et du GB.
5. Plages plausibles (§2.2) à ajuster après les premières semaines.

## 8. Corrections demandées à Code dans l'existant
- `pipeline/analyse_porte_mode.py` lit `data/runs/*/hotm.json` → lire `data/runs/*/hotm-gate-*.json`.
- `gate` : entier dans le JSON (voir §5.1).
- Retirer `runs_detail.submode` (skill et code).
