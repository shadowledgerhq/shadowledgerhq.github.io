# SPEC_SITE — Site Shadow Ledger (étape 5)

État actuel : **v2.1 — 2026-11-27** (discussion 5 — Site). Historique : `docs/archives/` quand il y aura une v2.

## 1. Principe

- Site statique, FR + EN, qui lit les JSON du dépôt (aucun serveur). Fichier : `site/index.html` (HTML + CSS + JS dans un seul fichier, sans dépendance).
- **Rien de public avant le lancement** (CONTEXTE §2) : GitHub Pages reste coupé ; `<meta name="robots" content="noindex, nofollow">` sur toutes les pages et `site/robots.txt` (`Disallow: /`), contrôlés par `pipeline/check_site.py`. Aperçu : `python -m http.server` à la racine du dépôt, puis `http://localhost:8000/site/`, ou artefact privé (données embarquées).
- Chemin des données : `../data/runs/` par défaut (`window.SL_DATA_BASE` pour le changer). Au lancement, Code choisit le déploiement (Pages depuis la racine ou copie de `site/` + `data/runs/`) ; seul ce chemin change.

## 1 bis. Identité

Charte commune (`docs/reseaux/RESEAUX.md` §1-2, discussion 4) : fond `#0B0D17`, violet `#7C5CFF`, bleu glace `#4FD1FF`, texte `#EDEBFF`, police Inter (sans chargement externe : repli système) ; logo piste B (sceau hexagonal) dans l'en-tête.

## 2. Arborescence (v1 → lancement)

| Page | Contenu | Version |
| --- | --- | --- |
| Classement | Onglets POC / BOT / GB / HOTM ; HOTM : un onglet par porte ; sélecteur de semaine (archives) | **v1 (fait)** |
| Build du joueur | `site/build.html#week=…&board=…&run=<run_id>` : lit `data/builds/<semaine>/<board>/<run_id>-1.json` et `-2.json` (POC/GB : un onglet par run, avec l'élément) ; noms FR/EN et icônes de `data/db/` ; SJW (armes, sets, noyaux, compétences, bénédictions), 3 chasseurs (arme, sets, noyaux), ombres, successeur ; éléments non reconnus regroupés (« n non reconnus ») ; bandeau si `build_partiel` ou `a_verifier`. Lien « build » sur les lignes classées du top 10 | **v2 (fait)** |
| Base de données | Fiches chasseurs, armes, artefacts… (`data/db/`), FR/EN | v3 |
| Vidéos | Guides de la semaine par mode | v3 |
| Demande de retrait | `site/retrait.html` : ce qui est retiré, demande dans le salon Discord #retrait, preuve = mot « ShadowLedger » dans la description de la chaîne, retrait sous 7 jours (choix par défaut) ; lien depuis le pied de page | **v1.1 (fait)** |
| Mentions légales | `site/mentions-legales.html` : éditeur particulier non professionnel anonyme (LCEN art. 6-III-2, identité donnée à l'hébergeur ; **à revoir si revenus** : un éditeur professionnel doit publier son identité), hébergeur GitHub, propriété intellectuelle Netmarble, aucun cookie ni statistique (seul `sl_lang` en stockage local) | **v1.2 (fait)** |

Liens réseaux (@shadowledger_hq) dans le pied de **chaque** page.

## 3. Fichier d'index — à produire par le pipeline (Code)

Un site statique ne peut pas lister un dossier : le pipeline écrit `data/runs/index.json` à chaque passage (daily et weekly) :

```json
{"weeks": [{"week": "2026-11-12", "frozen": false, "frozen_at": null,
            "boards": ["bot", "gb", "poc", "hotm-gate-1"]}]}
```

- `boards` = noms des fichiers de classement présents (sans `.json`), **jamais** `hotm-gate-inconnue` ni les fichiers `_*`.
- `frozen` / `frozen_at` repris de `_meta.json`.

## 4. Règles d'affichage de la page classement

- **Lignes classées** : `confidence: "sur"` et `rank` non nul, triées par `rank`. Top 3 en or / argent / bronze.
- **Lignes `a_verifier`** : jamais classées ; repliées sous « N run(s) en cours de vérification (non classées) ».
- `hotm-gate-inconnue.json` : jamais lu.
- Score : dégâts en T / B / M (valeur exacte au survol) ; BOT en secondes (« 28,349 s », m:ss,mmm au-delà d'une minute) ; RC, points, Rank Score en entier. Séparateurs selon la langue.
- Étiquettes : « une seule run » si `notes` la contient ; « arrondi » si `exact: false` sur une ligne classée ; « provisoire » sur une ligne à vérifier.
- GB : colonne Runs = élément de chaque run (`runs_detail[i].element`, pastille couleur ; `null` → « ? ») + RC de la run. POC (Rank Score) : pas de colonne Runs en v1 (`score.runs` = information, jamais additionnée).
- BOT : `player_ingame` sous le nom de la chaîne s'il est lu.
- Joueur = lien vers la chaîne (`channel_id`) ; Vidéo = lien vers chaque `video_ids`.
- Les `notes` techniques ne sont **jamais** affichées (seulement les étiquettes ci-dessus).
- Semaine d'essai (2026-11-12, SPEC_ETAPE1 §6 ; champ `essai` de `index.json` prioritaire s'il existe) : « (essai) » dans le sélecteur et bandeau « Semaine d'essai du pipeline : non publiée, chiffres non fiables ». **Au lancement : les semaines d'essai sont retirées du sélecteur.**
- POC 2026-11-19 : lignes fausses tirées des titres (« Unstable Dungeon », scores à 0), correction attendue de Code (SPEC_ETAPE1 v43). Rien de public d'ici là ; ne pas les citer en exemple.
- Bandeau : semaine en cours → « provisoire, mis à jour chaque soir, figé le jeudi 01h00 » ; semaine passée non figée → « encore provisoire » ; `frozen` → « définitif, figé le … ».
- Langue : FR par défaut, EN si le navigateur est en anglais ; bouton FR/EN ; choix mémorisé.
- Semaine par défaut : la plus récente.

## 5. Contrôle (checklist du skill, étape 5)

- Pages FR et EN de même contenu ; liens réseaux et crédits sur chaque page ; lien vers la vidéo source de chaque score ; `noindex` présent.
