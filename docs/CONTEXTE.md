# Projet SLA — Shadow Ledger : contexte de référence

Document de référence du projet. Toute discussion du Projet SLA s'y fie. En cas de contradiction avec une discussion, ce document fait foi. Mis à jour le 13/11/2026 (alignement sur SPEC_ETAPE1 v6 : GB classé au Rage Count, écran Personal Record accepté, contrôles BOT et GB).

## 1. Le projet en une phrase

**Shadow Ledger** recense chaque semaine les meilleures runs YouTube de *Solo Leveling: Arise* sur 4 modes, analyse les builds du top 10, publie un guide théorique par mode et diffuse le tout sur un site et sur les réseaux, en français et en anglais.

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

## 3. Les 4 modes

| Mode | Nom complet | Critère de classement | Runs |
| --- | --- | --- | --- |
| POC | Power Of Calamity | Dégâts max. Une run = une équipe : total = meilleure run de l'équipe 1 + meilleure run de l'équipe 2 | 2 (une par équipe) |
| BOT | Battlefield Of Time | Chrono le plus court, **deux classements par semaine** : `season` (時の戦場, saison de 49 jours, SJW autorisé) et `challenge` (時の戦場チャレンジ, 7 jours, chasseurs uniquement) | 1 par variante |
| GB | Guild Boss | Rage Count (RC) le plus élevé. Une run = un groupe (6 chasseurs, équipes A + B, + SJW) : total = meilleure run du groupe 1 + meilleure run du groupe 2. Égalité de RC : départage par la somme des dégâts. Écran *Personal Record* accepté comme source | 2 (une par groupe) |
| HOTM | Hall Of The Monarchs | Points les plus élevés, **par porte** : un classement par porte (제 n관문 / 第n関門), pas de classement HOTM global | 1 par porte |

- Reset de tous les modes : **jeudi 01h00, heure de Paris**.
- Une **semaine** est identifiée par la date du jeudi où elle commence (ex. `2026-11-12`).
- Éléments autorisés (ombres, successeur, Sung Jin Woo, compétences, bénédictions) : **ils changent chaque semaine** (ex. semaine du 05/11/2026 : BOT challenge sans Sung Jin Woo, compétences ni bénédictions, mais avec ombres et successeur). Ils sont enregistrés dans `data/rules/<semaine>.json`, un bloc par classement (`poc`, `bot_season`, `bot_challenge`, `gb`, `hotm`), avec source et date de vérification.

## 4. Les étapes

### Étape 1 — Classements (automatisée)

1. **Recherche** : YouTube Data API v3, vidéos publiées depuis le dernier reset. Quota ≈ 100 recherches/jour : requêtes ciblées.
2. **Tri 1** : score dans le titre, la description ou les sous-titres (Whisper si commentaire oral). Score du titre = provisoire tant qu'il n'est pas confirmé à l'image.
3. **Tri 2** : score lisible sur la miniature (OCR).
4. **Tri 3** : images des 10 premières secondes et des 30 dernières, 1 image / 2 s (OCR).
5. **Tri 4** : vidéo entière, 1 image / 10 s (OCR).
6. Vidéo sans score après le tri 4 → liste `rejected` (identifiant + raison), jamais réanalysée.

Règles :
- **Joueur = chaîne YouTube** (`channel_id`) ; le pseudo en jeu n'est pas la clé (au BOT, il est seulement noté dans `player_ingame`). Une ligne par joueur (HOTM : par porte ; BOT : par variante), toutes vidéos de la semaine confondues.
- Shorts inclus ; lives et rediffusions de live exclus.
- POC et GB : somme des 2 meilleures runs distinctes, qui peuvent venir de **2 vidéos différentes** (POC : équipe 1 + équipe 2 ; GB : groupe 1 + groupe 2 ; jamais deux runs de la même équipe ou du même groupe). Si une seule run est trouvée : statut `a_verifier`, pas de classement tant que la 2e manque.
- Égalité : la vidéo publiée en premier passe devant (GB : d'abord la somme des dégâts).
- Score arrondi (« 2.1B ») : provisoire ; on garde la valeur exacte dès qu'elle est lue à l'image.
- Doublons : même run ré-uploadée ou postée en 2 langues → on garde la vidéo de la chaîne d'origine (la plus ancienne).
- Boss de la semaine **déduit des données** : libellé le plus fréquent parmi les runs sûres, à partir de 3 vidéos (`_boss.json`). Run avec un autre libellé → `a_verifier` ; libellé de la semaine précédente → `rejected`.
- Toutes régions et langues (OCR multilingue, formats 1.2B / 억 / 万).
- Champ `confiance` : `sur` ou `a_verifier`.
- Seul l'écran RESULT donne un score sûr. **Exception GB** : l'écran *Personal Record* est accepté si `Total Rage Count` = RC du groupe 1 + RC du groupe 2 et si `Time Left in Season` prouve que la capture date de la semaine en cours (sinon `rejected`, raison `semaine_precedente`).
- POC et HOTM : le score retenu est « 이번 기록 » (score de cette run) de l'écran RESULT, **jamais** « 기존 기록 » (ancien record) ni le score de l'écran de composition.
- BOT : score = chrono de la dernière phase de l'écran `Results` (= chrono du bandeau du bas). Variante : armes de SJW présentes dans le bandeau → `season`, absentes → `challenge` (indice à confirmer sur une capture de challenge).
- Contrôles de cohérence :
  - POC : total = SJW + successeur + 3 chasseurs ;
  - HOTM : total = 클리어 (clear) + 증명 보너스 (bonus de preuve) ;
  - BOT : phases cumulées croissantes, dernière phase = chrono du bandeau = `Play Time` tronqué à la seconde ;
  - GB : `Player's Score` + les 6 `Hunter Rank` = `Final Score` (écran Results) ; `Total Rage Count` = groupe 1 + groupe 2 (Personal Record).
- Légendes ajoutées par l'auteur de la vidéo (titre, texte incrusté) : au mieux un score provisoire, à confirmer sur l'écran RESULT.
- HOTM : une ligne par joueur **et par porte** ; porte illisible (écran et titre) → `hotm-gate-inconnue.json`, jamais publié. BOT : variante illisible → `bot-variante-inconnue.json`, jamais publié.
- *Décisions d'Alexis du 13/11/2026 (discussion 1 — Classements).* Détail complet : `docs/SPEC_ETAPE1.md` v6 (aussi dans les documents du Projet SLA).

### Étape 2 — Builds du top 10 (automatisée en grande partie)

- Mêmes tris que l'étape 1, sur le **top 10 de chaque mode**. Une vidéo ne s'arrête pas quand une partie du stuff est trouvée : elle passe au tri suivant avec ce qui est déjà trouvé.
- Éléments recherchés : persos, armes, 3 ombres (si le mode le permet), successeur (si le mode le permet), artefacts de chaque perso, skills et bénédictions (si Sung Jin Woo), noyaux, **stats principales** des persos.
- Statut final : `build_complet`, `build_partiel` ou `pas_de_build`.
- POC/GB : une vidéo avec 2 runs = 2 builds distincts.
- Reconnaissance des objets : comparaison d'images (OpenCV) avec la **banque d'icônes** (à construire, cf. étape 3a).
- Source unique : un JSON par build. Un **PowerPoint par vidéo du top 10** est généré automatiquement (1 slide par élément du build) ; il sert de base pour les vidéos.

### Étape 3a — Base de données du jeu

- Fichiers JSON découpés par catégorie : chasseurs, armes, sets d'artefacts, noyaux, bénédictions, ombres, successeurs, compétences de Sung Jin Woo, etc.
- Chaque entrée : identifiant, nom **FR + EN** (+ coréen si possible), rareté, effets, passifs, conditions d'activation, valeurs par niveau, source, date de vérification, version du jeu.
- Banque d'icônes : une image par objet, construite à partir de captures et de slagate (autorisé).
- Mise à jour à chaque patch, à partir des notes des développeurs sur le forum officiel Netmarble.
- La base sera aussi affichée sur le site (fiches).

### Étape 3b — Theorycraft et vidéos

- **4 vidéos par semaine**, une par mode, version **compte au maximum** uniquement (pas de F2P).
- Alexis ne joue pas : vidéos **100 % schémas** (composition, stuff, rotation sur une timeline, timings, estimation des dégâts). Aucun extrait de gameplay de tiers.
- Base de départ : les meilleures runs réelles du classement, améliorées ou remplacées par une équipe nouvelle.
- Tout ce qui n'est pas observé dans une run réelle est présenté comme une **estimation calculée**, sources citées. Objectif : « le guide le plus optimisé connu à date ».
- Chaque choix est justifié (pourquoi ce perso, ce set, cette rotation, ce timing).
- Voix : **clone de la voix d'Alexis** (outil gratuit à licence commerciale, ex. Chatterbox ou OpenVoice ; licence à vérifier). Échantillon de voix fourni par Alexis.
- Script rédigé en FR et en EN.

### Étape 4 — Réseaux sociaux

| Réseau | Format | Langue |
| --- | --- | --- |
| YouTube | 4 vidéos/semaine, une chaîne, 2 pistes audio (FR + EN) | FR + EN |
| YouTube Shorts | Extraits verticaux | EN + sous-titres FR |
| TikTok | Clips verticaux de **1 à 3 min** (rémunération > 1 min) | Voix EN + sous-titres FR |
| Discord | Serveur communautaire, salon « classement de la semaine » | FR + EN |
| X | Top 3 de chaque classement en image (HOTM : par porte ; BOT : season et challenge), **chaque mercredi** | FR + EN |
| Instagram Reels | Optionnel, réutilise les verticaux | EN + sous-titres FR |

- Même pseudo, même description, même photo de profil partout. Création des comptes : par Alexis.
- Intro et outro ≤ 5 s, renvoyant vers les autres comptes et le site.
- Classements publiés le **mercredi** (quasi définitifs avant le reset du jeudi 01h).
- Risque connu : 4 vidéos/semaine au même gabarit = risque de démonétisation pour contenu « produit en série ». Chaque vidéo doit apporter une analyse réellement différente.
- Seuils de monétisation : YouTube 1 000 abonnés + 4 000 h (8 000 h pour les candidatures dès le 01/02/2027) ou Shorts ; TikTok Creator Rewards 10 000 abonnés + 100 000 vues/30 j.
- Cocher « contenu modifié ou synthétique » sur YouTube (voix clonée), par prudence.

### Étape 5 — Site web

- Site statique sur GitHub Pages, FR + EN, qui lit les JSON du dépôt.
- Pages : classement par mode (HOTM : **une page par porte** ; BOT : season et challenge) → page build du joueur → fiches de la base de données → liens vers les réseaux (sur toutes les pages) → vidéos.
- Archives des semaines passées.
- Crédit et lien vers la vidéo source de chaque joueur ; moyen de demander le retrait.
- Mentions légales ; consentement cookies si statistiques ou publicité.
- Visuels : uniquement officiels autorisés (fan kit Netmarble) ou originaux.

## 5. Calendrier automatique (heure de Paris)

| Quand | Quoi | Où |
| --- | --- | --- |
| Tous les jours 20h00 | Nouvelles vidéos : tris 1-2, puis tris 3-4, builds du top 10, mise à jour du site | GitHub Actions (tris 1-2, site) + PC d'Alexis (tris 3-4) |
| Jeudi 01h00 | Passage final : classement de la semaine figé et archivé, nouvelle semaine ouverte | GitHub Actions + PC d'Alexis |
| Mercredi | Posts du classement (X, Discord) ; vidéos de la semaine | Alexis / outil de programmation |
| Après chaque passage | Contrôle des résultats + rapport court | Tâche planifiée Claude |

Note technique : les horaires GitHub Actions sont en UTC ; gérer le passage heure d'été / heure d'hiver.

## 6. Structure du dépôt GitHub

```
shadowledgerhq.github.io/
├── data/
│   ├── db/                  base de données du jeu (un JSON par catégorie) + patches.json
│   ├── icons/<categorie>/   banque d'icônes
│   ├── rules/<semaine>.json éléments autorisés par mode et par semaine
│   ├── runs/<semaine>/      classements publiés : poc.json, gb.json, bot-season.json, bot-challenge.json, hotm-gate-<n>.json
│   │                        non publiés (rank: null) : bot-variante-inconnue.json, hotm-gate-inconnue.json
│   │                        internes : _lectures.json (lectures de score des tris, entrée de classement.py), _videos.json (titre, chaîne, miniature, durée, mode_guess),
│   │                        _meta.json (fenêtre, gel), _boss.json (boss déduit), _rapport.md (rapport du passage)
│   ├── channels.json        chaînes YouTube suivies (channel_id, nom, playlist d'uploads, ajout manuel ou auto)
│   ├── builds/<semaine>/<mode>/   un JSON par build
│   ├── rejected/<semaine>.json
│   └── processed.json       vidéos déjà traitées ; `pc.sous_titres` = fait | absent | erreur
├── pipeline/                scripts Python
├── exports/<semaine>/       Excel et PowerPoint générés
├── videos/<semaine>/<mode>/ scripts FR/EN, storyboard
├── site/                    site statique
├── suivi/                   un SUIVI.md par discussion
└── .github/workflows/       daily.yml (20h), weekly.yml (jeudi 01h)
```

## 7. Discussions du Projet SLA

| # | Discussion | Rôle |
| --- | --- | --- |
| 1 | Étape 1 — Classements | Règles, contrôle des classements |
| 2 | Étape 2 — Builds | Règles, contrôle des builds, PowerPoint |
| 3 | Étape 3 — Theorycraft & vidéos | Analyses, scripts FR/EN, storyboards |
| 4 | Étape 4 — Réseaux | Comptes, logo, posts, calendrier de publication |
| 5 | Étape 5 — Site | Contenu, design, pages |
| 6 | Prompt | Architecture, contexte, instructions, skill |
| 7 | Tâche planifiée | Contrôle automatique et rapports |
| 8 | Code | Scripts Python, workflows GitHub Actions — **dans Claude Code** (écrit dans le dépôt) |
| 9 | Base de données | Base du jeu (3a) et banque d'icônes — **dans Claude Code** (écrit dans le dépôt) |

Les discussions d'étape décident **quoi** faire ; la discussion Code décide **comment** le coder.

Les discussions 8 et 9 se font dans Claude Code (claude.ai/code), sur le dépôt `shadowledgerhq/shadowledgerhq.github.io` : elles lisent `CLAUDE.md` et le skill du dépôt. Les autres se font dans le Projet SLA sur claude.ai.

### Aiguillage : quelle discussion pour quelle demande

| Demande d'Alexis | Discussion |
| --- | --- |
| Règles de recherche YouTube, tris, calcul des scores, vérification d'un classement | 1 — Classements |
| Éléments d'un build, statuts, PowerPoint, vérification d'un build | 2 — Builds |
| Meilleure team, rotation, script ou storyboard d'une vidéo, voix off | 3 — Theorycraft & vidéos |
| Logo, profils, posts, Discord, calendrier de publication, monétisation | 4 — Réseaux |
| Pages, design, textes ou bugs d'affichage du site | 5 — Site |
| Organisation du projet, CONTEXTE.md, instructions, skill, nouvelle règle | 6 — Prompt |
| Contrôle automatique, rapports, horaires des passages | 7 — Tâche planifiée |
| Écrire ou corriger un script, un workflow, une erreur technique, installation | 8 — Code (Claude Code) |
| Données du jeu (chasseurs, armes, artefacts…), icônes, mise à jour après un patch | 9 — Base de données (Claude Code) |

Règle de renvoi : si une demande relève d'une autre discussion, Claude ne la traite pas. Il indique la discussion à ouvrir et donne **un seul message prêt à coller**, dans cet ordre : (1) la ligne de rôle de la discussion cible, reprise de `PROMPTS_DISCUSSIONS.md` ; (2) la demande, avec le contexte utile (fichiers, décisions, ce qui est attendu). Il le fait aussi quand une discussion devient trop longue : **au 15e message d'Alexis** (puis à chaque nouveau message), il le signale en tête de réponse, recommande d'ouvrir une nouvelle discussion et donne un seul message prêt à coller : la ligne de rôle, le SUIVI à jour et la prochaine action précise.

## 8. Ordre de réalisation

1. **Mise en place** : dépôt GitHub, clé API YouTube en secret, skill installé, documents dans le projet. *Fait le 12/11/2026.*
2. **Base de données + banque d'icônes** (discussion 9).
3. **Pipeline étape 1** (discussions 1 et 8), avec les images de référence des scores.
4. **Site v1** : classements (discussion 5).
5. **Étape 2** : builds du top 10 + PowerPoint + pages builds.
6. **Réseaux** : comptes, logo, échantillon de voix, premières vidéos (discussions 3 et 4).
7. **Tâche planifiée** de contrôle (discussion 7).

## 9. Ce qu'Alexis doit fournir

- [ ] Images de référence : où lire le score. *Fait pour BOT et GB (client anglais, 13/11/2026) et pour POC et HOTM (client coréen).* Reste : libellés coréens et japonais de BOT et GB, libellés japonais de POC et HOTM, capture d'un BOT challenge.
- [ ] Images de référence : où lire chaque élément du build.
- [ ] Liste des éléments autorisés par mode (ombres, successeur, Sung Jin Woo…).
- [x] Clé API YouTube Data v3, rangée dans le secret GitHub `YOUTUBE_API_KEY`.
- [x] Organisation `shadowledgerhq` + dépôt public `shadowledgerhq.github.io` créés.
- [x] Comptes réseaux créés le 12/11/2026 : YouTube, TikTok, X, Instagram (@shadowledger_hq) + compte et serveur Discord « Shadow Ledger ». Reste : nom TikTok à passer en « Shadow Ledger » à partir du 19/11/2026.
- [ ] Échantillon de voix (1 à 2 min, propre, sans bruit).
- [ ] Trace écrite de l'autorisation de Sohoven (à conserver).

## 10. Points ouverts

- Le boss de chaque mode change-t-il chaque jeudi ? Si oui, une vidéo-guide publiée le mercredi ne sert qu'un jour : il faudrait la publier en début de semaine (vendredi ou samedi). À confirmer.
- Déclaration des revenus (statut micro-entrepreneur) quand les plateformes paieront.
