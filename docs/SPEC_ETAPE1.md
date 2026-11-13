# Spécification — Pipeline étape 1 (classements)

Version 9 — 13/11/2026 (BOT : contrôle de semaine par `S<saison>-<semaine>` du titre) — discussion 1 (Classements). Destinataire : discussion 8 (Code).
Références : `docs/CONTEXTE.md` §3-4, skill shadow-ledger §3, `docs/REFERENCE_ECRANS_*.md`, `pipeline/hotm_ecran.py`.
Marqueurs : **[À CONFIRMER]** = hypothèse à coder en paramètre, modifiable sans toucher au code ; **[EN ATTENTE]** = bloqué par une info manquante, à coder en « non géré » propre (la vidéo reste `en_cours`, jamais une valeur inventée).

---

## 0. Principes

- Une **semaine** = de jeudi 01h00 (Europe/Paris) au jeudi suivant 01h00 (exclu). Identifiant = date du jeudi de début (`2026-11-12`).
- **Joueur = chaîne YouTube** (clé `channel_id`). Le pseudo en jeu, quand il est lisible (BOT), est seulement noté dans `player_ingame`.
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
| Rage Count (GB, v5) | `165 RC` · `RC 167` · `332RC` · `Rage Count 165` ; libellés coréen et japonais **[À CONFIRMER]** | entier |

- Une virgule ou un point suivi d'exactement 3 chiffres (et répété) = séparateur de milliers. Sinon = séparateur décimal.
- **Nombres ignorés** : dates, années, `Lv.`/`niv.`, puissance (`CP`, `전투력`, `戦闘力`, `power`, `puissance`), numéros de porte, durées hors BOT, numéros de saison BOT (`S20-4`).
- **Plage plausible** par mode (`config.plausible`) : POC 1e12–1e16, HOTM 1 000–200 000, BOT 5–180 s (v3), GB 1–500 RC par run (v5). Valeurs de départ **[À CONFIRMER]** ; un nombre hors plage est ignoré.
- **Choix du candidat (v3)** : priorité titre > description > sous-titres ; dans une même source, le **premier** candidat retenu (pas le plus fort). Les autres vont dans `notes`.
- **Candidats exclus (v3)** :
  - contexte hypothétique : nombre précédé de `can`, `could`, `possible`, `up to`, `max`, `~`, `가능`, `可能`, `目標`, `target` (liste `config.hypothese_mots`) ;
  - chapitres de description : ligne qui commence par un horodatage (`0:12 …`), ou au moins 2 horodatages croissants dans la description ;
  - au BOT, une durée en `m:ss` sans millisecondes trouvée dans la description (souvent un chapitre).
- **Chrono BOT (v3)** : `\d{1,3}[.;:,]\d{3}` suivi ou non de `s` = secondes.millisecondes (`19.558`, `23;223s`) ; jamais lu comme un entier.
- **Mots « semaine passée » (v3)** : `last week`, `저번 주`, `지난주`, `先週` dans le titre → note `semaine précédente ?`, la vidéo reste `a_verifier`.
- **Mots-clés de mode (v3)** : mots courts (`bot`, `poc`, `gb`, `hotm`) seulement en mot entier. `GB` (v7) : ajouté, en mot entier et jamais précédé d'un chiffre (`12GB`, `128 GB` = gigaoctets).
- **Relecture (v8)** : chaque lecture du tri 1 porte la version des règles (`regles`, ex. `9`). À chaque passage, une lecture faite avec une version plus ancienne est **refaite** (titre, description, variante BOT, porte HOTM, semaine BOT) tant que la vidéo est `en_cours` ; titre et description relus via `videos.list` (1 unité / 50 vidéos). La note `description non relue` disparaît. Cas vu le 13/11 : `E4lHBPoZeKs` garde `00:32` (chapitre, exclu depuis la v3) et une variante `null` malgré `SEASON 20` dans le titre.
- **Dégâts GB du titre (v8)** : si un titre GB donne un RC et des dégâts (`64.2 T … 189 rc`), les dégâts vont dans `runs_detail[0].damage`, `exact: false` (provisoire, sert seulement au départage tant que l'écran n'est pas lu).
- **Publication proche du reset (v8)** : vidéo publiée moins de `config.reset_alerte_heures` (= 3 h **[À CONFIRMER]**) après le reset → note `publiée juste après le reset : semaine précédente ?`. Alerte seulement, jamais un motif de rejet ni un frein au classement. Au GB, le `Time Left in Season` du Personal Record (§4.7) tranche ; au BOT, `S<n>-<w>` du titre (§4.6) tranche s'il est présent.

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
- BOT (v4, capture client anglais du 13/11/2026) : titre `Results` + nom du boss dessous (ex. `Baruka`). Bloc gauche : `Phase 1` / `Phase 2` / `Phase 3` avec des temps **cumulés** `mm:ss.mmm` (ex. 00:09.281 / 00:14.986 / 00:19.926, le dernier en cyan). Bandeau du bas : pseudo en jeu (ex. `ThenaX`), chrono final (00:19.926), icônes de l'équipe. Haut droite : `Play Time 00:19` (arrondi à la seconde).
  - Score = chrono de la **dernière phase** = chrono du bandeau du bas.
  - Libellés coréens et japonais **[À CONFIRMER]**. Nombre de phases selon le boss **[À CONFIRMER]** : toujours prendre la dernière.
  - Jamais le « record » de l'écran de composition.
  - Bandeau du bas (confirmé par Alexis) : le losange « 1 » est un **rang** (ignoré) ; les 2 icônes après les 3 chasseurs sont les **armes de SJW**.
  - **Indice de variante (v5)** : armes de SJW présentes dans le bandeau → `season` (le challenge se joue sans SJW, source altema.jp). Absentes → `challenge`. Indice **[À CONFIRMER]** sur une capture de challenge.
- GB (v5, captures client anglais du 13/11/2026, boss `Giant Statue`) :
  - **Écran RESULT** : titre `Results` + nom du boss. `Player's Score` (SJW), `Hunter Rank` 1 à 6 (les 6 chasseurs, équipes A + B), `Final Score` (dégâts), `Rage Count` (RC), `Play Time 03:00`, bandeau éventuel `New Record Achieved!`.
  - **Une run = un groupe** (`Group 1` / `Group 2`) de 6 chasseurs (Team A + Team B) + SJW. 2 runs par semaine, comme le POC.
  - L'écran RESULT **n'indique pas le groupe**. On le retrouve avec l'écran `Guild Boss` / `Personal Record` s'il apparaît dans la vidéo (RC et dégâts arrondis par groupe) ; sinon groupe inconnu.
  - **Écran `Guild Boss` → `Personal Record`** : `Total Score` (exact), `Challenge Count`, `Total Rage Count`, puis par groupe le RC et les dégâts arrondis (ex. `Group 1` 167 · 17.28T ; `Group 2` 165 · 15.55T ; total 332 = 167 + 165). C'est un record, mais **accepté comme source au GB (décision d'Alexis, v6)** : voir §4.7.
  - Écran `Form Team` (`Guild Boss Mode`) : `Score` = total du record (ex. 32 842 054 460 310), jamais utilisé.
- Japonais et autres langues : libellés RESULT **[À CONFIRMER]** (seul le coréen est vu pour POC et HOTM).

### 3.2 Contrôles
- POC : `이번 기록` = SJW + successeur + chasseurs 1, 2 et 3. Si égal → `exact: true`, `sur`. Sinon ou illisible → `a_verifier`.
- HOTM : `클리어` + `증명 보너스` = `합산 결과` = `이번 기록`. Si égal → `sur`. `증명 보너스` = niveau × 100 : contrôle d'alerte seulement (`notes`), jamais un motif de rejet.
- BOT (v4) : dernière phase = chrono du bandeau, et `Play Time` = ce chrono tronqué à la seconde ; les phases doivent croître. Si tout concorde → `exact: true`, `sur`. Sinon ou illisible → `a_verifier`.
- Pseudo en jeu (BOT, bandeau du bas) : à enregistrer dans `player_ingame` (nouveau champ) ; la clé du joueur reste `channel_id`.
- GB (v5) : `Player's Score` + les 6 `Hunter Rank` = `Final Score` (vérifié sur la capture du 13/11 : 15 763 121 797 048, exact). Si égal → `exact: true`, `sur`. Le RC est lu à côté ; pas de contrôle arithmétique du RC.
- Jamais `기존 기록`, jamais le score de l'écran de composition.

## 4. Calcul du classement (`pipeline/classement.py`, idempotent)

### 4.1 Une ligne par joueur
- Clé : `channel_id` (+ `gate` au HOTM).
- On rassemble toutes les runs `sur` du joueur dans la semaine, **toutes vidéos confondues**.
- BOT : meilleur chrono (le plus court), **par variante** (§4.6). HOTM : meilleur score **par porte** (un fichier par porte).
- POC et GB : total = **somme des 2 meilleures runs distinctes**, prises dans 1 ou 2 vidéos.
  - POC (confirmé par Alexis) : **une run = une équipe**. Total = meilleure run de l'équipe 1 (`1팀`) + meilleure run de l'équipe 2 (`2팀`). Si l'équipe n'est pas lisible : les 2 meilleures runs, en `a_verifier`. Deux runs de la même équipe ne s'additionnent jamais.
  - GB (v5, réactivé) : classement au **Rage Count**. Total = RC de la meilleure run du groupe 1 + RC de la meilleure run du groupe 2, comme le POC. « Meilleure run » d'un groupe = RC le plus élevé, puis les dégâts (`Final Score`) en cas d'égalité. Groupe illisible : les 2 meilleures runs, en `a_verifier`. Deux runs du même groupe ne s'additionnent jamais.
  - GB, égalité de RC total (fréquente, nombres entiers) : départage par la **somme des dégâts** des 2 runs, puis par §4.2.
  - `score.total` et `score.runs` = RC (`unit: rage_count`) ; dégâts dans `runs_detail[i].damage` ; `team` = groupe (1, 2 ou `null`).
  - Une seule run trouvée → la ligne existe, `confidence: a_verifier`, `rank: null`.

### 4.2 Égalité
1. Le joueur dont le score a été **complet le plus tôt** passe devant : on compare le `published_at` le plus récent des vidéos utilisées.
2. En dernier recours : `channel_id` par ordre alphabétique (ordre stable).

### 4.3 Arrondis
- Un score provisoire est remplacé dès qu'une run exacte du même joueur est lue. Il n'est jamais additionné à une run exacte.

### 4.4 Doublons et ré-uploads
- Règle appliquée seulement aux modes de `config.doublon_modes` = `["poc"]` (v3). Le score POC a 15 chiffres, et la règle est encore plus sûre si les 5 nombres du détail sont aussi identiques.
- Mode concerné : même score exact, même mode = même run.
  - Même chaîne : compter la run une seule fois.
  - Chaînes différentes : la run revient à la vidéo **la plus ancienne**. La run en trop est retirée de l'autre vidéo. Cette vidéo n'est rejetée (`doublon`, `detail` = video_id d'origine) que si elle n'a plus aucune run.
- BOT et HOTM (scores ronds ou chronos identiques possibles) : pas de dédoublonnage automatique. Même score sur 2 chaînes → les deux lignes sont gardées, note `doublon possible : <video_id>`, contrôle manuel (discussion 1).

### 4.5 Boss / semaine (option b : déduit des données)
- Pour chaque mode (et chaque porte HOTM), lire le libellé du boss ou du stage (`stage`) sur l'écran.
- Libellé de référence de la semaine = le plus fréquent parmi les runs `sur`, s'il y a **au moins 3 vidéos** (`config.boss_min_videos`). Il est écrit dans `data/runs/<semaine>/_boss.json` (mode, gate, libellé, nombre de vidéos).
- Run avec un autre libellé → `a_verifier` + note `boss différent : <libellé>`. Si ce libellé est la référence de la semaine précédente → `rejected`, raison `semaine_precedente`.
- Moins de 3 vidéos : pas de contrôle, note `boss non contrôlé`.

### 4.6 BOT : deux variantes classées séparément (décision d'Alexis)
- `season` : 時の戦場, saison de 49 jours, SJW autorisé. `challenge` : 時の戦場チャレンジ, 7 jours, mode chasseurs uniquement (source : altema.jp, à vérifier en jeu).
- Les deux sont classées **chaque semaine**, dans deux fichiers séparés. On ne compare jamais une variante à l'autre.
- Lecture de la variante sur l'écran : **[EN ATTENTE]** des écrans BOT.
- **Indice du titre (v3, élargi en v8)** — casse indifférente, espace facultatif :
  - `challenge`, `チャレンジ`, `챌린지` → `challenge` ;
  - `S\d+` en mot entier, suivi ou non de `-\d+` (`S20`, `s20`, `S20-4`), `season\s*\d+`, `시즌\s*\d+`, `シーズン\s*\d+` → `season`. Titres du 13/11 concernés : `s20` (X SLA, PADWAE), `BOT S20` (Keos), `시즌20` (리히온), `SEASON 20` (Black Thunder X).
  - Les deux indices ou aucun → variante inconnue. Indice accepté avec la note `variante d'après le titre` ; l'écran prime dès qu'il est lu.
- **Contrôle de semaine par le titre (v9, confirmé par Alexis : `S20-4` = saison 20, semaine 4)** :
  - Lecture : `S(\d+)-(\d)` en mot entier, casse indifférente → (saison n, semaine w), w de 1 à 7 (sinon ignoré).
  - Référence : `config.bot.saison_ref = {"saison": 20, "semaine_saison": 4, "week": "2026-11-12"}` (déduite des titres `a-923ClD9Rc` et `Lt84IhMjBvM`, publiés dans la semaine 2026-11-12). Une saison = 7 semaines, saisons enchaînées sans pause **[À CONFIRMER]**. Semaine attendue (n, w) calculée à partir de la référence et de l'écart en semaines.
  - (n, w) = semaine attendue → note `semaine confirmée (titre)`, lève l'alerte « publiée juste après le reset ».
  - (n, w) = semaine **précédente** attendue → `rejected`, raison `semaine_precedente`, `detail` = `S<n>-<w>`.
  - Autre écart → `a_verifier` + note `semaine du titre incohérente : S<n>-<w>` (contrôle manuel, discussion 1). Le calendrier des saisons est peut-être faux : ne jamais rejeter dans ce cas.
  - Le rapport (§5.5) signale toute semaine où au moins 2 vidéos donnent un même (n, w) différent de l'attendu : la référence est alors à corriger.
- Variante inconnue → `data/runs/<semaine>/bot-variante-inconnue.json`, `rank: null`, jamais publié sur le site.
- HOTM, même principe : porte d'après le titre (`제 n관문`, `第n関門`, `gate n`) si l'écran est illisible ; sinon `hotm-gate-inconnue.json`, `rank: null`, jamais publié.

### 4.7 GB : écran `Personal Record` (v6, décision d'Alexis)
- Un joueur qui ne filme que son `Personal Record` est **classé**. Une lecture de cet écran donne 2 runs : groupe 1 et groupe 2, chacune avec son RC (exact) et ses dégâts arrondis (`17.28T`, `exact: false` pour les dégâts).
- **Contrôle** : `Total Rage Count` = RC du groupe 1 + RC du groupe 2. Si égal → RC `sur`, `score_source: record`. Sinon ou illisible → `a_verifier`. `Total Score` (exact) est gardé dans `runs_detail` et sert au départage des dégâts (§4.1).
- **Bonne semaine** : lire `Time Left in Season` (ex. `6d 9h`). Moment de la capture = prochain reset − temps restant. S'il tombe **après** `published_at`, le record date de la saison précédente → `rejected`, raison `semaine_precedente`. Illisible → `a_verifier`. Contrôle du boss (§4.5) comme pour les autres écrans.
  - **Marge (v7)** : la marge vaut la plus petite unité affichée dans `Time Left` (heures → 60 min, `config.gb.record_tolerance_minutes` ; jours seulement → 24 h ; minutes → 1 min). Rejet seulement si la capture tombe après `published_at` + marge.
- **Avec les écrans Results** de la même semaine : pour chaque groupe, garder la meilleure des runs (RC, puis dégâts). **Rattachement d'une run Results à un groupe (v7)**, dans cet ordre :
  1. RC et dégâts arrondis égaux à ceux d'un seul groupe → ce groupe (c'est la run du record).
  2. RC égal à celui d'un seul groupe et dégâts **supérieurs** à son record → ce groupe (nouveau record ; `New Record Achieved!` renforce, sans être exigé).
  3. Sinon (RC égal pour les 2 groupes, RC différent des deux, ou RC égal mais dégâts inférieurs) → `team: null`.
- Exemple (captures du 13/11) : Personal Record 167 + 165 = 332 RC. Ensuite, une run Results à 165 RC et 15 763 121 797 048 de dégâts (`New Record Achieved!`). Elle remplace celle du groupe 2 (15,55T), car à RC égal elle a plus de dégâts. Total : 332 RC.

## 5. Fichiers de sortie

### 5.1 `data/runs/<semaine>/<mode>.json` (POC, GB), `bot-season.json`, `bot-challenge.json`, `hotm-gate-<n>.json`
Format du skill §3, avec ces précisions :
- `channel_id` (nouveau, clé du joueur) ; `player` = nom de la chaîne ; `channel` = idem.
- `video_id` = vidéo de la meilleure run ; `video_ids` (nouveau) = toutes les vidéos utilisées.
- `runs_detail` : un objet par run, dans l'ordre de `score.runs`, avec en plus `video_id`, `published_at`, `t` (secondes dans la vidéo), `stage`, `score_source`, `exact`, `team` (POC : 1, 2 ou `null`).
- `gate` (HOTM) = **entier**. `hotm_ecran.py` renvoie `{"number", "points"}` : n'enregistrer que `number`. `points` est le score de l'écran de composition, jamais utilisé.
- `bot_variant` (BOT) : `season` | `challenge` | `null`. `bot_season_week` (BOT, v9) : `"S20-4"` lu dans le titre, ou `null`.
- `hunter_mode` (HOTM, booléen ou `null`) ; **supprimer `runs_detail.submode`** (doublon).
- Liste triée : runs classées par rang, puis runs `rank: null`.

### 5.2 `data/rejected/<semaine>.json` (liste)
`{"video_id", "channel_id", "title", "published_at", "mode_guess", "reason", "detail", "last_tri", "date"}`
Codes `reason` (v6 : `semaine_precedente` couvre aussi un Personal Record de la saison précédente ; v9 : et un `S<n>-<w>` BOT de la semaine précédente) : `hors_fenetre` · `live` · `pas_de_score` (après tri 4) · `semaine_precedente` · `doublon` · `hors_sujet` (pas Solo Leveling: Arise) · `semaine_gelee`.
Une vidéo rejetée n'est jamais réanalysée.

### 5.3 `data/processed.json` (objet indexé par video_id, toutes semaines)
`{"week", "channel_id", "published_at", "first_seen", "updated_at", "last_tri": 0-4, "status": "en_cours | termine | rejete", "modes": [], "pc_needed": true}`
- `en_cours` : reprise au passage suivant, là où elle s'est arrêtée.
- `termine` / `rejete` : jamais retraitée.

### 5.4 Fichiers internes (v3)
- `data/runs/<semaine>/_lectures.json` : toutes les lectures de score des tris (entrée de `classement.py`) ; champ `regles` (v8).
- `data/runs/<semaine>/_videos.json` : titre, chaîne, miniature, durée, `mode_guess`.
- `processed.json[video].pc.sous_titres` : `fait` | `absent` | `erreur`.

### 5.5 Autres
- `data/channels.json` (nouveau) : `{"channel_id", "name", "uploads_playlist", "added_at", "source": "manuel | auto"}`.
- `data/runs/<semaine>/_meta.json` : `{"week", "start_utc", "end_utc", "frozen": false, "frozen_at": null}`.
- `data/runs/<semaine>/_rapport.md` : réécrit à chaque passage. Contenu : unités de quota, vidéos nouvelles / traitées / rejetées, runs `a_verifier`, alertes boss, alerte référence de saison BOT (v9), erreurs. Lu par la tâche planifiée (discussion 7).

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
- **Gel (v3)** : `pc.geler = false` tant que les tris 3-4 ne sont pas codés. On ne gèle jamais une semaine dont toutes les lignes sont provisoires. Une fois l'OCR en place : au gel, vidéo sans aucun score après le tri 4 → `pas_de_score` ; ligne seulement provisoire → archivée avec `rank: null` et la mention « non vérifié », jamais rejetée.
- PC et Actions écrivent dans les mêmes fichiers : `git pull --rebase` avant chaque écriture, et une seule tentative de fusion automatique. En cas de conflit, arrêter et le signaler dans le rapport.

## 7. Points ouverts (ne bloquent pas le codage)
1. POC équipe 1 + équipe 2 : **réglé** (§4.1).
2. BOT deux variantes : **réglé** (§4.6) ; lecture de la variante à l'écran [EN ATTENTE].
3. BOT : écran RESULT défini (v4) ; variante d'après les armes de SJW (v5) **[À CONFIRMER]** sur une capture de challenge. GB : écrans définis (v5).
4. **[À CONFIRMER]** noms anglais des modes ; nom japonais du POC et du GB.
5. Plages plausibles (§2.2) à ajuster après les premières semaines.
6. GB : `Personal Record` accepté comme source (v6, §4.7).
7. BOT : `S20-4` = saison 20, semaine 4 : **réglé** (v9, §4.6). Reste **[À CONFIRMER]** : 7 semaines par saison, saisons sans pause.

## 8. Corrections demandées à Code dans l'existant
- `pipeline/analyse_porte_mode.py` lit `data/runs/*/hotm.json` → lire `data/runs/*/hotm-gate-*.json`.
- `gate` : entier dans le JSON (voir §5.1).
- Retirer `runs_detail.submode` (skill et code).
- (v8) `docs/SPEC_ETAPE1.md` du dépôt est encore en v6 : le remplacer par la dernière version (v9).
