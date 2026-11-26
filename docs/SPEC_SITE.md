# SPEC_SITE — Site Shadow Ledger (étape 5)

État actuel : **v1.2 — 2026-11-27** (discussion 5 — Site). Historique : `docs/archives/` quand il y aura une v2.

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
| Build du joueur | Depuis une ligne du top 10 : build (`data/builds/`), PowerPoint, vidéo source | v2 (après étape 2) |
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
- Bandeau : semaine en cours → « provisoire, mis à jour chaque soir, figé le jeudi 01h00 » ; semaine passée non figée → « encore provisoire » ; `frozen` → « définitif, figé le … ».
- Langue : FR par défaut, EN si le navigateur est en anglais ; bouton FR/EN ; choix mémorisé.
- Semaine par défaut : la plus récente.

## 5. Contrôle (checklist du skill, étape 5)

- Pages FR et EN de même contenu ; liens réseaux et crédits sur chaque page ; lien vers la vidéo source de chaque score ; `noindex` présent.
