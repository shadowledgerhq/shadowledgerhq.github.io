# Projet SLA — Shadow Ledger : contexte de référence

Document de référence du projet. Toute discussion du Projet SLA s'y fie. En cas de contradiction avec une discussion, ce document fait foi. Une seule version : `claude/CONTEXTE.md` du Projet et `docs/CONTEXTE.md` du dépôt sont identiques (la discussion 6 met à jour les deux). Mis à jour le 28/11/2026 (HOTM arrêté définitivement, §2-4). Avant : 27/11/2026 (POC refonte au Rank Score, §3-4 ; commande « message ? » et annonce de chaque message envoyé, §7 ; droit de pousser rappelé dans chaque message de démarrage, §7 ; SUIVI silencieux, §2 ; messages entre discussions annoncés en une ligne, plus recopiés ; boîtes de 8 et 9 dans `docs/BOITE.md`). Avant : 26/11/2026 (droit de pousser pour toutes les discussions, §7 ; rien de public avant le lancement ; boîtes : messages traités retirés ou archivés ; specs : seul le dépôt fait foi). Précédentes mises à jour : 19/11/2026 (discussions 8 et 9 ouvertes directement sur le dépôt) ; 17/11/2026 (alignement sur SPEC_ETAPE1 v30, aucun relevé manuel, `data/rotations/`).

## 1. Le projet en une phrase

**Shadow Ledger** recense chaque semaine les meilleures runs YouTube de *Solo Leveling: Arise* sur 3 modes (POC, BOT, GB ; HOTM arrêté le 28/11/2026), analyse les builds du top 10, publie un guide théorique par mode et diffuse le tout sur un site et sur les réseaux, en français et en anglais.

## 2. Décisions prises

| Sujet | Décision |
| --- | --- |
| Comptes Claude | Un seul compte (le compte payant). Le schéma à 8 comptes est abandonné. |
| Exécution | Le travail répétitif est fait par des scripts Python, pas par Claude. Claude écrit le code, vérifie les résultats et rédige. |
| Dépôt | Organisation GitHub gratuite `shadowledgerhq` (rattachée au compte perso d'Alexis), dépôt **public** `shadowledgerhq.github.io` (nécessaire pour GitHub Pages et GitHub Actions gratuits). Clés API en secrets GitHub, jamais dans le code. |
| Langues | Français et anglais partout (site, vidéos, posts). |
| Pseudo | Nom affiché « Shadow Ledger », identifiant **@shadowledger_hq** sur tous les réseaux (@shadowledgerhq était pris sur YouTube). GitHub reste `shadowledgerhq`. |
| Source des builds | slagate.com (portail fan FR de Sohoven). **Autorisation obtenue.** Autres sites seulement si l'info manque ou est douteuse. |
| Domaine | `shadowledgerhq.github.io` au début ; domaine personnel plus tard si le projet marche. |
| Autonomie | Les discussions trouvent elles-mêmes ce dont elles ont besoin ; Alexis ne fournit que ce que lui seul peut faire (section 9). Décision du 15/11/2026. |
| Aucun relevé manuel | Scores, builds, éléments autorisés, rotations : tout est relevé automatiquement par le pipeline. Une discussion n'écrit jamais « à relever à la main » ; une donnée non relevée reste vide ou « à vérifier ». Décision du 15/11/2026. |
| Rien de public avant le lancement | Site, réseaux et vidéos se **préparent** dès maintenant, rien n'est publié avant le feu vert d'Alexis. GitHub Pages coupé (Settings → Pages) ; déploiement du site seulement par `deployer-site.yml` (manuel) ; toutes les pages en `<meta name="robots" content="noindex">` + `site/robots.txt` « Disallow: / » (contrôle : `pipeline/check_site.py`), à retirer au lancement ; aucun script ne publie sur X, Discord, TikTok ou YouTube (test YouTube seulement en « Privé ») ; profils des comptes inchangés. Le dépôt reste public (Actions gratuites) mais n'est lié nulle part. Décision du 26/11/2026. |
| Lectures légères | Les spécifications ne sont que dans `docs/` du dépôt (plus de copie dans le Projet) : un **état actuel** court, l'historique des versions dans `docs/archives/`. Les archives (`docs/archives/`, `suivi/archives/`) ne se lisent qu'en cas de besoin précis. Décision du 26/11/2026. |
| Droit de pousser | Toutes les discussions peuvent écrire dans le dépôt, chacune dans sa zone (section 7). Décision du 26/11/2026. |
| HOTM arrêté | Décision d'Alexis du 28/11/2026 : HOTM n'est plus suivi (ni classement, ni builds, ni vidéo, ni page, ni post X). Données de 2026-11-12 gardées en archive. Côté code : `modes_actifs` = [poc, bot, gb] et `modes_classement` sans hotm (`pipeline/config/etape1.json`) ; vidéo à indices HOTM seuls rejetée `mode_arrete`. Réactivation : remettre `hotm` aux deux endroits. |
| SUIVI silencieux | Chaque discussion tient son SUIVI à jour dans `suivi/<discussion>.md` du dépôt (poussé à chaque étape), mais **ne l'affiche plus** à Alexis en fin de réponse. Il n'apparaît que dans le message prêt à coller du message n = 15. Décision du 27/11/2026. |

## 3. Les modes suivis (POC, BOT, GB)

| Mode | Nom complet | Critère de classement | Runs |
| --- | --- | --- | --- |
| POC | Power Of Calamity | **Depuis la refonte du 19/11/2026** : paliers ; classement au **Rank Score** = 1 000 000 × (palier − 1 + progression), les 2 équipes partageant les PV du boss (le score cumule les deux) ; égalité = ex aequo ; plus d'élément imposé (`docs/SPEC_ETAPE1.md` §9). Avant le 19/11 : dégâts max, total = meilleure run de l'équipe 1 + meilleure run de l'équipe 2 | Depuis le 19/11 : 1 (meilleur Rank Score de la semaine) ; avant : 2 (une par équipe) |
| BOT | Battlefield Of Time | Chrono le plus court, **un seul classement par semaine** (le mode Challenge a été retiré du jeu en mai 2026, source forum Netmarble). Saison = 4 semaines de jeu (1 boss par semaine) + 1 semaine de calcul sans classement | 1 |
| GB | Guild Boss | Rage Count (RC) le plus élevé. **Seules les runs filmées (écran Results) comptent.** Une run = un groupe (6 chasseurs, équipes A + B, + SJW) : total = meilleure run filmée de chaque groupe (toutes vidéos de la semaine). Égalité de RC : départage par la somme des dégâts. Le *Personal Record* sert seulement à identifier le groupe ; il ne classe jamais une run non filmée | 2 (une par groupe) |
| HOTM | Hall Of The Monarchs | **Arrêté définitivement le 28/11/2026** (§2). Ancienne règle, pour les archives : points, un classement par porte | — |

- Reset de tous les modes : **jeudi 01h00, heure de Paris**.
- Une **semaine** est identifiée par la date du jeudi où elle commence (ex. `2026-11-12`).
- BOT, cycle de saison (dates **calculées**, à vérifier sur les vidéos) : S20 a commencé le 22/10/2026 ; semaine de calcul le 19/11/2026 ; S21 le 26/11/2026. Le titre `S<n>-<w>` (saison n, semaine w) sert de contrôle de semaine.
- Rythme des boss (SPEC_ETAPE1 v24 §4.5, sources Netmarble via dotgg.gg, **à vérifier sur les données**) : BOT change chaque jeudi ; POC à chaque saison ; GB à la mise à jour régulière suivante (attributs variables changés chaque semaine).
- Éléments autorisés (ombres, successeur, Sung Jin Woo, compétences, bénédictions) : ils peuvent changer chaque semaine. Ils sont **déduits des écrans par le pipeline** et enregistrés dans `data/rules/<semaine>.json`, un bloc par classement (`poc`, `bot`, `gb`), avec source et date : `true` dès qu'une run sûre montre l'élément ; `false` seulement si au moins 5 runs sûres de 5 chaînes le montrent absent ; sinon `null` (= inconnu, jamais « interdit »).

## 4. Les étapes

### Étape 1 — Classements (automatisée)

1. **Recherche** : YouTube Data API v3, vidéos publiées depuis le dernier reset. Quota ≈ 100 recherches/jour : requêtes ciblées.
2. **Tri 1** : score dans le titre, la description ou les sous-titres (Whisper si commentaire oral). Score du titre = provisoire tant qu'il n'est pas confirmé à l'image.
3. **Tri 2** : score lisible sur la miniature (OCR).
4. **Tri 3** : images des 10 premières secondes et des 30 dernières, 1 image / 2 s (OCR).
5. **Tri 4** : vidéo entière, 1 image / 10 s (OCR).
6. Vidéo sans score après le tri 4 → liste `rejected` (identifiant + raison), jamais réanalysée.

Règles :
- **Joueur = chaîne YouTube** (`channel_id`) ; le pseudo en jeu n'est pas la clé (au BOT, il est seulement noté dans `player_ingame`). Une ligne par joueur, toutes vidéos de la semaine confondues.
- Shorts inclus ; lives et rediffusions de live exclus.
- POC (avant le 19/11/2026 seulement ; depuis : Rank Score, §3) et GB : somme des 2 meilleures runs distinctes, qui peuvent venir de **2 vidéos différentes** (POC : équipe 1 + équipe 2 ; GB : groupe 1 + groupe 2 ; jamais deux runs de la même équipe ou du même groupe). Une seule run `sur` : le joueur est **classé** (total = cette run, note « une seule run ») ; une 2e run trouvée plus tard dans la semaine, dans la même vidéo ou une autre, complète le total. Une seule run provisoire : `a_verifier`.
- POC et GB, groupe/équipe inconnu : les runs sont distinguées par leur **élément** (`runs_detail[i].element` : light / fire / water / wind / dark, ou `null`, avec `element_source`), lu sur les chasseurs à l'écran, sinon dans le titre. Deux groupes/équipes n'ont jamais de chasseur commun (un chasseur commun → `a_verifier`). L'Excel affiche l'élément au lieu de « Groupe/Équipe 1/2 ». (L'ancienne règle « le groupe n'est jamais déduit du titre » est levée.)
- Égalité : la vidéo publiée en premier passe devant (GB : d'abord la somme des dégâts).
- Score arrondi (« 2.1B ») : provisoire ; on garde la valeur exacte dès qu'elle est lue à l'image.
- Doublons : même run ré-uploadée ou postée en 2 langues → on garde la vidéo de la chaîne d'origine (la plus ancienne).
- Boss de la semaine **déduit des données** : libellé le plus fréquent parmi les runs sûres, à partir de 3 vidéos (`_boss.json`). Run avec un autre libellé → `a_verifier` ; libellé de la semaine précédente → `rejected`.
- Toutes régions et langues (OCR multilingue, formats 1.2B / 억 / 万). Écrans aux libellés inconnus : collectés par le pipeline.
- Champ `confiance` : `sur` ou `a_verifier`.
- Compteurs animés (RC, Final Score) : seule la valeur finale compte ; les valeurs croissantes lues avant sont des étapes de l'animation (note « compteur animé »).
- Seul l'écran RESULT donne un score sûr, **sans exception** (GB : le Personal Record identifie le groupe, il ne donne jamais le score classé).
- POC : le score retenu est « 이번 기록 » (score de cette run) de l'écran RESULT, **jamais** « 기존 기록 » (ancien record) ni le score de l'écran de composition.
- BOT : score = chrono de la dernière phase de l'écran `Results` (= chrono du bandeau du bas). Un seul classement (`bot.json`). Titre `S<n>-<w>` de la semaine précédente → `rejected` (`semaine_precedente`) ; vidéo BOT publiée pendant la semaine de calcul → `a_verifier`.
- Contrôles de cohérence :
  - POC : total = SJW + successeur + 3 chasseurs (avant le 19/11) ; depuis la refonte : Rank Score = 1e6 × (palier − 1 + progression) et progression = Team 1 % + Team 2 % (SPEC_ETAPE1 §9) ;
  - BOT : phases cumulées croissantes, dernière phase = chrono du bandeau = `Play Time` tronqué à la seconde ;
  - GB : `Player's Score` + les 6 `Hunter Rank` = `Final Score` (écran Results).
- Vidéo publiée moins de 3 h après le reset : note d'alerte « semaine précédente ? », jamais un rejet.
- Légendes ajoutées par l'auteur de la vidéo (titre, texte incrusté) : au mieux un score provisoire, à confirmer sur l'écran RESULT.
- *Décisions d'Alexis à partir du 13/11/2026 (discussion 1 — Classements).* Détail complet : `docs/SPEC_ETAPE1.md` du dépôt (état actuel, fait foi ; historique dans `docs/archives/`).

### Étape 2 — Builds du top 10 (automatisée en grande partie)

- Mêmes tris que l'étape 1, sur le **top 10 de chaque mode**. Une vidéo ne s'arrête pas quand une partie du stuff est trouvée : elle passe au tri suivant avec ce qui est déjà trouvé.
- Éléments recherchés : persos, armes, 3 ombres (si le mode le permet), successeur (si le mode le permet), artefacts de chaque perso, skills et bénédictions (si Sung Jin Woo), noyaux, **stats principales** des persos.
- Statut final : `build_complet`, `build_partiel` ou `pas_de_build`.
- POC/GB : une vidéo avec 2 runs = 2 builds distincts ; le build reprend le champ `element` de la run.
- Reconnaissance des objets : comparaison d'images (OpenCV) avec la **banque d'icônes** et les cartes de chasseurs (discussion 9).
- Source unique : un JSON par build. Un **PowerPoint par vidéo du top 10** est généré automatiquement (1 slide par élément du build) ; il sert de base pour les vidéos. Détail : `docs/SPEC_ETAPE2.md`.

### Étape 3a — Base de données du jeu

- Fichiers JSON découpés par catégorie : chasseurs, armes, sets d'artefacts, noyaux, bénédictions, ombres, successeurs, compétences de Sung Jin Woo, etc.
- Chaque entrée : identifiant, nom **FR + EN** (+ coréen si possible), rareté, effets, passifs, conditions d'activation, valeurs par niveau, source, date de vérification, version du jeu.
- Banque d'icônes : une image par objet, construite à partir de captures et de slagate (autorisé).
- Mise à jour à chaque patch, à partir des notes des développeurs sur le forum officiel Netmarble.
- La base sera aussi affichée sur le site (fiches).

### Étape 3b — Theorycraft et vidéos

- **3 vidéos par semaine**, une par mode suivi, version **compte au maximum** uniquement (pas de F2P). Un guide POC ou GB peut servir plusieurs semaines tant que le boss ne change pas ; la vidéo BOT est refaite chaque semaine et publiée en début de semaine.
- Alexis ne joue pas : vidéos **100 % schémas** (composition, stuff, rotation sur une timeline, timings, estimation des dégâts). Aucun extrait de gameplay de tiers.
- Base de départ : les meilleures runs réelles du classement, améliorées ou remplacées par une équipe nouvelle.
- **Rotation** : vient du relevé automatique `data/rotations/` (`docs/SPEC_ROTATION.md` : compétences détectées par le passage en recharge des boutons du HUD ; top 3, BOT d'abord ; passage PC, la vidéo étant déjà téléchargée). Aucun relevé manuel.
- Tout ce qui n'est pas observé dans une run réelle est présenté comme une **estimation calculée**, sources citées. Objectif : « le guide le plus optimisé connu à date ».
- Chaque choix est justifié (pourquoi ce perso, ce set, cette rotation, ce timing).
- Voix : **clone de la voix d'Alexis** (outil gratuit à licence commerciale, ex. Chatterbox ou OpenVoice ; licence à vérifier). Échantillon de voix fourni par Alexis.
- Script rédigé en FR et en EN.
- Avant le lancement : vidéos produites en interne seulement (section 2).

### Étape 4 — Réseaux sociaux

| Réseau | Format | Langue |
| --- | --- | --- |
| YouTube | 3 vidéos/semaine, une chaîne, 2 pistes audio (FR + EN) | FR + EN |
| YouTube Shorts | Extraits verticaux | EN + sous-titres FR |
| TikTok | Clips verticaux de **1 à 3 min** (rémunération > 1 min) | Voix EN + sous-titres FR |
| Discord | Serveur communautaire, salon « classement de la semaine » | FR + EN |
| X | Top 3 de chaque classement en image (POC, BOT, GB), **chaque mercredi** | FR + EN |
| Instagram Reels | Optionnel, réutilise les verticaux | EN + sous-titres FR |

- Même pseudo, même description, même photo de profil partout. Création des comptes : par Alexis.
- Intro et outro ≤ 5 s, renvoyant vers les autres comptes et le site.
- Classements publiés le **mercredi** (quasi définitifs avant le reset du jeudi 01h), **à partir du lancement** (section 2).
- Risque connu : 3 vidéos/semaine au même gabarit = risque de démonétisation pour contenu « produit en série ». Chaque vidéo doit apporter une analyse réellement différente.
- Seuils de monétisation : YouTube 1 000 abonnés + 4 000 h (8 000 h pour les candidatures dès le 01/02/2027) ou Shorts ; TikTok Creator Rewards 10 000 abonnés + 100 000 vues/30 j.
- Cocher « contenu modifié ou synthétique » sur YouTube (voix clonée), par prudence.

### Étape 5 — Site web

- Site statique sur GitHub Pages, FR + EN, qui lit les JSON du dépôt. Pages coupé et `noindex` jusqu'au lancement (section 2).
- Pages : classement par mode (POC, BOT, GB) → page build du joueur → fiches de la base de données → liens vers les réseaux (sur toutes les pages) → vidéos.
- Archives des semaines passées.
- Crédit et lien vers la vidéo source de chaque joueur ; moyen de demander le retrait.
- Mentions légales ; consentement cookies si statistiques ou publicité.
- Visuels : uniquement officiels autorisés (fan kit Netmarble) ou originaux.

## 5. Calendrier automatique (heure de Paris)

| Quand | Quoi | Où |
| --- | --- | --- |
| Tous les jours 20h00 | Nouvelles vidéos : tris 1-2, puis tris 3-4, builds du top 10, relevé de rotation, mise à jour du site | GitHub Actions (tris 1-2, site) + PC d'Alexis (tris 3-4, builds, rotations : YouTube bloque le téléchargement depuis le cloud) |
| Jeudi 01h00 | Passage final : classement de la semaine figé et archivé, nouvelle semaine ouverte | GitHub Actions + PC d'Alexis |
| Mercredi (après lancement) | Posts du classement (X, Discord) ; vidéos de la semaine | Alexis / outil de programmation |
| Après chaque passage | Contrôle des résultats + rapport court | Tâche planifiée Claude |

Note technique : les horaires GitHub Actions sont en UTC ; gérer le passage heure d'été / heure d'hiver. Le passage PC doit suivre le passage GitHub (ordre à confirmer par la discussion 7, 26/11/2026).

## 6. Structure du dépôt GitHub

```
shadowledgerhq.github.io/
├── data/
│   ├── db/                  base de données du jeu (un JSON par catégorie) + patches.json
│   ├── icons/<categorie>/   banque d'icônes
│   ├── rules/<semaine>.json éléments autorisés par classement, déduits des écrans (true / false / null)
│   ├── runs/<semaine>/      classements publiés : poc.json, gb.json, bot.json (hotm-gate-<n>.json : archive 2026-11-12 seulement)
│   │                        internes : _lectures.json (lectures de score des tris, champ `regles`, entrée de classement.py), _videos.json (titre, chaîne, miniature, durée, mode_guess),
│   │                        _meta.json (fenêtre, gel), _boss.json (boss déduit), _rapport.md (rapport du passage)
│   ├── channels.json        chaînes YouTube suivies (channel_id, nom, playlist d'uploads, ajout manuel ou auto)
│   ├── builds/<semaine>/<mode>/   un JSON par build
│   ├── rotations/<semaine>/<mode>/<video_id>.json   relevé automatique de l'ordre des compétences (+ _crops/)
│   ├── rotations/<semaine>/_rapport.md              rapport du relevé de rotation
│   ├── rejected/<semaine>.json
│   └── processed.json       vidéos déjà traitées ; `pc.sous_titres` et `pc.rotation` = fait | absent | erreur
├── docs/                    spécifications (SPEC_ETAPE1, SPEC_ETAPE2, SPEC_ROTATION, SPEC_SITE…, état actuel), essais, réseaux, CONTEXTE.md, BOITE.md (messages des discussions 8-9 vers 1-7)
│   └── archives/            historiques des specs, messages traités de BOITE.md
├── pipeline/                scripts Python
├── outils-pc/               scripts .bat du PC d'Alexis
├── exports/<semaine>/       Excel et PowerPoint générés
├── videos/<semaine>/<mode>/ scripts FR/EN, storyboard
├── site/                    site statique
├── suivi/                   un SUIVI.md par discussion (anciennes lignes « Fait » dans suivi/archives/)
└── .github/workflows/       daily.yml (20h), weekly.yml (jeudi 01h), auto-merge-claude.yml, deployer-site.yml (manuel)…
```

Format de `data/rotations/…/<video_id>.json` : voir `docs/SPEC_ROTATION.md` §3 (fait foi ; un objet par run dans `runs[]`, événements horodatés `t` / `t_run`).

## 7. Discussions du Projet SLA

| # | Discussion | Rôle |
| --- | --- | --- |
| 1 | Étape 1 — Classements | Règles, contrôle des classements |
| 2 | Étape 2 — Builds | Règles, contrôle des builds, PowerPoint |
| 3 | Étape 3 — Theorycraft & vidéos | Analyses, scripts FR/EN, storyboards, spec du relevé de rotation |
| 4 | Étape 4 — Réseaux | Comptes, logo, posts, calendrier de publication |
| 5 | Étape 5 — Site | Contenu, design, pages |
| 6 | Prompt | Architecture, contexte, instructions, skill |
| 7 | Tâche planifiée | Contrôle automatique et rapports |
| 8 | Code | Scripts Python, workflows GitHub Actions — **dans Claude Code** (écrit dans le dépôt) |
| 9 | Base de données | Base du jeu (3a), banque d'icônes, cartes de chasseurs — **dans Claude Code** (écrit dans le dépôt) |

Les discussions d'étape décident **quoi** faire ; la discussion Code décide **comment** le coder. Code pousse toujours sur une branche `claude/…` (fusion automatique dans `main`).

Les discussions 8 et 9 se font dans Claude Code (claude.ai/code), **ouvertes directement sur le dépôt** `shadowledgerhq/shadowledgerhq.github.io` (choix du dépôt à la création de la session) : elles lisent `CLAUDE.md` et le skill du dépôt. Les autres se font dans le Projet SLA sur claude.ai. Prompts de démarrage : `PROMPTS_DISCUSSIONS.md`.

### Droit de pousser (26/11/2026)

Toutes les discussions (1 à 9) écrivent elles-mêmes dans le dépôt, **chacune dans sa zone** :
- **Accès** : une discussion du Projet (1 à 7) demande l'accès en écriture au dépôt (`add_repo`, accès `push`) la première fois qu'elle doit écrire ; Alexis accepte une fois par session. Discussions 8 et 9 : ouvertes sur le dépôt.
- **Méthode** : clone superficiel, `git pull origin main`, branche `claude/<discussion>-<sujet>`, commit court en français, push. Le workflow `auto-merge-claude.yml` fusionne dans `main`. Pas de pull request. Rien laissé non poussé.
- **Hors de sa zone** : ne rien modifier ; écrire un message au propriétaire de la zone (`claude/BOITE.md` pour 1 à 7, `docs/BOITE.md` §8 ou §9 pour 8 et 9).
- Les documents de travail du Projet (`claude/site/`, `claude/SPEC_SITE.md`, `claude/reseaux/`…) sont déplacés dans le dépôt par leur discussion, puis retirés du Projet. Le Projet ne garde que `CONTEXTE.md`, `BOITE.md` et `PROMPTS_DISCUSSIONS.md`.

| Discussion | Zone d'écriture |
| --- | --- |
| 1 — Classements | `docs/SPEC_ETAPE1.md`, `docs/REFERENCE_ECRANS_*.md`, `docs/essais/` (classements), `suivi/classements.md` |
| 2 — Builds | `docs/SPEC_ETAPE2.md`, `docs/essais/builds/`, `docs/essais/composition/`, `suivi/builds.md` |
| 3 — Theorycraft & vidéos | `docs/SPEC_ROTATION.md`, `videos/`, `suivi/theorycraft.md` |
| 4 — Réseaux | `docs/reseaux/`, `suivi/reseaux.md` |
| 5 — Site | `docs/SPEC_SITE.md`, `site/` (pages, styles, textes ; ni `robots.txt` ni `noindex` retirés avant le lancement), `suivi/site.md` |
| 6 — Prompt | `docs/CONTEXTE.md`, `docs/PROMPTS_DISCUSSIONS.md`, `CLAUDE.md`, `.claude/skills/shadow-ledger/`, `suivi/prompt.md` |
| 7 — Tâche planifiée | `docs/controle/`, `suivi/tache-planifiee.md` |
| 8 — Code | `pipeline/`, `.github/`, `outils-pc/`, `exports/`, `data/` (sauf `db/` et `icons/`), `docs/BOITE.md`, `docs/archives/`, `docs/PC_ALEXIS.md`, `suivi/code.md` ; scripts de génération du site |
| 9 — Base de données | `data/db/`, `data/icons/`, `suivi/base-de-donnees.md` |

Les données produites par le pipeline (`data/runs/`, `data/builds/`, `data/rotations/`…) ne sont jamais modifiées à la main, par aucune discussion.

### Aiguillage : quelle discussion pour quelle demande

| Demande d'Alexis | Discussion |
| --- | --- |
| Règles de recherche YouTube, tris, calcul des scores, vérification d'un classement | 1 — Classements |
| Éléments d'un build, statuts, PowerPoint, vérification d'un build | 2 — Builds |
| Meilleure team, rotation (et son relevé), script ou storyboard d'une vidéo, voix off | 3 — Theorycraft & vidéos |
| Logo, profils, posts, Discord, calendrier de publication, monétisation | 4 — Réseaux |
| Pages, design, textes ou bugs d'affichage du site | 5 — Site |
| Organisation du projet, CONTEXTE.md, instructions, skill, nouvelle règle | 6 — Prompt |
| Contrôle automatique, rapports, horaires des passages | 7 — Tâche planifiée |
| Écrire ou corriger un script, un workflow, une erreur technique, installation | 8 — Code (Claude Code) |
| Données du jeu (chasseurs, armes, artefacts…), icônes, mise à jour après un patch | 9 — Base de données (Claude Code) |

Règle de renvoi : si une demande relève d'une autre discussion, Claude ne la traite pas : il écrit le message dans la boîte du destinataire (discussions 1 à 7 → `claude/BOITE.md` du Projet ; discussions 8 et 9 → `docs/BOITE.md` du dépôt, §8 ou §9, poussé sur sa branche), avec le contexte utile (fichiers, décisions, ce qui est attendu).

**Annonce à Alexis** (27/11/2026, renforcée le 27/11/2026) : **chaque fois** qu'une discussion pose un message dans une boîte, au cours de la discussion, elle le dit à Alexis dans la même réponse, sans exception (une ligne par message, à la fin de la réponse). Le message **n'est jamais recopié** : Claude écrit seulement une ligne : « Message de <discussion> pour <discussion> dans `claude/BOITE.md` » (ou `docs/BOITE.md` §n). Pour 8 et 9, Alexis leur dit simplement « lis ta boîte ». Seule exception : session sans accès en écriture au dépôt → message prêt à coller pour 8 ou 9, comme avant. Le message prêt à coller pour **ouvrir une nouvelle discussion** (compteur à 15) reste donné en entier.

**Commande « message ? »** (27/11/2026) : quand Alexis écrit « message ? », la discussion (1) relit `claude/BOITE.md` et `docs/BOITE.md`, traite les messages qui lui sont adressés et dit lesquels ; (2) liste les messages qu'elle a envoyés à d'autres discussions, une ligne chacun : destinataire, date, sujet en quelques mots, état (« en attente » s'il est encore dans la boîte, « traité » s'il est passé en traité ou retiré). Ici, et seulement ici, le résumé du message est montré à Alexis. Rien en attente ni envoyé : « Aucun message ».

**Boîte aux lettres** (15/11/2026, allégée le 26/11/2026) : entre les discussions 1 à 7, les messages passent par le document du Projet `claude/BOITE.md`, sans Alexis. Chaque discussion lit `claude/BOITE.md` et `docs/BOITE.md` en début de discussion et traite les messages qui lui sont adressés. Message traité : **retiré** de `claude/BOITE.md` (la décision est dans la SPEC, ce document ou le SUIVI du destinataire) ; dans `docs/BOITE.md`, passé en « traité » puis archivé par Code dans `docs/archives/` au plus tard 7 jours après. Vers 8 ou 9 : `docs/BOITE.md` §8 ou §9 (lu par 8 et 9 au démarrage). Depuis 8 ou 9 : `docs/BOITE.md` du dépôt, section du destinataire, lu par les discussions 1 à 7.

**Compteur** (15/11/2026) : chaque réponse commence par **« Message n/15 »**, où n = nombre de messages d'Alexis dans la discussion (n = numéro de la réponse précédente + 1, pour ne pas avoir à recompter). À partir de **n = 15**, Claude ajoute en tête « ⚠ Discussion longue », recommande d'ouvrir une nouvelle discussion et donne un seul message prêt à coller : la ligne de rôle (qui rappelle le droit de pousser dans sa zone, `add_repo` push), le SUIVI à jour (lu dans `suivi/<discussion>.md`) et la prochaine action précise. C'est le seul moment où le SUIVI est montré à Alexis. La règle figure dans les instructions du Projet (discussions 1 à 7) et dans `CLAUDE.md` du dépôt (discussions 8 et 9). Si une discussion ne compte pas, Alexis lui indique « on en est au message n ».

**Autonomie** (15/11/2026) : Claude ne demande jamais à Alexis une information qu'il peut trouver lui-même (dépôt GitHub, documents du Projet, slagate.com, forum Netmarble, vidéos YouTube via le pipeline, recherche web). Il cherche d'abord. Si c'est introuvable, il prend l'hypothèse la plus prudente, la marque « à vérifier » avec sa source, et continue. Pour une décision, il propose son choix par défaut et avance ; Alexis peut le refuser. « Besoin d'Alexis » dans le SUIVI ne contient que ce qu'Alexis seul peut faire (section 9). Aucun relevé manuel ne lui est demandé (section 2).

## 8. Ordre de réalisation

1. **Mise en place** : dépôt GitHub, clé API YouTube en secret, skill installé, documents dans le projet. *Fait le 12/11/2026.*
2. **Base de données + banque d'icônes** (discussion 9).
3. **Pipeline étape 1** (discussions 1 et 8), avec les images de référence des scores.
4. **Site v1** : classements (discussion 5), en interne jusqu'au lancement.
5. **Étape 2** : builds du top 10 + PowerPoint + pages builds ; relevé de rotation (SPEC_ROTATION, BOT d'abord).
6. **Réseaux** : logo, échantillon de voix, premières vidéos (discussions 3 et 4), en interne jusqu'au lancement.
7. **Tâche planifiée** de contrôle (discussion 7).
8. **Lancement public** : sur décision d'Alexis, quand tout est au point.

## 9. Ce qu'Alexis seul peut faire

À fournir une fois :
- [ ] Échantillon de voix (1 à 2 min, propre, sans bruit) — pour le clone de voix.
- [ ] Trace écrite de l'autorisation de Sohoven (à conserver).
- [ ] Nom TikTok à passer en « Shadow Ledger » à partir du 19/11/2026.
- [ ] Feu vert du lancement public (section 2).
- [x] Clé API YouTube Data v3, rangée dans le secret GitHub `YOUTUBE_API_KEY`.
- [x] Organisation `shadowledgerhq` + dépôt public `shadowledgerhq.github.io` créés.
- [x] Comptes réseaux créés le 12/11/2026 : YouTube, TikTok, X, Instagram (@shadowledger_hq) + compte et serveur Discord « Shadow Ledger ».

En continu :
- Connexions aux comptes (réseaux, GitHub) et secrets GitHub.
- Actions sur son PC (installer, lancer des scripts, horaires du Planificateur de tâches).
- Ouvrir les discussions 8 et 9 sur le dépôt ; accepter l'accès en écriture au dépôt (`add_repo`, push) dans les discussions 1 à 7, une fois par session.
- Modifier les instructions du Projet ; enregistrer les propositions de skill ; dire « lis ta boîte » aux discussions 8 et 9 quand un message les attend ; coller le message de démarrage d'une discussion neuve.
- Refuser un choix par défaut proposé par une discussion, s'il n'est pas d'accord.

Repris par les discussions (plus demandé à Alexis, 15/11/2026) :
- Images de référence des scores, dont les libellés coréens et japonais manquants → discussion 1 (images extraites des vidéos par le pipeline). Déjà fait : BOT et GB (client anglais), POC et HOTM (client coréen).
- Images de référence des éléments du build → discussion 2 (`docs/essais/composition/auto/`).
- Éléments autorisés par classement et par semaine → pipeline (section 3).
- Ordre des compétences (rotation) → relevé automatique (section 4, étape 3b).

## 10. Points ouverts

- Rythme des boss POC et GB : réponse provisoire en section 3 (sources Netmarble via dotgg.gg), à confirmer sur les données par la discussion 1.
- Poids du dépôt (`.git` 178 Mo au 26/11/2026) : tout est gardé ; on en reparle à 500 Mo.
- Dépôt public avant le lancement : les données et docs sont lisibles par qui trouve le dépôt (non lié, non annoncé). Alternative si Alexis le veut : dépôt privé jusqu'au lancement (Actions gratuites dans la limite de 2 000 min/mois, à vérifier ; Pages indisponible en privé sur le plan gratuit ; la source GitHub du Projet devra être réautorisée).
- Déclaration des revenus (statut micro-entrepreneur) quand les plateformes paieront.
