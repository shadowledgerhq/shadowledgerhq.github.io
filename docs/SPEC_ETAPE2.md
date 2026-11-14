# Spécification — Étape 2 : builds du top 10 et PowerPoint

Version 1 — 14/11/2026 — discussion 2 (Builds). Destinataire : discussion 8 (Code). À déposer dans `docs/SPEC_ETAPE2.md`.
Références : `docs/CONTEXTE.md` §4 (étape 2), `docs/SPEC_ETAPE1.md`, `docs/REFERENCE_ECRANS_*.md`, `data/db/_schema.md`, `data/rules/<semaine>.json`, `pipeline/sjw.py`, `pipeline/hotm_ecran.py`, `pipeline/export_excel.py`.
Marqueurs (mêmes sens qu'à l'étape 1) : **[À CONFIRMER]** = hypothèse codée en paramètre dans `pipeline/config/etape2.json` ; **[EN ATTENTE]** = info manquante, à coder en « non géré » propre (élément `null` + note, jamais une valeur inventée).

---

## 0. Principes

- **Builds analysés** : les lignes `rank` 1 à 10 (`confidence: sur`) de `data/runs/<semaine>/<mode>.json` (`poc`, `bot`, `gb`, `hotm-gate-<n>`). Une ligne `rank: null` n'a pas de build.
- **Un build = une run** : un objet de `runs_detail[i]` donne un build `<run_id>-<i+1>.json`. POC et GB : 2 runs = 2 builds, éventuellement dans 2 vidéos différentes.
- **Où chercher** : dans la vidéo `runs_detail[i].video_id`, l'écran de composition (onglets) **avant** l'écran RESULT de la run (`t`). Si la vidéo contient 2 runs, on prend la composition située entre le RESULT précédent et celui de la run.
- **Reconnaissance** : par icône (OpenCV, comparaison avec `data/icons/<categorie>/`). Aucun nom n'est lu à l'écran, sauf le pseudo et les chiffres (niveaux, stats).
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
| Stats de SJW | 10 + 5 | règle | règle | règle | oui | — |
| Compétences de SJW | 6 emplacements | règle | règle | règle | oui | — |
| Bénédictions | 8 | règle | règle | règle | oui | — |
| Chasseurs | 3 (GB : 6) | oui | oui | oui (A1-3, B1-3) | oui | oui |
| Arme de chaque chasseur | 1 par chasseur | oui | oui | oui | oui | oui |
| Artefacts | 8 pièces par chasseur | oui | oui | oui | oui | oui |
| Noyaux | 3 par chasseur | oui | oui | oui | oui | oui |
| Stats | 10 + 5 par chasseur | oui | oui | oui | oui | oui |
| Ombres | 3 | règle | règle | règle | oui | oui |
| Successeur | 1 | règle | règle | règle | oui | oui |
| Soutien de subjugation | 3 choix (1 par colonne) | fac. | — | — | — | — |
| Preuve d'entraînement | niveau + handicaps | — | — | — | fac. | fac. |

- **Règles de la semaine** : SJW, compétences et bénédictions sont attendus si `rules.<mode>.sjw` (et `sjw_skills`, `blessings`) valent `true`. Ombres : `shadows`. Successeur : `successor`. Bloc du mode `null` → **[EN ATTENTE]** (§5). Pour le BOT, lire `modes.bot`, sinon `modes.bot_season` (le fichier du 12/11 garde l'ancien découpage).
- **HOTM** : `hunter_mode` vient de la run, c'est le booléen déjà codé par `hotm_ecran.py`. `false` = avec SJW, `true` = sans SJW, `null` = inconnu. On ne cherche SJW que si `rules.hotm.sjw == true` **et** `hunter_mode == false`.
  - Si `hunter_mode` vaut `null`, on le déduit de la composition : 4 onglets sans bénédictions → `true` ; 5 onglets, ou un personnage à gauche des 3 chasseurs → `false`. Note : `hunter_mode déduit`. Sinon il reste `null` (§2.2).
- **Stats** : les 15 lignes `required: true` de `data/db/stats.json`, soit 10 stats et 5 attributs. La puissance de combat est facultative (info). Elles sont lisibles seulement si l'écran de stats du personnage est filmé (`REFERENCE_ECRANS_STATS.md`). Leur caractère obligatoire est un paramètre : `config.stats_obligatoires = true` **[À CONFIRMER]** (§5, point 6).
- **Hors build pour l'instant** : les 8 icônes de compétences de chaque chasseur, les stats principales et secondaires des pièces d'artefact, et le sens des pastilles de set. Voir §5.

### 1.2 Format JSON — `data/builds/<semaine>/<mode>/<run_id>-<n>.json`
Ce format remplace l'exemple du skill §3 (« Build »). Pour le HOTM, `<mode>` = `hotm-gate-<n>`.

```json
{
  "spec": 1,
  "run_id": "poc-2026-11-12-XXXXXXXXXXX",
  "run_index": 1,
  "week": "2026-11-12",
  "mode": "poc",
  "gate": null,
  "hunter_mode": null,
  "rank": 1,
  "player": "nom de la chaîne",
  "channel_id": "UC…",
  "video_id": "XXXXXXXXXXX",
  "t_result": 183,
  "t_composition": [4, 12],
  "team": 1,
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
  "successor": {"id": "…", "level": null},
  "subjugation_support": null,
  "proof": null,
  "found": {"sjw": true, "sjw_weapons": true, "sjw_artifacts": false, "sjw_cores": true, "sjw_stats": false,
            "sjw_skills": true, "blessings": true, "hunters": true, "weapons": true, "artifacts": false,
            "cores": true, "stats": false, "shadows": true, "successor": true,
            "subjugation_support": null, "proof": null},
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
- **GB** : `hunters` contient 6 entrées, `team_slot` vaut `"A1"` à `"B3"`, et `team` = groupe 1/2 de la run (repris de l'étape 1).
- **`set_bonuses`** : calculé par le code à partir des 8 pièces (nombre de pièces par set), jamais lu. Les paliers d'effet (2/4/8) viennent de `artifact_sets.json`.
- **POC** : `subjugation_support` = liste de 3 `id` (colonnes 1 à 3) ou `null`.
- **HOTM** : `proof` = `{"level": 931, "modifiers": [{"id": "…", "level": 5}]}` ou `null`. Contrôle : somme des coûts = `level` ; sinon note `contrôle preuve`.
- **`found`** : `true` = complet ; `false` = attendu mais incomplet ; `null` = non attendu ou facultatif non trouvé. `counts` = nombre trouvé / nombre attendu pour les éléments multiples.
- **`unmatched`** : icônes vues mais non reconnues (score sous le seuil, §2.1). On garde le meilleur candidat et le recadrage (`data/builds/<semaine>/<mode>/_crops/…png`, non publié). Elles ne comptent pas comme trouvées.

## 2. Statuts

### 2.1 Élément trouvé
- Correspondance d'icône ≥ `config.seuil_icone` = 0,80 **[À CONFIRMER]** sur de vraies images, **et** écart ≥ `config.ecart_icone` = 0,05 avec le 2e candidat. Sinon → `unmatched`.
- Un même emplacement lu sur plusieurs images : on garde le vote majoritaire. En cas d'égalité → `null` + note `conflit : <élément>`.
- Icône absente de la banque (`icon: null` dans la base) : l'objet ne peut pas être reconnu. Note `icône absente : <categorie>`.

### 2.2 Calcul du statut
1. On établit la liste des éléments **attendus** (§1.1), sans les facultatifs.
2. **`build_complet`** : tous les éléments attendus valent `found: true`, sans conflit, et tous les `id` existent dans la base.
3. **`build_partiel`** : au moins un élément (même partiel, `counts` > 0) est trouvé, mais pas tous.
4. **`pas_de_build`** : aucun élément trouvé après le tri 4, ou vidéo illisible (supprimée, privée, bloquée). Note : la raison.
5. **Plafonds à `build_partiel`** (même si tout le reste est trouvé), avec la note entre parenthèses :
   - règles du mode inconnues, bloc `null` (`règles <mode> inconnues`). Ombres, successeur et SJW sont alors traités comme facultatifs ;
   - HOTM avec `hunter_mode` à `null` après déduction (`hunter_mode inconnu`). SJW est traité comme facultatif ;
   - vidéo pas encore passée au tri 4 (`analyse en cours`).
6. **Jamais de `pas_de_build` à cause de l'absence de SJW** quand il n'est pas attendu. HOTM avec `hunter_mode: true` : `"sjw": null`, clés `sjw*` et `blessings` à `null` ; les 3 chasseurs complets suffisent pour `build_complet`.

### 2.3 Confiance et alertes
- `confidence: a_verifier` dans les cas suivants, avec la note entre parenthèses ; le statut n'est pas modifié :
  - élément interdit par les règles mais détecté (`élément interdit détecté : <élément>`) ;
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
| 7 | Successeur | Icône + nom (+ niveau s'il est lu) |
| 8 | Compétences de SJW | Grille 3 + 3 (`sjw.GRILLE_SLIDE`) : compétences en haut, QTE en bas, niveau `+n` |
| 9 | Bénédictions | Grille 4 × 2, niveau `+n` |
| 10 | Soutien de subjugation (POC) / Preuve d'entraînement (HOTM) | Seulement si trouvé. POC : 3 colonnes. HOTM : niveau de preuve + tableau des handicaps (nom, niveau choisi / max, coût) |

Puis, une seule fois en fin de fichier : **Sources** (voir §3.4).

- Élément « sans objet » (« — » en §1.1) → pas de slide. Élément attendu mais non trouvé → la slide existe avec des cases « Non trouvé ».
- **Nombre de slides par build** (hors slide Sources) :

| Mode | Slides | Détail |
| --- | --- | --- |
| BOT | 9 | titre + SJW + 3 chasseurs + ombres + successeur + compétences + bénédictions |
| POC | 9 à 10 | idem, + la slide subjugation si elle est trouvée |
| HOTM avec SJW | 9 à 10 | idem, + la slide preuve si elle est trouvée |
| HOTM sans SJW | 6 à 7 | titre + 3 chasseurs + ombres + successeur, + la slide preuve si elle est trouvée |
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
- Date de génération, `spec` = 1.

## 4. Origine des données

| Donnée | Source | Qui la remplit |
| --- | --- | --- |
| Top 10, `video_id`, `t`, équipe/groupe, `gate`, `hunter_mode` | `data/runs/` (étape 1) | Pipeline étape 1 (discussions 1 et 8) |
| Éléments autorisés par mode et par semaine | `data/rules/<semaine>.json` | Alexis via la discussion 2 (POC, BOT, HOTM) et la discussion 1 |
| Identité des objets du build (persos, armes, pièces, noyaux, ombres, successeur, compétences, bénédictions, subjugation, handicaps) | Images de la vidéo (tris 2 à 4, écran de composition), comparées à la banque d'icônes | Pipeline étape 2 (discussion 8) |
| Niveaux, stats, niveau de preuve | OCR des chiffres sur les images | Pipeline étape 2 (discussion 8) |
| Noms FR/EN/KO, rareté, élément, rôle, effets, paliers de set, coûts des handicaps | `data/db/*.json` (slagate.com, routes GET publiques autorisées ; wiki Fandom ; forum Netmarble) | Discussion 9 (Base de données) |
| Icônes | `data/icons/` | Discussion 9 |
| Bonus de sets actifs, contrôle de la preuve | Calculés | Pipeline étape 2 |
| Mise en page, libellés FR/EN | Cette spec + `config.libelles` | Discussion 8 |
| Contrôle des builds produits | Checklist du skill + §6 | Discussion 2 |

Le tri 1 (texte) **ne remplit aucun élément** en v1 : une description qui liste un build n'est pas vérifiable à l'image. On la garde dans `notes` comme indice.

## 5. [EN ATTENTE] — à coder en « non géré » propre

| # | Manque | Ce que le code fait en attendant | Qui débloque |
| --- | --- | --- | --- |
| 1 | **Zones des onglets de composition** (coordonnées des icônes par onglet, 1080p) | Cadre de recadrage + comparaison codé, zones dans `config.zones.<mode>.<onglet>` en fractions, vides. Sans zone : aucun élément cherché, note `zones <mode>/<onglet> non définies`, statut `pas_de_build` (raison) | Alexis : 1 capture 1080p par onglet et par mode (BOT, POC, HOTM ×2, GB) |
| 2 | **Seuil de correspondance d'icône** | Paramètres `seuil_icone` 0,80 et `ecart_icone` 0,05 [À CONFIRMER] | Essai sur 3 vidéos (discussions 8 puis 2) |
| 3 | **Règles POC et GB** (`modes.poc` et `modes.gb` à `null`) | SJW, ombres, successeur traités comme facultatifs ; statut plafonné `build_partiel`, note `règles <mode> inconnues` | Alexis |
| 4 | **Écrans de composition GB** (Team A/B, 6 chasseurs, SJW ?) : non décrits | Mode `gb` reconnu, aucun élément cherché, note `composition GB non décrite`, `pas_de_build` | Alexis : captures |
| 5 | **Icônes absentes de la banque** (196 `icon: null` au 14/11, surtout armes ; pas de dossier `successors/`) | L'objet ne peut pas être reconnu : `unmatched`, note `icône absente : <categorie>` | Discussion 9 |
| 6 | **Stats** : écran de stats rarement filmé | Lues seulement si l'écran est vu. `config.stats_obligatoires = true` (CONTEXTE) [À CONFIRMER] ; si `false`, les stats deviennent facultatives | Alexis : décision |
| 7 | **Compétences des chasseurs** (8 icônes chacun) | Non cherchées, pas de slide | Alexis : décision |
| 8 | **Stats des pièces d'artefact, sens des pastilles de set** | Non lues | Captures + discussion 2 |
| 9 | **Libellés et onglets des clients autres que KR/JP** (EN, PT…) pour reconnaître l'écran de composition | Reconnaissance par la disposition (icônes) et non par le texte ; si impossible, note `composition <langue> non reconnue` | Captures |
| 10 | **Niveaux** (arme `+100`, étoiles, niveau du successeur) | `level: null` si non lu ; jamais requis pour le statut | — |
| 11 | **Logo Shadow Ledger** | Mot « SHADOW LEDGER » en texte (Segoe UI, gras, `BLEU`) | Discussion 4 |
| 12 | **Noms FR manquants** (170 au 14/11) | Nom EN en italique + `(EN)` | Discussion 9 |

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
