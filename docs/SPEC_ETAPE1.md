# Spécification — Pipeline étape 1 (classements)

Version 16 — 14/11/2026 (POC et GB : une ligne avec une seule run sûre est classée, décision d'Alexis) — discussion 1 (Classements). Destinataire : discussion 8 (Code).
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
- **Publication proche du reset (v8)** : vidéo publiée moins de `config.reset_alerte_heures` (= 3 h, décision du 13/11, à réajuster après 3 semaines de données) après le reset → note `publiée juste après le reset : semaine précédente ?`. Alerte seulement, jamais un motif de rejet ni un frein au classement. Au GB, le `Time Left in Season` du Personal Record (§4.7) tranche ; au BOT, `S<n>-<w>` du titre (§4.6) tranche s'il est présent.

### 2.3 Statut
- Tout score du tri 1 est **provisoire** : `exact: false`, `confidence: a_verifier`, `score_source` = `titre` / `description` / `sous-titres` (v12 : jamais `hud` pour un RC). Une légende de l'auteur (« Same strat get 132T ») est traitée de la même façon.
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
  - (v10) Plus de variante à lire : les armes de SJW du bandeau ne servent plus au classement.
- GB (v5, captures client anglais du 13/11/2026, boss `Giant Statue`) :
  - **Écran RESULT** : titre `Results` + nom du boss. `Player's Score` (SJW), `Hunter Rank` 1 à 6 (les 6 chasseurs, équipes A + B), `Final Score` (dégâts), `Rage Count` (RC), `Play Time 03:00`, bandeau éventuel `New Record Achieved!`.
  - **Une run = un groupe** (`Group 1` / `Group 2`) de 6 chasseurs (Team A + Team B) + SJW. 2 runs par semaine, comme le POC.
  - L'écran RESULT **n'indique pas le groupe**. On le retrouve avec l'écran `Guild Boss` / `Personal Record` s'il apparaît dans la vidéo (RC et dégâts arrondis par groupe) ; sinon groupe inconnu.
  - **Écran `Guild Boss` → `Personal Record`** : `Total Score` (exact), `Challenge Count`, `Total Rage Count`, puis par groupe le RC et les dégâts arrondis (ex. `Group 1` 167 · 17.28T ; `Group 2` 165 · 15.55T ; total 332 = 167 + 165). C'est un record, mais **accepté comme source au GB (décision d'Alexis, v6)** : voir §4.7.
  - Écran `Form Team` (`Guild Boss Mode`) : `Score` = total du record (ex. 32 842 054 460 310), jamais utilisé.
  - **Écran de combat (HUD), v11** (vidéo `lGDbzyIJcjY`, client anglais, captures `docs/essais/ocr/lGDbzyIJcjY_*.jpg`, 14/11/2026). C'est l'écran pendant la run, **pas un écran de résultat** :
    - en haut à gauche, un bloc de 2 lignes : `Points` (ex. `1,540,584,556`) et `Boss Rage Count` `xN` (ex. `x12`), qui augmentent pendant la run ;
    - en haut au centre : `LV. 150 Giant Statue` (nom du boss), barre de vie en %, multiplicateur de barre `xN` (ex. `x426`, ignoré) ;
    - en haut à droite : chrono décompté depuis `03:00` (`mm:ss`, puis `ss.cc` en rouge sous 1 min, ex. `10.45`) ;
    - à droite : panneau `Team A` / `Team B` (équipe active de 3 chasseurs ; ce n'est **pas** le groupe 1/2) ;
    - bandeaux au centre : `The boss monster refuses to die and becomes enraged!` (+1 au `Boss Rage Count` du HUD, pas au RC classé), `The giant statue is using a powerful attack!` ;
    - une cible secondaire peut remplacer le nom en haut (ex. `LV. 150 Temple Altar` à 130 s) : ce n'est pas le boss.
  - **Règles HUD (v11, révisées v12 après l'essai réel du 14/11 sur `lGDbzyIJcjY`)** :
    - `Points` + `Boss Rage Count` + chrono sur la même image → mode `gb` confirmé (type d'écran `combat`). Le HUD ne donne **jamais** un score `sur`.
    - **`Boss Rage Count` du HUD = information seulement (v12), jamais un RC, même provisoire.** Essai : HUD `x12` à 228 s et à 238 s (chrono `1.00`), écran Results `Rage Count 19`. Le compteur du HUD ne mesure donc pas le RC classé (son sens exact est inconnu). Gardé dans `runs_detail[i].hud_rage_count`. Une vidéo qui n'a que le HUD n'a pas de RC lu à l'image : on garde le RC du titre s'il existe, sinon la vidéo continue les tris (puis `pas_de_score`).
    - **`Points` du HUD = `Final Score` en cours de run (v12, hypothèse [À CONFIRMER] sur 3 autres vidéos).** Essai : `Points 1,593,663,209` à 1 s de la fin, `Final Score 1,601,097,999` sur Results (écart 0,46 %, dégâts de la dernière seconde). Confirmé en partie (v15) : `Pontos 7.884.144.289.064` à 0,80 s pour un titre « Score : 7,9T » (RaidenShadow). Reste 1 comparaison HUD / Results à faire avant de lever le [À CONFIRMER]. Usage :
      - la dernière lecture `Points` avec un chrono ≤ 5 s donne des dégâts **provisoires** : `runs_detail[i].damage`, `damage_exact: false`, `damage_source: hud`, seulement si aucun écran Results n'est lu ;
      - jamais pour le départage d'une ligne classée (le départage n'utilise que `Final Score` ou `Total Score`, §4.1) ;
      - sert au contrôle de l'écran Results (ci-dessous).
      - (Correction v11 : la comparaison avec les 15 763 milliards de la capture du 13/11 n'avait pas de sens, il s'agit d'un autre joueur.)
    - `stage` : pris sur l'écran Results. Le nom en haut du HUD ne sert que s'il n'y a pas d'écran Results, et jamais une cible secondaire (`Temple Altar`).
    - Une lecture HUD incomplète (sans les 3 éléments) est ignorée : l'OCR du HUD est bruité (ex. 50 s : `Points 99,530,637` lu entre 313 989 131 et 770 387 441).
  - **Trouver l'écran Results (v11)** : il suit la fin du chrono (ou la mort du boss). Si un HUD GB montre un chrono ≤ 15 s à l'instant t, lire les images de t à t + 30 s à 1 image/s jusqu'à trouver `Results`. Vérifié : chrono `10.45` à 228 s, Results à 252 s.
  - **Écran Results en animation (v12, précisé v13)** : l'écran se remplit en plusieurs temps, et aucune image ne porte forcément tout. Essai `lGDbzyIJcjY` : à 252 s, titre, boss et bandeau `Your points have been registered.` seuls ; puis valeurs ; à 253 s, l'animation `Rage Rewards` (`Tap the screen to continue.`) recouvre les Hunter Rank 1 à 3, mais `Player's Score`, Hunter Rank 4 à 6, `New Record Achieved!`, `Final Score` et `Rage Count` restent lisibles.
  - **Fusion des images d'un même écran (v13, validé)** : les champs d'un écran Results peuvent venir de plusieurs images, à ces conditions :
    - mêmes vidéo et run : images consécutives entre la première image `Results` et la dernière, sans HUD de combat entre elles, sur 15 s au plus (`config.gb.fusion_max_s = 15`) ;
    - chaque champ garde la valeur lue ; si un champ est lu avec 2 valeurs différentes, on garde la plus fréquente, et en cas d'égalité → conflit, run `a_verifier`, note `conflit de lecture : <champ>` ;
    - **`Rage Count` (v14)** : s'il existe au moins une lecture discordante, la valeur retenue doit avoir **au moins 2 fois plus d'images que toutes les valeurs discordantes réunies** (ex. 2 contre 1 : accepté ; 2 contre 2 ou 3 contre 2 : refusé). Sinon → `a_verifier`, note `conflit de lecture : rage_count`. Toute valeur écartée est notée : `RC discordant écarté : <valeur> (t=<s>)`. Essai `lGDbzyIJcjY` : 19 sur 2 images, 7 sur 1 image → 19 retenu, note `RC discordant écarté : 7`.
    - **Compteurs animés (v15)** : `Rage Count` (et peut-être `Final Score`) défilent de 0 jusqu'à la valeur finale pendant l'animation. Avant le vote, trier les lectures par `t` : si elles ne font que croître (ex. 1 → 183 → 189) et que la dernière valeur est lue sur au moins 2 images consécutives à la fin, c'est la valeur finale ; les valeurs plus petites et plus anciennes sont des étapes de l'animation, ni discordantes ni conflictuelles (note `compteur animé`). Une valeur plus petite lue **après** la valeur finale reste discordante (vote ci-dessus). Essai `awb-GlVIa7Q` : 1, 183, 189 → 189 si l'ordre dans le temps le confirme (**à vérifier sur les images publiées**).
    - la run porte la note `lecture fusionnée (<n> images)` et `t` = l'image où `Rage Count` est lu.
    - Libellés de l'animation à reconnaître pour ne pas les lire comme des valeurs : `Rage Rewards`, `Tap the screen to continue.`
  - **Zones ciblées (v13, validé comme méthode)** : en plus de l'OCR de l'image entière, lecture de zones recadrées et agrandies (titre/boss, `Player's Score`, `Hunter Rank` 1 à 6, `Final Score`, `Rage Count`, `Play Time`). Coordonnées dans `config.gb.zones`, en **fractions de l'image** (x, y, largeur, hauteur entre 0 et 1), jamais en pixels. Valeurs estimées sur du 720p 16:9 : **[À CONFIRMER]** sur au moins 3 autres vidéos, dont une en 1080p. Image au format différent (Short vertical, 4:3, bandes noires) → zones non appliquées, OCR de l'image entière seulement, note `format non standard`. La valeur d'une zone ciblée prime sur celle de l'image entière ; si les deux diffèrent, la note `écart OCR zone/image : <champ>` est ajoutée. Images de référence : `docs/essais/ocr/lGDbzyIJcjY_*results*.jpg`.
    - **Largeur des zones (v15)** : une zone couvre toute la case du champ à l'écran, jamais la largeur d'une valeur vue. Les scores GB vont d'environ 1e9 à plus de 1e14 (14 à 16 chiffres avec séparateurs) : `Final Score`, `Player's Score` et `Hunter Rank` doivent tenir 20 caractères. Une lecture qui perd des chiffres en tête ou en fin (`64,299,126,425` pour 64 299 126 429 862 ; `88,332,559,253` contre `188,332,559,253`) est un défaut de zone, pas une valeur : un nombre dont les groupes de 3 chiffres sont incomplets est rejeté.
    - **Résolution (v15)** : tri 3 et recherche de l'écran Results en **1080p** si la vidéo le propose (sinon la meilleure résolution ≤ 1080p) ; tri 4 en 720p (coût). Les zones en fractions restent valables.
    - **Vidéos de test des zones (v14)**, semaine 2026-11-12, choisies parce qu'elles annoncent une run GB (RC ou score dans le titre) ; résolution et présence de l'écran Results **non vérifiées d'ici** (à contrôler avec `yt-dlp -F` et le tri 3) :
      - `T5dR6iJAn-Y` et `Oj_-5x6700s` (RaidenShadow, « Rage 159 » groupe Feu et « Rage 137 » groupe Lumière, semaine 4) : même joueur, 2 runs → test aussi de la somme groupe 1 + groupe 2 ;
      - `vYtRCpFtSOk` et `MJ2iz5TFmvM` (Eden(이든), 162 Lumière et 160 Feu, titre coréen) : même joueur, 2 runs, client coréen probable → test des libellés coréens ;
      - `nh2D7xZ7dOQ` (SlayOnLow, 165 RC) et `awb-GlVIa7Q` (Ahmad1195, 189 RC, 64.2T).
      Au moins une doit être en 1080p ; sinon, chercher une autre vidéo GB en 1080p la semaine prochaine.
  - **Contrôle Results sans les 6 Hunter Rank (v12, durci v13)** : si la somme `Player's Score` + 6 `Hunter Rank` = `Final Score` n'est pas vérifiable, la run est `sur` seulement si **toutes** ces conditions sont réunies, sinon `a_verifier` :
    1. `Results`, le nom du boss, `Final Score`, `Rage Count` et `Play Time` sont lus (fusion permise) ;
    2. **`Rage Count` lu à l'identique sur au moins 2 images** (c'est le score classé : 2 chiffres, une seule erreur d'OCR change le rang) ;
    3. **`Final Score` confirmé par une source indépendante** : dernier `Points` du HUD avec un chrono ≤ 5 s, et `Points` ≤ `Final Score` ≤ `Points` × 1,02 (`config.gb.hud_tolerance = 0.02`). Sans HUD lisible : `Final Score` identique sur au moins 2 images **et** condition 4 ;
    4. cohérence des valeurs lues : `Player's Score` + les `Hunter Rank` lus < `Final Score`, et les `Hunter Rank` lus décroissent du rang 1 au rang 6.
       Avec le HUD (condition 3 par les `Points`), la condition 4 est un simple contrôle de bon sens : 0 à 6 `Hunter Rank` lus suffisent. **Sans HUD (v14)**, il faut au moins 3 `Hunter Rank` lus pour la condition 4, sinon `a_verifier`. Essai `lGDbzyIJcjY` : rangs 5 et 6 seuls lus (58 465 656 et 22 280 102), accepté car le HUD confirme le `Final Score`.
    La condition « `Player's Score` < `Final Score` » seule (v12) ne suffit plus. Note : `contrôle sans Hunter Rank`.
    Cas test `lGDbzyIJcjY` : RC 19 lu à 252 s et à 253 s (condition 2) ; `Points` 1 596 246 179 à 0,47 s ≤ 1 601 097 999 ≤ 1 628 171 102 (condition 3) ; 313 099 049 + 62 925 78x + 58 465 656 + 22 280 102 ≈ 456,8 millions < 1 601 097 999, et 62,9 M > 58,5 M > 22,3 M (condition 4) → RC 19 `sur`, dégâts 1 601 097 999 exacts, `new_record: true` (bandeau visible à 253 s). Ligne classée avec 19 (v16, une seule run).
- Japonais et autres langues : libellés RESULT **[À CONFIRMER]** (seul le coréen est vu pour POC et HOTM).
- **Langues du GB (v15)** : toutes les langues sont à gérer (CONTEXTE : toutes régions et langues). Libellés rangés par langue dans `config.gb.libelles.<langue>`, jamais en dur. Connus :
  - portugais (RaidenShadow, HUD) : `Pontos` (= `Points`), `Número de Fúrias do Chefão` (= `Boss Rage Count`, information seulement comme en anglais : 120 lu contre 159 dans le titre), `Estátua de Pedra Gigante` (= `Giant Statue`), `Equipe A` / `Equipe B` ; nombres à points (`7.884.144.289.064`) ;
  - écran Results et Personal Record en portugais, HUD/Results/Personal Record en coréen et japonais : **[EN ATTENTE]** des images (prochain essai : publier les images de fin de `T5dR6iJAn-Y` et les images de la run de `vYtRCpFtSOk`, qui n'est pas dans les 30 dernières secondes).
  - Langue sans libellés connus : la vidéo reste `en_cours`, note `libellés <langue> inconnus` ; jamais un score lu sans libellé reconnu.
- **Libellés que l'OCR doit reconnaître au GB (client anglais, v11)** : écran Results : `Results`, `Player's Score`, `Hunter Rank`, `Final Score`, `Rage Count`, `Play Time`, `New Record Achieved!` ; Personal Record : `Guild Boss`, `Personal Record`, `Total Score`, `Challenge Count`, `Total Rage Count`, `Group 1`, `Group 2`, `Time Left in Season` ; HUD : `Points`, `Boss Rage Count`, `Giant Statue`, `Team A`, `Team B`, `WARNING` ; bandeau Results : `Your points have been registered.` Tolérer les fautes d'OCR courantes (`Rage Gount`, `RageCount`, `Rage Coun`).

### 3.2 Contrôles
- POC : `이번 기록` = SJW + successeur + chasseurs 1, 2 et 3. Si égal → `exact: true`, `sur`. Sinon ou illisible → `a_verifier`.
- HOTM : `클리어` + `증명 보너스` = `합산 결과` = `이번 기록`. Si égal → `sur`. `증명 보너스` = niveau × 100 : contrôle d'alerte seulement (`notes`), jamais un motif de rejet.
- BOT (v4) : dernière phase = chrono du bandeau, et `Play Time` = ce chrono tronqué à la seconde ; les phases doivent croître. Si tout concorde → `exact: true`, `sur`. Sinon ou illisible → `a_verifier`.
- Pseudo en jeu (BOT, bandeau du bas) : à enregistrer dans `player_ingame` (nouveau champ) ; la clé du joueur reste `channel_id`.
- GB (v5) : `Player's Score` + les 6 `Hunter Rank` = `Final Score` (vérifié sur la capture du 13/11 : 15 763 121 797 048, exact). Si égal → `exact: true`, `sur`. Hunter Rank illisibles : contrôle de remplacement (v12, §3.1). Le RC est lu à côté ; pas de contrôle arithmétique du RC.
- Jamais `기존 기록`, jamais le score de l'écran de composition.

## 4. Calcul du classement (`pipeline/classement.py`, idempotent)

### 4.1 Une ligne par joueur
- Clé : `channel_id` (+ `gate` au HOTM).
- On rassemble toutes les runs `sur` du joueur dans la semaine, **toutes vidéos confondues**.
- BOT : meilleur chrono (le plus court), un seul classement (§4.6). HOTM : meilleur score **par porte** (un fichier par porte).
- POC et GB : total = **somme des 2 meilleures runs distinctes**, prises dans 1 ou 2 vidéos.
  - POC (confirmé par Alexis) : **une run = une équipe**. Total = meilleure run de l'équipe 1 (`1팀`) + meilleure run de l'équipe 2 (`2팀`). Si l'équipe n'est pas lisible : les 2 meilleures runs, en `a_verifier`. Deux runs de la même équipe ne s'additionnent jamais.
  - GB (v5, réactivé) : classement au **Rage Count**. Total = RC de la meilleure run du groupe 1 + RC de la meilleure run du groupe 2, comme le POC. « Meilleure run » d'un groupe = RC le plus élevé, puis les dégâts (`Final Score`) en cas d'égalité. Groupe illisible : les 2 meilleures runs, en `a_verifier`. Deux runs du même groupe ne s'additionnent jamais.
  - GB, égalité de RC total (fréquente, nombres entiers) : départage par la **somme des dégâts** des 2 runs, puis par §4.2.
  - `score.total` et `score.runs` = RC (`unit: rage_count`) ; dégâts dans `runs_detail[i].damage` ; `team` = groupe (1, 2 ou `null`).
  - **Une seule run (v16, décision d'Alexis du 14/11)** : une ligne avec une seule run `sur` est **classée** (`confidence: sur`, `rank`), total = cette run, note `une seule run`. Si une 2e run (autre équipe / autre groupe) est trouvée plus tard dans la semaine, dans la même vidéo ou une autre, elle s'ajoute au total. Vaut pour le POC et le GB (`No history` ou 2e groupe simplement pas filmé). Une seule run provisoire → `a_verifier` comme avant.

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

### 4.6 BOT : un seul classement, saisons de 4 semaines (v10, décision d'Alexis)
- **Challenge supprimé** : le mode `Battlefield of Time: Challenge` a été retiré du jeu à la mise à jour de mai 2026 (source : forum Netmarble, *Developer Note: 2nd Anniversary Eve* et *5/7 (Thu) Update Details*, lus le 13/11/2026). Un seul classement BOT par semaine : `data/runs/<semaine>/bot.json`. Plus de champ `bot_variant`, plus de fichier `bot-season.json`, `bot-challenge.json` ni `bot-variante-inconnue.json`.
- Un titre contenant `challenge`, `チャレンジ` ou `챌린지` (ancienne vidéo, autre mode) → note `challenge ? (mode supprimé)`, `a_verifier`.
- **Saison (source : *5/7 (Thu) Update Details*)** : 4 semaines de jeu, **1 boss par semaine** (4 boss différents), puis **1 semaine de calcul** sans classement. Cycle de 5 semaines.
  - S20 : début le 22/10/2026 (mise à jour 2.5 du 22/10 ; cohérent avec `S20-4` = semaine 2026-11-12). Semaine de calcul attendue : 2026-11-19. S21-1 attendue : 2026-11-26. Ces dates sont **calculées**, à vérifier sur les vidéos de ces semaines.
  - Paramètres : `config.bot.saison_ref = {"saison": 20, "semaine_saison": 1, "week": "2026-10-22"}`, `config.bot.semaines_jeu = 4`, `config.bot.semaines_calcul = 1`.
  - Semaine de calcul : aucune run BOT attendue. Toute vidéo BOT publiée cette semaine-là est traitée normalement mais reçoit la note `semaine de calcul : run de la semaine précédente ?` et reste `a_verifier` ; le rapport le signale.
- **Contrôle de semaine par le titre (v9, adapté v10)** : `S(\d+)-(\d)` en mot entier, casse indifférente → (saison n, semaine w), w de 1 à `semaines_jeu` (sinon ignoré). Semaine attendue calculée avec le cycle ci-dessus.
  - (n, w) = semaine attendue → note `semaine confirmée (titre)`, lève l'alerte « publiée juste après le reset ».
  - (n, w) = dernière semaine de jeu précédente (y compris par-dessus une semaine de calcul) → `rejected`, raison `semaine_precedente`, `detail` = `S<n>-<w>`.
  - Autre écart → `a_verifier` + note `semaine du titre incohérente : S<n>-<w>`, jamais de rejet. Le rapport signale ≥ 2 vidéos avec le même écart (référence à corriger).
- Boss : un boss par semaine, le contrôle §4.5 s'applique tel quel.
- Champ `bot_season_week` (`"S20-4"` ou `null`) gardé dans la run.
- HOTM, même principe : porte d'après le titre (`제 n관문`, `第n関門`, `gate n`) si l'écran est illisible ; sinon `hotm-gate-inconnue.json`, `rank: null`, jamais publié.

### 4.7 GB : écran `Personal Record` (v6, décision d'Alexis)
- Un joueur qui ne filme que son `Personal Record` est **classé**. Une lecture de cet écran donne 2 runs : groupe 1 et groupe 2, chacune avec son RC (exact) et ses dégâts arrondis (`17.28T`, `exact: false` pour les dégâts).
- **Contrôle** : `Total Rage Count` = RC du groupe 1 + RC du groupe 2. Si égal → RC `sur`, `score_source: record`. Sinon ou illisible → `a_verifier`. `Total Score` (exact) est gardé dans `runs_detail` et sert au départage des dégâts (§4.1).
- **Bonne semaine** : lire `Time Left in Season` (ex. `6d 9h`). Moment de la capture = prochain reset − temps restant. S'il tombe **après** `published_at`, le record date de la saison précédente → `rejected`, raison `semaine_precedente`. Illisible → `a_verifier`. Contrôle du boss (§4.5) comme pour les autres écrans.
  - **Marge (v7)** : la marge vaut la plus petite unité affichée dans `Time Left` (heures → 60 min, `config.gb.record_tolerance_minutes` ; jours seulement → 24 h ; minutes → 1 min). Rejet seulement si la capture tombe après `published_at` + marge.
- **Personal Record prioritaire (v15)** : quand un Personal Record contrôlé (Total = somme des groupes, bonne semaine) est lu dans la vidéo, il **prime** sur un écran Results en conflit pour le RC de chaque groupe. Le Results ne sert alors qu'à départager (dégâts exacts) et à rattacher (règle ci-dessous).
- **Groupe sans run (v15)** : `Group 2  No history` (ou groupe 1) = ce groupe n'a pas encore de run cette semaine. Ce n'est pas une lecture manquante : le groupe joué est connu (`team` = 1 ou 2).
- **Final Score par le Personal Record (v15)** : si un seul groupe a une run (`Challenge Count 1` ou l'autre groupe en `No history`), le `Total Score` (exact, lisible) **est** le `Final Score` de cette run : `runs_detail[i].damage` = `Total Score`, `damage_exact: true`, `damage_source: record`. Contrôle : un écran Results de même RC doit donner ce même nombre ; s'il diffère, le Personal Record l'emporte (note `écart Results/record : <valeur Results>`). Avec 2 groupes joués, `Total Score` = somme des deux runs du record (départage, §4.1).
- **Cas `awb-GlVIa7Q` (Ahmad1195)** : Personal Record à 241 s : `Total Score 64,299,126,429,862`, `Challenge Count 1`, `Total Rage Count 189`, `Group 1 189 · 64.29T`, `Group 2 No history`, `Time Left in Season 6d 22h` → run du groupe 1 : RC 189 `sur` (`score_source: record`), dégâts 64 299 126 429 862 exacts. Capture entre le 12/11 02:01 et 03:00 (19/11 01:00 − 6 j 22 h), vidéo publiée le 12/11 à 02:07 : bonne semaine, l'alerte « publiée juste après le reset » est levée. Ligne **classée** avec 189 (v16, une seule run), complétée si le groupe 2 apparaît plus tard.
- **Cas `nh2D7xZ7dOQ` (SlayOnLow)** : Personal Record en début de vidéo : `Total Score 32,842,054,460,310`, `Total Rage Count 332`, `Group 1 167 · 17.28T`, `Group 2 165 · 15.55T`, `Time Left 6d 9h` → 167 + 165 = 332 RC `sur`, ligne **classable** (2 groupes). C'est la vidéo des captures de référence du 13/11.
- **Avec les écrans Results** de la même semaine : pour chaque groupe, garder la meilleure des runs (RC, puis dégâts). **Rattachement d'une run Results à un groupe (v7)**, dans cet ordre :
  1. RC et dégâts arrondis égaux à ceux d'un seul groupe → ce groupe (c'est la run du record).
  2. RC égal à celui d'un seul groupe et dégâts **supérieurs** à son record → ce groupe (nouveau record ; `New Record Achieved!` renforce, sans être exigé).
  3. Sinon (RC égal pour les 2 groupes, RC différent des deux, ou RC égal mais dégâts inférieurs) → `team: null`.
- Exemple (captures du 13/11) : Personal Record 167 + 165 = 332 RC. Ensuite, une run Results à 165 RC et 15 763 121 797 048 de dégâts (`New Record Achieved!`). Elle remplace celle du groupe 2 (15,55T), car à RC égal elle a plus de dégâts. Total : 332 RC.

## 5. Fichiers de sortie

### 5.1 `data/runs/<semaine>/<mode>.json` (POC, GB), `bot.json` (v10), `hotm-gate-<n>.json`
Format du skill §3, avec ces précisions :
- `channel_id` (nouveau, clé du joueur) ; `player` = nom de la chaîne ; `channel` = idem.
- `video_id` = vidéo de la meilleure run ; `video_ids` (nouveau) = toutes les vidéos utilisées.
- `runs_detail` : un objet par run, dans l'ordre de `score.runs`, avec en plus `video_id`, `published_at`, `t` (secondes dans la vidéo), `stage`, `score_source`, `exact`, `team` (POC : 1, 2 ou `null`).
- `gate` (HOTM) = **entier**. `hotm_ecran.py` renvoie `{"number", "points"}` : n'enregistrer que `number`. `points` est le score de l'écran de composition, jamais utilisé.
- `bot_season_week` (BOT, v9) : `"S20-4"` lu dans le titre, ou `null`. (v10) `bot_variant` supprimé.
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
2. BOT : un seul classement (v10, Challenge supprimé du jeu).
3. BOT : écran RESULT défini (v4). GB : écrans définis (v5).
4. **[À CONFIRMER]** noms anglais des modes ; nom japonais du POC et du GB.
5. Plages plausibles (§2.2) à ajuster après les premières semaines.
6. GB : `Personal Record` accepté comme source (v6, §4.7).
7. BOT : `S20-4` = saison 20, semaine 4 (v9) ; cycle 4 + 1 semaines (v10, source Netmarble). À vérifier sur les vidéos du 19/11 (calcul) et du 26/11 (S21-1).
8. POC et GB avec une seule run : **réglé** (v16, classée, complétée ensuite).

## 8. Corrections demandées à Code dans l'existant
- `pipeline/analyse_porte_mode.py` lit `data/runs/*/hotm.json` → lire `data/runs/*/hotm-gate-*.json`.
- `gate` : entier dans le JSON (voir §5.1).
- Retirer `runs_detail.submode` (skill et code).
- (v16) POC et GB : une ligne avec une seule run `sur` est classée (note `une seule run`), complétée si la 2e run arrive plus tard. Cas tests : `awb-GlVIa7Q` → classé 189 ; `lGDbzyIJcjY` → classé 19.
- (v15) GB : Personal Record prioritaire sur un Results conflictuel ; `Total Score` = `Final Score` quand un seul groupe a une run (`damage_source: record`) et contrôle Results/record ; `No history` = groupe non joué (`team` connu) ; compteurs animés (lectures croissantes dans le temps = animation) ; zones larges (20 caractères, nombre aux groupes incomplets rejeté) ; 1080p pour le tri 3 et la recherche du Results ; libellés par langue dans `config.gb.libelles` (portugais HUD connu) ; publier les images de fin de `T5dR6iJAn-Y` et les images de la run de `vYtRCpFtSOk`. Cas tests : `awb-GlVIa7Q` → groupe 1, RC 189 `sur` (record), dégâts 64 299 126 429 862, ligne `a_verifier` ; `nh2D7xZ7dOQ` → 167 + 165 = 332 `sur`, ligne classée.
- (v14) GB : vote du Rage Count discordant (≥ 2× les discordantes réunies, note `RC discordant écarté`) ; sans HUD, ≥ 3 Hunter Rank lus pour la condition 4 ; tester les zones sur `T5dR6iJAn-Y`, `Oj_-5x6700s`, `vYtRCpFtSOk`, `MJ2iz5TFmvM`, `nh2D7xZ7dOQ`, `awb-GlVIa7Q` (§3.1).
- (v13) GB : fusion des images de l'écran Results (§3.1, conditions et conflits) ; zones ciblées en fractions dans `config.gb.zones` ; contrôle sans Hunter Rank durci (RC identique sur 2 images, Final Score confirmé par le HUD ou 2 images + cohérence des Hunter Rank lus). Corrections de l'essai du 14/11 : `new_record` doit être `true` pour `lGDbzyIJcjY` (bandeau à 253 s) ; `regles` vaut `null` au lieu de 13 ; la lecture HUD porte `score_source: hud` avec `score: null` : mettre `score_source: null` (seul `damage_source: hud`).
- (v12) GB : le HUD ne donne plus de RC (supprimer `score_source: hud` pour le RC) ; champs `runs_detail[i].hud_rage_count` (info) et `damage_source: hud` (dégâts provisoires) ; `points_hud` remplacé par `damage` provisoire ; contrôle Results sans Hunter Rank (§3.1) ; lire l'écran Results jusqu'à la fin de la vidéo. Cas test : `lGDbzyIJcjY` → RC 19 `sur`, dégâts 1 601 097 999, note `contrôle sans Hunter Rank`, ligne `a_verifier` (une seule run).
- (v10) Migration : fusionner `bot-season.json` et `bot-variante-inconnue.json` de la semaine 2026-11-12 dans `bot.json` ; supprimer les anciens fichiers BOT et le champ `bot_variant` (code, tests, site).
