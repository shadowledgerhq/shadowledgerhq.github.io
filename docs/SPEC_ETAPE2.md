# Spécification — Étape 2 : builds du top 10 et PowerPoint

Version 5 — 17/11/2026 — discussion 2 (Builds). Destinataire : discussion 8 (Code).
Nouveauté v5 : reconnaissance par cartes de référence (chasseurs, ombres) prioritaire (§2.1) ; élément de la run et contrôle des groupes GB/POC (§1.2, §2.3) ; règles `null` = inconnu (§2.3) ; zones établies à partir des images extraites par le pipeline, plus de captures demandées à Alexis (§5).
Nouveauté v4 : builds sur classement provisoire quand un mode n'a aucune ligne classée (§0), demandé par la discussion 3 pour le BOT de la semaine 2026-11-12.
Nouveautés v3 : écrans hors composition (§1.4 : fiche de SJW, stats 能力値情報, statues 彫像, gemmes 宝石情報, soutien 討伐支援), reconnaissance par le **nom écrit** quand il est visible (§2.1), stats du successeur, slides Statues et Gemmes (§3.2). Stats toujours facultatives. Source : captures POC (client JA, `docs/essais/composition/poc_*_ja.png`) et description de la discussion 8 (15/11/2026).
Nouveautés v2 : écran de composition et onglets réels (§1.3), stats facultatives (décision d'Alexis), position des compétences de SJW et des artefacts, reconnaissance avec la banque actuelle seulement (décision d'Alexis, §2.1), §5 et §7 mis à jour. Source des positions : 5 captures BOT (client JA, `docs/essais/composition/bot_*_ja.png`) et capture HOTM de SJW (13/11/2026).
Références : `docs/CONTEXTE.md` §4 (étape 2), `docs/SPEC_ETAPE1.md`, `docs/REFERENCE_ECRANS_*.md`, `data/db/_schema.md`, `data/rules/<semaine>.json`, `pipeline/sjw.py`, `pipeline/hotm_ecran.py`, `pipeline/export_excel.py`.
Marqueurs (mêmes sens qu'à l'étape 1) : **[À CONFIRMER]** = hypothèse codée en paramètre dans `pipeline/config/etape2.json` ; **[EN ATTENTE]** = info manquante, à coder en « non géré » propre (élément `null` + note, jamais une valeur inventée).

---

## 0. Principes

- **Builds analysés** : les lignes `rank` 1 à 10 (`confidence: sur`) de `data/runs/<semaine>/<mode>.json` (`poc`, `bot`, `gb`, `hotm-gate-<n>`). Une ligne `rank: null` n'a pas de build.
- **Classement provisoire (v4)** : si un mode n'a **aucune** ligne `rank` 1 à 10, on prend les `config.top` premières lignes `a_verifier` triées par score provisoire (même ordre que le classement : BOT du plus court au plus long, autres du plus haut au plus bas). Paramètre `config.builds_provisoires = true`. Ces builds portent `"line_provisional": true`, `rank: null`, `provisional_rank` (1 à 10), `confidence: a_verifier`, note `ligne non classée (score provisoire)`. PowerPoint : bandeau `CLASSEMENT PROVISOIRE` sur la slide de titre et rang affiché `~n`. Dès qu'une ligne du mode devient classée, on revient au §0 normal et les builds provisoires du mode sont supprimés au passage suivant.
- **Un build = une run** : un objet de `runs_detail[i]` donne un build `<run_id>-<i+1>.json`. POC et GB : 2 runs = 2 builds, éventuellement dans 2 vidéos différentes.
- **Où chercher** : dans la vidéo `runs_detail[i].video_id`, l'écran de composition (onglets) **avant** l'écran RESULT de la run (`t`). Si la vidéo contient 2 runs, on prend la composition située entre le RESULT précédent et celui de la run.
- **Reconnaissance** : par icône (OpenCV, comparaison avec `data/icons/<categorie>/`). Sur l'écran de composition, aucun nom n'est écrit ; les noms écrits des écrans hors composition sont lus par OCR (v3, §1.4 et §2.1), ainsi que les chiffres (niveaux, stats).
- **Ne rien inventer** : un élément non reconnu reste `null`. Un nom absent de la base s'affiche par son `id`, jamais traduit à la main.
- **Idempotent** : un build est recalculé à chaque passage tant que sa vidéo est `en_cours` ; un build `build_complet` n'est plus retraité.
- Paramètres réglables dans `pipeline/config/etape2.json`, pas dans le code.

## 1. Éléments à extraire, mode par mode

### 1.1 Éléments attendus
« oui » = attendu et compté dans le statut ; « règle » = dépend de `data/rules/<semaine>.json` ; « fac. » = facultatif (affiché s'il est trouvé, jamais compté) ; « — » = sans objet (clé `null`, pas de slide).

| Élément | Quantité | POC | BOT | GB | HOTM avec SJW | HOTM sans SJW |
| --- | --- | --- | --- | --- | --- | --- |
| SJW présent | 1 | règle | règle | règle | oui | — |
| Armes de SJW | 2 | règle | règle | règle | oui | — |
| Artefacts de SJW | 8 pièces | règle | règle | règle | oui | — |
| Noyaux de SJW | 3 | règle | règle | règle | oui | — |
| Stats de SJW | 10 + 5 | fac. | fac. | fac. | fac. | — |
| Compétences de SJW | 6 emplacements | règle | règle | règle | oui | — |
| Bénédictions | 8 | règle | règle | règle | oui | — |
| Chasseurs | 3 (GB : 6) | oui | oui | oui (A1-3, B1-3) | oui | oui |
| Arme de chaque chasseur | 1 par chasseur | oui | oui | oui | oui | oui |
| Artefacts | 8 pièces par chasseur | oui | oui | oui | oui | oui |
| Noyaux | 3 par chasseur | oui | oui | oui | oui | oui |
| Stats | 10 + 5 par chasseur | fac. | fac. | fac. | fac. | fac. |
| Ombres | 3 | règle | règle | règle | oui | oui |
| Successeur | 1 | règle | règle | règle | oui | oui |
| Soutien de subjugation | 3 choix (1 par colonne) | fac. | — | — | — | — |
| Preuve d'entraînement | niveau + handicaps | — | — | — | fac. | fac. |
| Stats du successeur | 10 | fac. | fac. | fac. | fac. | fac. |
| Statues (v3) | 5 statues × 3 options | fac. | fac. | fac. | fac. | fac. |
| Gemmes (v3) | 5 couleurs + bonus | fac. | fac. | fac. | fac. | fac. |

- **Règles de la semaine** : SJW, compétences et bénédictions sont attendus si `rules.<mode>.sjw` (et `sjw_skills`, `blessings`) valent `true`. Ombres : `shadows`. Successeur : `successor`. Bloc du mode `null` → **[EN ATTENTE]** (§5). Pour le BOT, lire `modes.bot`, sinon `modes.bot_season` (le fichier du 12/11 garde l'ancien découpage).
- **HOTM** : `hunter_mode` vient de la run, c'est le booléen déjà codé par `hotm_ecran.py`. `false` = avec SJW, `true` = sans SJW, `null` = inconnu. On ne cherche SJW que si `rules.hotm.sjw == true` **et** `hunter_mode == false`.
  - Si `hunter_mode` vaut `null`, on le déduit de la composition : 4 onglets sans bénédictions → `true` ; 5 onglets, ou un personnage à gauche des 3 chasseurs → `false`. Note : `hunter_mode déduit`. Sinon il reste `null` (§2.2).
- **Stats** : les 15 lignes `required: true` de `data/db/stats.json`, soit 10 stats et 5 attributs. La puissance de combat est facultative (info). Elles sont lisibles seulement si l'écran de stats du personnage est filmé (`REFERENCE_ECRANS_STATS.md`). **Décision d'Alexis (v2, 14/11/2026) : facultatives**, `config.stats_obligatoires = false`. Elles sont cherchées et affichées si l'écran est filmé, jamais comptées dans le statut. La puissance de combat de chaque personnage (onglet personnages) n'est pas une stat du build. **v3 : confirmé, toujours facultatives**, maintenant que l'écran de stats est connu (§1.4) : il n'apparaît que si le joueur l'ouvre.
- **Statues et gemmes (v3)** : **valables dans tous les modes** (confirmé par Alexis le 15/11/2026). Lues dans tout mode si l'écran est filmé, toujours facultatives, jamais comptées dans le statut.
- **Hors build pour l'instant** : les 8 icônes de compétences de chaque chasseur (décision d'Alexis v2 : « plus tard »), les stats principales et secondaires des pièces d'artefact, et le sens des pastilles de set. Voir §5.

### 1.2 Format JSON — `data/builds/<semaine>/<mode>/<run_id>-<n>.json`
Ce format remplace l'exemple du skill §3 (« Build »). Pour le HOTM, `<mode>` = `hotm-gate-<n>`.

```json
{
  "spec": 5,
  "run_id": "poc-2026-11-12-XXXXXXXXXXX",
  "run_index": 1,
  "week": "2026-11-12",
  "mode": "poc",
  "gate": null,
  "hunter_mode": null,
  "rank": 1,
  "line_provisional": false,
  "provisional_rank": null,
  "player": "nom de la chaîne",
  "channel_id": "UC…",
  "video_id": "XXXXXXXXXXX",
  "t_result": 183,
  "t_composition": [4, 12],
  "team": 1,
  "element": "dark",
  "rules": {"week": "2026-11-12", "sjw": true, "sjw_skills": true, "blessings": true, "shadows": true, "successor": true},
  "status": "build_complet | build_partiel | pas_de_build",
  "confidence": "sur | a_verifier",
  "sjw": {
    "weapons": [{"id": "…", "level": null}, {"id": null, "level": null}],
    "artifacts": [{"slot": "helmet", "set_id": "…", "level": null}],
    "cores": [{"slot": "mind", "id": "…", "level": 25}],
    "stats": {"attack": 195607, "crit-rate": {"percent": 50.0, "rating": 19191}, "strength": 697},
    "skills": [{"slot": "skill_1", "id": "…", "level": 5}],
    "blessings": [{"id": "…", "level": 5}]
  },
  "hunters": [
    {"position": 1, "team_slot": null, "id": "…", "weapon": {"id": "…", "level": null},
     "artifacts": [], "cores": [], "stats": {}}
  ],
  "set_bonuses": {"sjw": [{"set_id": "…", "pieces": 4}], "hunter_1": []},
  "shadows": [{"position": 1, "id": "…"}],
  "successor": {"id": "…", "level": null, "stats": {}},
  "subjugation_support": null,
  "proof": null,
  "statues": [{"position": 1, "grade": "D", "options": [{"text_read": "…", "lang": "ja", "grade": "S", "id": null}]}],
  "gems": {"colors": [{"position": 1, "color": null, "level": 10}],
           "bonuses": [{"stat": "attack", "unit": "percent", "value": 12.0}]},
  "found": {"sjw": true, "sjw_weapons": true, "sjw_artifacts": false, "sjw_cores": true, "sjw_stats": false,
            "sjw_skills": true, "blessings": true, "hunters": true, "weapons": true, "artifacts": false,
            "cores": true, "stats": false, "shadows": true, "successor": true,
            "subjugation_support": null, "proof": null,
            "successor_stats": null, "statues": null, "gems": null},
  "counts": {"artifacts": "22/24", "cores": "9/9"},
  "found_at": {"hunters": {"tri": "tri-3", "t": [4, 6]}},
  "unmatched": [{"element": "cores", "owner": "hunter_2", "slot": "body", "best_id": "…", "score": 0.61, "crop": "…"}],
  "notes": "",
  "sources": [{"type": "video", "video_id": "XXXXXXXXXXX", "t": [4, 6, 8, 12]}]
}
```

Règles du format :
- **Identifiants** = `id` de la base (`hunters`, `weapons`, `artifact_sets`, `cores`, `shadows`, `successors`, `sjw_skills`, `blessings`, `subjugation_support`, `proof_modifiers`). Un `id` absent de la base est une erreur de contrôle.
- **Emplacements d'artefact** (8, dans cet ordre) : `helmet`, `chestplate`, `gloves`, `boots`, `necklace`, `bracelet`, `ring`, `earrings`. La pièce est reconnue par son icône `data/icons/artifact_pieces/<set_id>--<slot>.png`, d'où `set_id`. Un emplacement vide à l'écran donne `"set_id": null` avec la note `emplacement vide`, ce qui est différent de « non reconnu ».
- **Noyaux** : emplacements `mind`, `body`, `spirit` (champ `slot` de `cores.json`). Niveau lu si visible (`25`), sinon `null`.
- **Compétences de SJW** : 6 emplacements, déjà codés dans `pipeline/sjw.py` (`skill_1`, `skill_2`, `ultimate`, `qte_1`, `qte_2`, `qte_3`) ; `level` vaut `null` si aucun niveau n'est affiché.
- **Bénédictions** : 8 objets `{id, level}`.
- **Stats** : clés = `id` de `stats.json`. Valeur `raw` → entier. Valeur `percent_with_rating` → `{"percent", "rating"}`, lue au format `50% (19191)`. Une stat non lue est absente de l'objet.
- **`element` (v5)** : repris de `runs_detail[i].element` de l'étape 1 (light, fire, water, wind, dark ou `null`), jamais lu par l'étape 2 ; sert au titre de la slide 1 (« Run Feu » au lieu de « Groupe 1 » quand le groupe est inconnu).
- **GB** : `hunters` contient 6 entrées, `team_slot` vaut `"A1"` à `"B3"`, et `team` = groupe 1/2 de la run (repris de l'étape 1).
- **`set_bonuses`** : calculé par le code à partir des 8 pièces (nombre de pièces par set), jamais lu. Les paliers d'effet (2/4/8) viennent de `artifact_sets.json`.
- **POC** : `subjugation_support` = liste de 3 `id` (colonnes 1 à 3) ou `null`.
- **HOTM** : `proof` = `{"level": 931, "modifiers": [{"id": "…", "level": 5}]}` ou `null`. Contrôle : somme des coûts = `level` ; sinon note `contrôle preuve`.
- **Statues (v3)** : 5 objets dans l'ordre de l'écran ; `grade` de la statue et de chaque option = lettre lue (`E`, `D`, `C`, `B`, `A`, `S`). Le texte de l'option est gardé tel qu'il est lu (`text_read`, `lang`) ; `id` reste `null` tant que la base n'a pas de catégorie statues (§5). Jamais de traduction.
- **Gemmes (v3)** : `colors` = 5 objets (`position` 1 à 5 dans l'ordre de l'écran, `color` = nom de couleur seulement si la base le définit, sinon `null`, `level` lu). `bonuses` = bonus totaux affichés, `stat` = `id` de `stats.json` (ATQ % → `attack`, PV % → `hp`, DEF % → `defense`, pénétration → `defense-penetration`, mana → `mana`), `unit` = `percent` ou `flat` selon l'affichage.
- **Stats du successeur (v3)** : `successor.stats`, même format que les stats des personnages.
- **`found`** : `true` = complet ; `false` = attendu mais incomplet ; `null` = non attendu ou facultatif non trouvé. `counts` = nombre trouvé / nombre attendu pour les éléments multiples.
- **`unmatched`** : icônes vues mais non reconnues (score sous le seuil, §2.1). On garde le meilleur candidat et le recadrage (`data/builds/<semaine>/<mode>/_crops/…png`, non publié). Elles ne comptent pas comme trouvées.

### 1.3 Écran de composition (v2)

L'écran de composition (`編成` en JA, titre de mode `プレイヤーモード` / `플레이어 모드` / `ハンターモード`) est le même pour tous les modes vus. Les **onglets** sont les icônes de la colonne verticale à gauche. Chaque onglet change le contenu des colonnes des personnages ; **ombres** (`影の権能`, 01 en grand, 02 et 03 en bandeau) et **successeur** (`残影の力`, niveau et puissance) restent visibles à droite sur tous les onglets.

| Onglet (clé config) | Contenu par personnage | BOT (vu) | POC | HOTM avec SJW | HOTM sans SJW | GB |
| --- | --- | --- | --- | --- | --- | --- |
| 1 `personnages` | Carte du personnage (illustration pleine carte, élément, SSR, niveau, puissance) ; armes : SJW 2 cartes, chasseur 1 carte | oui | oui (doc) | oui (doc) | oui (doc) | [EN ATTENTE] |
| 2 `artefacts` | 8 pièces (grille 2 × 4) ; pastilles de chiffre au-dessus des 2 colonnes | oui | oui (doc) | oui (doc) | oui (doc) | [EN ATTENTE] |
| 3 `competences` | SJW : 6 icônes ; chasseur : 8 icônes hexagonales (1re = « i ») | oui | oui (doc) | oui (doc) | oui (doc) | [EN ATTENTE] |
| 4 `benedictions` | SJW : 8 icônes `+n` | oui | oui (doc) | oui (doc) | **absent** | [EN ATTENTE] |
| 5 `noyaux` | 3 noyaux (haut → bas : `mind`, `body`, `spirit`) | oui | oui (doc) | oui (doc) | oui (doc) | [EN ATTENTE] |

- « oui (doc) » = mêmes onglets d'après `REFERENCE_ECRANS_POC.md` et `REFERENCE_ECRANS_HOTM.md`, **zones à calibrer** sur des captures du mode (§5, point 1). Les clés d'onglet sont les mêmes dans tous les modes ; `config.onglets.<mode>` = cette liste (remplace les listes par personnage de la v1).
- **HOTM sans SJW** : 4 onglets, sans `benedictions`, et pas de colonne SJW ; les 3 chasseurs se décalent vers la gauche. Ordre supposé personnages, artefacts, compétences, noyaux **[À CONFIRMER]**. Config : `config.onglets.hotm_sans_sjw` et `zones.hotm_sans_sjw…` (clé de mode distincte de `hotm`, car les colonnes ne sont pas au même endroit).
- **Fenêtres hors onglets** (facultatives) : POC `토벌 정비` → soutien de subjugation ; HOTM `증명 설정` → preuve d'entraînement. Clés d'onglet `subjugation` et `proof`.
- **GB** : écran non vu (Team A / Team B, 6 chasseurs). Aucune zone, statut selon §2.2 et §5.
- **Propriétaires** (`zones.<mode>.<onglet>.<propriétaire>.<élément>`, structure de la discussion 8 confirmée) : `sjw`, `hunter_1` à `hunter_3` (GB : `hunter_a1` … `hunter_b3`), `shadows`, `successor`. Ombres et successeur : lus sur chaque onglet, vote entre onglets (§2.1).
- **Artefacts, ordre des 8 tuiles** (lu sur la capture BOT, chasseur 1 et SJW) : colonne gauche = armure, colonne droite = accessoires.

| Ligne | Colonne gauche | Colonne droite |
| --- | --- | --- |
| 1 | `helmet` | `necklace` |
| 2 | `chestplate` | `bracelet` |
| 3 | `gloves` | `ring` |
| 4 | `boots` | `earrings` |

  Chaque tuile porte un cadre jaune, `+20`, un cadenas et `Lv.120` en bas : ces zones sont masquées pour la comparaison (§2.1). Pastilles `1` / `2` au-dessus des colonnes : sens non interprété, non lues.
- **Compétences de SJW, 6 icônes en 2 colonnes** sur l'illustration de SJW (capture HOTM du 13/11 avec les libellés SKILL / ULTIMATE / QTE, et capture BOT : même disposition) :

| Position | Colonne gauche (sur le corps) | Colonne droite (grandes icônes) |
| --- | --- | --- |
| haut | `ultimate` | `qte_3` |
| milieu | `skill_2` | `qte_2` |
| bas | `skill_1` | `qte_1` (pas de niveau affiché) |

  Les « 3 grandes icônes à droite » vues par la discussion 8 sont donc les QTE ; les 3 compétences sont à gauche, en partie sur l'illustration. Niveau `+n` lu à côté de chaque icône (`level: null` si absent).
- **Bénédictions** : 8 icônes `+n` sur SJW, ordre de lecture haut → bas, gauche → droite ; l'ordre n'a pas de sens de jeu (liste non ordonnée dans le JSON).

### 1.4 Écrans hors composition (v3)

Ces écrans s'ouvrent depuis le jeu (fiche d'un personnage, menus du mode). Ils ne sont filmés que par certains joueurs : tout ce qu'ils donnent est **facultatif** (jamais compté dans le statut), sauf quand ils confirment un élément attendu déjà cherché sur la composition (voir « Fiche de SJW »). Chaque écran est reconnu par ses libellés (`config.ecrans.<ecran>.libelles.<langue>`, au moins 2 libellés lus), comme les écrans de l'étape 1.

| Écran (clé config) | Libellés JA (vus) | Contenu lu | Va dans |
| --- | --- | --- | --- |
| `fiche_sjw` | nom du joueur (ex. `水篠旬`), `SKILL 01`, `SKILL 02`, `ULTIMATE SKILL`, `QTE 01`-`03`, `筋力`, `活力`, `速度`, `知能`, `感覚` | attributs (5) ; 6 compétences **avec leur libellé** et `+n` ; 8 bénédictions (2 lignes de 4) ; 2 armes avec **nom écrit**, niveau et étoiles | `sjw.stats` (attributs), `sjw.skills`, `sjw.blessings`, `sjw.weapons` |
| `stats` | `能力値情報`, `全体`, `武器`, `アーティファクト`, libellés des 10 stats | onglet `全体` seulement : 10 stats au format `88.32% (28905)` ; **nom du personnage écrit** sur sa carte (ex. `クリストファー・リード`) | `stats` du propriétaire (SJW, chasseur ou successeur, trouvé par le nom) |
| `statues` | `彫像` | 5 statues : grade (ex. D, E, C, B, B), 3 options chacune avec texte et grade E à S | `statues` |
| `gemmes` | `宝石情報` | 5 couleurs avec niveau ; bonus totaux (ATQ %, PV %, DEF %, pénétration, mana) | `gems` |
| `subjugation` | `討伐支援` (KR `토벌 지원`) | 9 choix en 3 colonnes ; on garde le choix sélectionné de chaque colonne (1/1) | `subjugation_support` (3 `id`) |

- **Correspondance des stats (libellés JA lus)** : `HP` → `hp`, `魔力` → `mana`, `攻撃力` → `attack`, `精密度` → `accuracy`, `防御力` → `defense`, `クリティカル率` → `crit-rate`, `クリティカルダメージ` → `crit-damage`, `クールタイム短縮` → `cooldown-reduction`, `防御力貫通` → `defense-penetration`, `ダメージ増加` → `damage-increase`. Attributs (fiche de SJW) : `筋力` → `strength`, `活力` → `vitality`, `速度` → `agility`, `知能` → `intelligence`, `感覚` → `perception`. Libellés KR : `REFERENCE_ECRANS_STATS.md`. Autres langues **[EN ATTENTE]**. Table dans `config.ecrans.stats.libelles`.
- **Rattachement au build** : un écran hors composition appartient à la run dont la composition le précède ou le suit dans la même vidéo, sans autre écran RESULT entre eux. Vidéo à 2 runs (POC) : si le rattachement est ambigu, l'écran est rattaché aux deux builds avec la note `écran commun aux 2 runs : <ecran>`.
- **Stats d'un chasseur** : le nom lu donne l'`id`. Si ce chasseur est déjà dans `hunters` (reconnu sur la composition), ses stats y vont. S'il n'y est pas, il est ajouté avec `position: null` (place sur la composition inconnue), note `chasseur trouvé par l'écran de stats`, et compte comme chasseur trouvé. Nom non reconnu : stats gardées dans `unmatched` (`element: stats`, `text_read`).
- **Fiche de SJW et composition** : les compétences lues sur la fiche portent leur libellé ; elles **priment** sur la position déduite de la composition (§1.3). Même règle pour les armes et les bénédictions : deux sources concordantes renforcent le vote, deux sources en désaccord → `confidence: a_verifier`, note `fiche/composition en désaccord : <élément>`.
- **Écrans de statues et de gemmes des autres langues** : **[EN ATTENTE]** de captures.

## 2. Statuts

### 2.1 Élément trouvé (v2 : banque actuelle seulement, décision d'Alexis du 14/11/2026)
On compare avec les icônes actuelles de `data/icons/` (pas de banque de variantes vues en jeu). Pour limiter les erreurs :
- **Masque** : dans chaque tuile, on ignore les zones de surimpression du jeu (cadre, fond de rareté, `+20`, `Lv.120`, cadenas, pastille d'élément). Zones de masque en fractions de la tuile dans `config.masques.<categorie>` **[À CONFIRMER]**.
- **Candidats réduits** : une tuile n'est comparée qu'aux icônes de sa catégorie **et de son emplacement** (pièce `helmet` → les 40 icônes `*--helmet.png` ; noyau `mind` → noyaux `slot: mind` ; compétence `qte_n` → `sjw_skills` de type QTE si la base le précise ; arme de chasseur → armes `hunter_id` = ce chasseur d'abord).
- **Seuils par catégorie** : `config.seuil_icone.<categorie>` (défaut 0,55, calibré sur les noyaux) et `config.ecart_icone` = 0,05 avec le 2e candidat. Sous le seuil → `unmatched`.
- **Bande de doute** : un résultat entre le seuil et `config.seuil_sur.<categorie>` (défaut seuil + 0,10) est gardé, mais le build passe en `confidence: a_verifier`, note `reconnaissance faible : <élément>`.
- **Vote** : un emplacement lu sur plusieurs images (même onglet à plusieurs instants, ou ombres/successeur sur plusieurs onglets) → vote majoritaire ; égalité → `null` + note `conflit : <élément>`. Pièces d'artefact : un set est en général porté par 2, 4 ou 8 pièces ; une pièce isolée d'un set différent de ses voisines garde sa valeur mais ajoute la note `pièce isolée : <slot>`.
- **Reconnaissance par le nom écrit (v3, prioritaire)** : quand un nom est écrit à l'écran (armes de la fiche de SJW, nom du personnage sur l'écran de stats ou sur sa fiche), on le lit par OCR et on le compare aux noms de la base (`name.ja`, `name.ko`, `name.en`, `name.fr`). Comparaison après normalisation (NFKC, sans espaces, sans `・`, `·`, casse ignorée) : égalité exacte → trouvé (`found_by: name`) ; ressemblance ≥ `config.seuil_nom` = 0,90 **[À CONFIRMER]** et un seul candidat → trouvé, note `nom approché : <lu>` ; sinon `unmatched` avec le texte lu. Le nom prime sur l'icône ; s'ils diffèrent → `a_verifier`, note `nom/icône en désaccord`. Nécessite `name.ja` et `name.ko` dans la base (§5, point 15).
- **Cartes de référence (v5, prioritaires)** : `data/icons/hunters_cartes/<id>.png` et `data/icons/shadows_cartes/<id>.png` = carte recadrée telle qu'affichée sur l'onglet `personnages`, identité tirée de la base. Comparaison SIFT + RANSAC (déjà codée) ; seuils `portraits.min_corr` / `min_corr_ombres` (25) **[À CONFIRMER]**. La carte l'emporte sur l'icône (note `<élément> reconnu par sa carte, icône lue : <id>`). Ordre de priorité : nom écrit > carte > icône. Une carte ne remplace pas la banque : elle est fournie par la discussion 9 (à partir de slagate.com ou d'images extraites des vidéos, identité vérifiée par le nom écrit ou une source citée), jamais déduite par le pipeline seul.
- **Icônes non reconnues** : sans nom ni carte, l'élément reste `unmatched` (portraits, armes, successeur). Le rapport liste les recadrages non reconnus par catégorie pour que la discussion 9 ajoute les cartes manquantes.
- **Chasseurs** : la banque contient des portraits, l'écran montre l'illustration pleine carte. On compare la zone du visage (haut de la carte, `config.zones.<mode>.personnages.<propriétaire>.hunter_face`). Si cela ne passe pas le seuil → `unmatched` (pas de déduction par l'arme ou l'élément).
- Icône absente de la banque (`icon: null` dans la base) : l'objet ne peut pas être reconnu. Note `icône absente : <categorie>`.

### 2.2 Calcul du statut
1. On établit la liste des éléments **attendus** (§1.1), sans les facultatifs.
2. **`build_complet`** : tous les éléments attendus valent `found: true`, sans conflit, et tous les `id` existent dans la base.
3. **`build_partiel`** : au moins un élément (même partiel, `counts` > 0) est trouvé, mais pas tous.
4. **`pas_de_build`** : aucun élément trouvé après le tri 4, ou vidéo illisible (supprimée, privée, bloquée), ou écran de composition jamais vu dans la vidéo (note `composition non filmée`). Note : la raison.
5. **Plafonds à `build_partiel`** (même si tout le reste est trouvé), avec la note entre parenthèses :
   - règles du mode inconnues, bloc `null` (`règles <mode> inconnues`). Ombres, successeur et SJW sont alors traités comme facultatifs ;
   - HOTM avec `hunter_mode` à `null` après déduction (`hunter_mode inconnu`). SJW est traité comme facultatif ;
   - vidéo pas encore passée au tri 4 (`analyse en cours`).
6. **Jamais de `pas_de_build` à cause de l'absence de SJW** quand il n'est pas attendu. HOTM avec `hunter_mode: true` : `"sjw": null`, clés `sjw*` et `blessings` à `null` ; les 3 chasseurs complets suffisent pour `build_complet`.

### 2.3 Confiance et alertes
- `confidence: a_verifier` dans les cas suivants, avec la note entre parenthèses ; le statut n'est pas modifié :
  - élément interdit par les règles mais détecté (`élément interdit détecté : <élément>`) — **seulement si la règle vaut `false`** ; `null` = inconnu, jamais interdit (v5, `data/rules` déduit des écrans, SPEC_ETAPE1 v24 §4.5) ;
  - (v5) POC et GB : deux builds de la même ligne (2 groupes ou 2 équipes) qui ont un chasseur en commun (`chasseur commun aux 2 runs : <id>`) — le jeu l'interdit, c'est donc une erreur de rattachement ou de lecture ;
  - (v5) `element` du build différent de l'élément majoritaire des chasseurs reconnus (`élément de la run incohérent`).
  - HOTM `hunter_mode: true` mais SJW vu (`SJW vu en mode sans SJW`) ;
  - chasseur en double dans l'équipe (`doublon : <id>`) ;
  - arme exclusive portée par un autre chasseur que le sien (`weapons.hunter_id` ≠ `id`, `arme d'un autre chasseur`).
- Sinon : `sur`.

## 3. PowerPoint

### 3.1 Fichiers
- **Un PowerPoint par vidéo du top 10 et par langue** (CONTEXTE : un PowerPoint par vidéo ; FR + EN partout) : `exports/<semaine>/builds/<mode>/<rang:02>-<video_id>-fr.pptx` et `…-en.pptx`.
- Une vidéo qui porte 2 runs (POC, GB) donne un seul fichier contenant les 2 builds. Une ligne POC/GB faite de 2 vidéos donne 2 fichiers.
- Généré par `pipeline/export_pptx.py [semaine] [--mode] [--sortie]`, avec python-pptx. Lancé après le calcul des builds, au passage quotidien et au gel. Les fichiers sont réécrits à chaque passage.
- Semaine d'essai (`2026-11-12`) : bandeau rouge `ESSAI — non publié` sur la slide de titre, comme dans l'Excel.

### 3.2 Slides (dans l'ordre)
Pour chaque build du fichier :

| # | Slide | Contenu |
| --- | --- | --- |
| 1 | Titre du build | Mode + nom complet ; semaine ; rang (pastille or/argent/bronze pour 1-3) ; joueur ; score (même format que l'Excel) ; run n/2 et équipe/groupe (POC/GB) ; porte et « avec SJW / sans SJW » (HOTM) ; badge de statut ; lien vers la vidéo à `t_composition` |
| 2 | Sung Jin Woo | 2 armes, 8 pièces d'artefact (grille 4 × 2) + bonus de sets, 3 noyaux, tableau des stats |
| 3-5 | Chasseur 1, 2, 3 (GB : 6 slides, A1 à B3) | Portrait + nom + élément + rôle ; arme ; 8 pièces + bonus de sets ; 3 noyaux ; tableau des stats |
| 6 | Ombres | 3 icônes + noms, positions 01 à 03 |
| 7 | Successeur | Icône + nom (+ niveau s'il est lu) ; tableau des stats s'il est lu (v3) |
| 8 | Compétences de SJW | Grille 3 + 3 (`sjw.GRILLE_SLIDE`) : compétences en haut, QTE en bas, niveau `+n` |
| 9 | Bénédictions | Grille 4 × 2, niveau `+n` |
| 10 | Soutien de subjugation (POC) / Preuve d'entraînement (HOTM) | Seulement si trouvé. POC : 3 colonnes, choix sélectionné mis en avant. HOTM : niveau de preuve + tableau des handicaps (nom, niveau choisi / max, coût) |
| 11 | Statues (v3) | Seulement si trouvé. 5 cartes (grade en grand) ; sous chacune, 3 options : grade + texte. Texte de la base s'il existe, sinon texte lu en italique avec la marque `(JA)` / `(KO)` |
| 12 | Gemmes (v3) | Seulement si trouvé. 5 pastilles de couleur avec niveau ; tableau des bonus totaux (stat, valeur) |

Puis, une seule fois en fin de fichier : **Sources** (voir §3.4).

- Élément « sans objet » (« — » en §1.1) → pas de slide. Élément attendu mais non trouvé → la slide existe avec des cases « Non trouvé ».
- **Nombre de slides par build** (hors slide Sources) :

| Mode | Slides | Détail |
| --- | --- | --- |
| BOT | 9 à 11 | titre + SJW + 3 chasseurs + ombres + successeur + compétences + bénédictions, + statues et gemmes si trouvées |
| POC | 9 à 12 | idem, + subjugation, statues et gemmes si trouvées |
| HOTM avec SJW | 9 à 12 | idem, + preuve, statues et gemmes si trouvées |
| HOTM sans SJW | 6 à 9 | titre + 3 chasseurs + ombres + successeur, + preuve, statues et gemmes si trouvées |
| GB | 12 | titre + SJW + 6 chasseurs + ombres + successeur + compétences + bénédictions, si les règles GB les permettent ([EN ATTENTE]) |

### 3.3 Mise en page (16:9, 13,333 × 7,5 pouces)
- **Charte = celle de l'Excel** : importer les constantes de `export_excel.py`, ne pas les recopier.
  - Fond : `NUIT` 0B0E1A. Panneaux : `PANNEAU` 121830 / `PANNEAU2` 181F3D. En-tête : `ENTETE` 1E1B4B. Texte : `TEXTE` E5E9F5. Texte secondaire : `SOURD` 7F88A8.
  - Couleur du mode : POC EF4444, BOT `BLEU` 38BDF8, GB `OR` F5C542, HOTM `VIOLET` 7C3AED.
  - Statut : complet `VERT`, partiel `AMBRE`, pas de build `ROUGE`. Podium : `OR` / `ARGENT` / `BRONZE`.
  - Police : Segoe UI.
- **Bandeau haut** (0 à 0,9 in) :
  - fond `ENTETE`, liseré de 0,06 in à la couleur du mode ;
  - à gauche, `POC · #1 · <joueur>` (14 pt, `TEXTE`) ; à droite, `Semaine du 12/11/2026` / `Week of 2026-11-12` (12 pt, `SOURD`) ;
  - titre de la slide à 1,0 in : 28 pt, gras, `BLEU`.
- **Contenu** (1,7 à 6,6 in) :
  - icônes en carrés de 1,1 in sur panneau arrondi, nom sous l'icône (12 pt, 2 lignes au plus) ;
  - niveaux en pastille (`+5`, `Lv 25`) ;
  - tableau des stats en 2 colonnes (stats | attributs), valeurs comme à l'écran (`50 % (19 191)`).
- **Pied** (6,9 à 7,5 in) :
  - à gauche, la source (11 pt, `SOURD`) : `Vidéo : <chaîne> — youtu.be/<id>?t=<t>` ;
  - à droite : `Shadow Ledger · shadowledgerhq.github.io · @shadowledger_hq`.
- **Cases d'état** (bordure pointillée `SOURD`) :
  - « Non trouvé dans la vidéo » / « Not found in the video » ;
  - « Non géré pour l'instant » / « Not supported yet » (éléments [EN ATTENTE]) ;
  - « Icône inconnue » / « Unknown icon » (`unmatched`).
- **Noms** : `name.fr` dans le fichier FR, `name.en` dans le fichier EN.
  - Si `name.fr` est vide, on affiche `name.en` en italique avec la marque `(EN)`. Si les deux sont vides, on affiche l'`id` en italique.
  - Jamais de traduction faite par le code ou par Claude.
- **Libellés fixes** (titres de slides, cases, pied) : dictionnaire FR/EN dans `config.libelles`. Exemples : « Ombres / Shadows », « Successeur / Successor », « Bénédictions / Blessings », « Compétences de Sung Jin Woo / Sung Jin Woo's Skills », « Noyaux / Cores », « Artefacts / Artifacts ».
- **Visuels** : seulement les icônes de `data/icons/` (crédits dans `CREDITS.md`) et des formes simples. Aucune capture de joueur, aucun visuel officiel hors fan kit.
- **Notes de l'orateur** de chaque slide, en FR dans les deux fichiers (usage interne) : horodatages `t`, scores de correspondance, `unmatched`, notes du build.

### 3.4 Slide « Sources » (dernière slide)
- Vidéo : titre, chaîne, lien, date de publication, horodatages utilisés.
- Données du jeu : `data/db` (Shadow Ledger), sources de la base : slagate.com (autorisation de Sohoven), wiki Fandom (CC BY-SA), forum Netmarble ; version du jeu (`patches.json`, dernière version).
- Crédits des icônes : contenu de `data/icons/CREDITS.md`, résumé.
- Mention : « Build relevé automatiquement à partir de la vidéo ; éléments non trouvés signalés. » / « Build read automatically from the video; missing elements are flagged. »
- Date de génération, `spec` = 5.

## 4. Origine des données

| Donnée | Source | Qui la remplit |
| --- | --- | --- |
| Top 10, `video_id`, `t`, équipe/groupe, `gate`, `hunter_mode` | `data/runs/` (étape 1) | Pipeline étape 1 (discussions 1 et 8) |
| Éléments autorisés par mode et par semaine | `data/rules/<semaine>.json` | Alexis via la discussion 2 (POC, BOT, HOTM) et la discussion 1 |
| Identité des objets du build (persos, armes, pièces, noyaux, ombres, successeur, compétences, bénédictions, subjugation, handicaps) | Images de la vidéo (tris 2 à 4, écran de composition), comparées à la banque d'icônes | Pipeline étape 2 (discussion 8) |
| Niveaux, stats, niveau de preuve, grades des statues, niveaux et bonus des gemmes | OCR des chiffres et lettres sur les images | Pipeline étape 2 (discussion 8) |
| Noms écrits (armes, personnages) | OCR, comparés aux noms de la base | Pipeline étape 2 (discussion 8) ; noms JA/KO : discussion 9 |
| Noms FR/EN/KO, rareté, élément, rôle, effets, paliers de set, coûts des handicaps | `data/db/*.json` (slagate.com, routes GET publiques autorisées ; wiki Fandom ; forum Netmarble) | Discussion 9 (Base de données) |
| Icônes | `data/icons/` | Discussion 9 |
| Bonus de sets actifs, contrôle de la preuve | Calculés | Pipeline étape 2 |
| Mise en page, libellés FR/EN | Cette spec + `config.libelles` | Discussion 8 |
| Contrôle des builds produits | Checklist du skill + §6 | Discussion 2 |

Le tri 1 (texte) **ne remplit aucun élément** en v1 : une description qui liste un build n'est pas vérifiable à l'image. On la garde dans `notes` comme indice.

## 5. [EN ATTENTE] — à coder en « non géré » propre

| # | Manque | Ce que le code fait en attendant | Qui débloque |
| --- | --- | --- | --- |
| 1 | **Zones des onglets** : BOT et POC/personnages calibrés ; POC (onglets 2-5), HOTM avec et sans SJW, GB à calibrer | Zones absentes → note `zones <mode>/<onglet> non définies` | **v5 : plus de captures demandées à Alexis** (règle « Autonomie »). Le pipeline enregistre les images de composition extraites des vidéos du top 10 dans `docs/essais/composition/auto/<mode>/<video_id>_<onglet>_<t>.png` (1 par onglet, meilleure résolution) ; la discussion 2 y définit les zones, la discussion 8 les code. |
| 2 | **Seuils et masques par catégorie** | `seuil_icone.<categorie>` 0,55, `seuil_sur` +0,10, `ecart_icone` 0,05, `masques` [À CONFIRMER] | Essai sur les captures BOT puis 3 vidéos ; résultats à la discussion 2 |
| 3 | **Règles POC et GB** (`modes.poc` et `modes.gb` à `null`) | SJW, ombres, successeur traités comme facultatifs ; statut plafonné `build_partiel`, note `règles <mode> inconnues` | Alexis |
| 4 | **Écrans de composition GB** (Team A/B, 6 chasseurs, SJW ?) : non décrits | Mode `gb` reconnu, aucun élément cherché, note `composition GB non décrite`, `pas_de_build` | Images extraites des vidéos GB du classement (`auto/gb/`, ci-dessus), puis discussion 2 |
| 5 | **Icônes absentes de la banque** (196 `icon: null` au 14/11, surtout armes ; **pas de dossier `successors/`**) | L'objet ne peut pas être reconnu : `unmatched`, note `icône absente : <categorie>` | Discussion 9 (demande envoyée par la discussion 2) |
| 6 | **Stats** : écran de stats rarement filmé | **Réglé (v2)** : facultatives, `stats_obligatoires = false`. Zones de l'écran de stats non calibrées → non lues, case « Non trouvé » | Une capture de l'écran de stats en 1080p suffira plus tard |
| 7 | **Compétences des chasseurs** (8 icônes chacun) | **Réglé (v2)** : hors build pour l'instant (« plus tard ») ; non cherchées, pas de slide | — |
| 8 | **Stats des pièces d'artefact, sens des pastilles `1`/`2` au-dessus des colonnes d'artefacts** | Non lues | Captures + discussion 2 |
| 9 | **Libellés et onglets des clients autres que KR/JP** (EN, PT…) pour reconnaître l'écran de composition | Reconnaissance par la disposition (icônes) et non par le texte ; si impossible, note `composition <langue> non reconnue` | Captures |
| 10 | **Niveaux** (arme `+100`, étoiles, niveau du successeur) | `level: null` si non lu ; jamais requis pour le statut | — |
| 11 | **Logo Shadow Ledger** | Mot « SHADOW LEDGER » en texte (Segoe UI, gras, `BLEU`) | Discussion 4 |
| 12 | **Noms FR manquants** (170 au 14/11) | Nom EN en italique + `(EN)` | Discussion 9 |
| 13 | **Ombres 02 et 03** : seule une bande de l'illustration est visible | Comparer la bande à la zone correspondante de l'icône ; sous le seuil → `unmatched` | Essai |
| 14 | **Type des compétences de SJW** (skill / ultimate / QTE) dans `sjw_skills.json` (champ `type` vide) | Candidats = toutes les compétences de SJW | Discussion 9 |
| 15 | **Noms JA et KO dans la base** (chasseurs, armes, successeurs, ombres) pour la reconnaissance par le nom | Comparaison avec les noms présents seulement (EN/FR) ; sans nom JA/KO, le nom lu reste `unmatched` | Discussion 9 |
| 16 | **Statues** : catégorie absente de la base (options, grades, effets) | Grades lus, texte lu gardé tel quel, `id: null` | Discussion 9 (catégorie `statues`) + captures |
| 17 | **Gemmes** : noms des 5 couleurs et effets | `color: null`, niveaux et bonus lus | Discussion 9 (catégorie `gems`) |
| 18 | **Statues et gemmes : modes concernés** | **Réglé (15/11)** : tous les modes (Alexis) | — |

## 6. Contrôles (discussion 2)

À chaque passage, le rapport `data/builds/<semaine>/_rapport.md` donne, par mode :
- le nombre de builds par statut ;
- la liste des `a_verifier` ;
- les `unmatched` par catégorie ;
- les éléments interdits détectés ;
- les `id` introuvables (erreur) ;
- les fichiers PowerPoint produits.

Checklist de la discussion 2 :
- [ ] Un build par run du top 10 (×2 runs pour POC et GB) ou la raison de l'absence.
- [ ] Chaque `id` existe dans la base.
- [ ] `status` cohérent avec `found` et les plafonds (§2.2).
- [ ] HOTM : `sjw` à `null` si `hunter_mode: true` ; aucun `build_partiel` dû à la seule absence de SJW.
- [ ] Aucun élément interdit par les règles.
- [ ] Un PowerPoint par vidéo et par langue ; nombre de slides conforme au §3.2.
- [ ] Noms FR/EN conformes (aucun nom inventé).

## 7. Tests demandés

1. HOTM `hunter_mode: true`, 3 chasseurs complets → `build_complet`, `sjw: null`, 7 slides par fichier (6 pour le build + Sources).
2. HOTM `hunter_mode: false`, SJW absent → `build_partiel`.
3. HOTM `hunter_mode: true` et SJW vu → `confidence: a_verifier`.
4. HOTM `hunter_mode: null` non déduit → plafond `build_partiel`.
5. POC avec règles `null` et tout trouvé → `build_partiel` (`règles poc inconnues`).
6. Aucun élément → `pas_de_build` avec raison.
7. Vidéo à 2 runs → 1 fichier, 2 builds, slide Sources unique.
8. `name.fr` vide → nom EN en italique + `(EN)` dans le fichier FR.
9. Élément `unmatched` → case « Icône inconnue », non compté.
10. (v2) Build BOT sans aucune stat, tout le reste trouvé → `build_complet`.
11. (v2) Captures BOT `docs/essais/composition/` : noyaux des 4 personnages reconnus ; positions des 8 pièces conformes au tableau du §1.3 ; 6 compétences de SJW rattachées aux bons emplacements (`qte_1` sans niveau).
12. (v2) Score entre le seuil et `seuil_sur` → élément gardé, `confidence: a_verifier`, note `reconnaissance faible`.
13. (v2) HOTM sans SJW : `config.onglets.hotm_sans_sjw` sans `benedictions` ; aucun recadrage SJW.
14. (v3) `poc_stats_chasseur_1_ja.png` : écran `stats` reconnu, nom `クリストファー・リード` lu, 10 stats lues (`accuracy` = 88.32 % / 28905, `cooldown-reduction` = 0 % / 0), rattachées au bon chasseur si `name.ja` existe, sinon `unmatched` + stats gardées sous `unmatched`.
15. (v3) `poc_sjw_ja.png` : fiche de SJW reconnue ; 6 compétences rattachées par leur libellé ; attributs `strength` 19, `vitality` 10, `agility` 10, `intelligence` 1335, `perception` 10 ; 2 noms d'armes lus.
16. (v3) Build sans statues ni gemmes → aucune slide 11-12, statut inchangé.
17. (v3) Nom et icône en désaccord → `confidence: a_verifier`.
18. (v4) Semaine 2026-11-12, BOT sans ligne classée → builds pour les 9 lignes `a_verifier` (wJ9CwjKwyco en `provisional_rank` 1), `line_provisional: true`, bandeau dans le PowerPoint. GB (lignes classées) inchangé.
19. (v5) Carte de référence et icône en désaccord → la carte l'emporte, note. Aucune carte ni nom → `unmatched`.
20. (v5) Règle `null` + élément vu → pas d'alerte « interdit » ; règle `false` + élément vu → `a_verifier`.
21. (v5) Deux runs GB d'une même ligne avec un chasseur commun → `a_verifier` sur les deux builds.
22. (v5) `element` repris de `runs_detail[i].element` (`null` si absent).
