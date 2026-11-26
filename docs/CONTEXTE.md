# Projet SLA — Shadow Ledger : contexte de référence

Document de référence du projet. Toute discussion du Projet SLA s'y fie. En cas de contradiction avec une discussion, ce document fait foi. Mis à jour le 17/11/2026 (alignement sur SPEC_ETAPE1 v33 et SPEC_ETAPE2 v5 : GB = runs filmées seulement, Personal Record = identification du groupe, élément de la run, `data/rules` déduits des écrans, rotations relevées automatiquement ; v16 : POC et GB classés avec une seule run sûre ; BOT : un seul classement, saison de 4 + 1 semaines).

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
| Autonomie | Claude ne demande à Alexis que ce que lui seul peut faire (section 9). Information introuvable : hypothèse la plus prudente, marquée « à vérifier » avec sa source. Décision : choix par défaut proposé, et on avance. |
| Aucun relevé manuel | Jamais « à relever à la main » : une donnée non relevée reste `null` ou « à vérifier ». |
| Rien de public avant le lancement | Décision d'Alexis du 26/11/2026 : site, réseaux et vidéos se **préparent**, rien n'est publié avant son feu vert. GitHub Pages coupé (Settings → Pages) ; déploiement du site seulement par `deployer-site.yml` (manuel) ; toutes les pages en `<meta name="robots" content="noindex">` + `site/robots.txt` « Disallow: / » (contrôle : `pipeline/check_site.py`, test `test_prive_avant_lancement.py`), à retirer au lancement ; aucun script ne publie sur X, Discord, TikTok ou YouTube (test YouTube seulement en « Privé »). |

## 3. Les 4 modes

| Mode | Nom complet | Critère de classement | Runs |
| --- | --- | --- | --- |
| POC | Power Of Calamity | Dégâts max. Une run = une équipe : total = meilleure run de l'équipe 1 + meilleure run de l'équipe 2 | 2 (une par équipe) |
| BOT | Battlefield Of Time | Chrono le plus court, **un seul classement par semaine** (le mode Challenge a été retiré du jeu en mai 2026, source forum Netmarble). Saison = 4 semaines de jeu (1 boss par semaine) + 1 semaine de calcul sans classement | 1 |
| GB | Guild Boss | Rage Count (RC) le plus élevé. Une run = un groupe (6 chasseurs, équipes A + B, + SJW). **Seules les runs filmées (écran Results) comptent** : total = meilleure run filmée de chaque groupe (groupe 1 + groupe 2). Égalité de RC : départage par la somme des dégâts contrôlés. L'écran *Personal Record* sert seulement à identifier le groupe d'une run filmée, jamais à classer | 2 (une par groupe) |
| HOTM | Hall Of The Monarchs | Points les plus élevés, **par porte** : un classement par porte (제 n관문 / 第n関門), pas de classement HOTM global | 1 par porte |

- Reset de tous les modes : **jeudi 01h00, heure de Paris**.
- Une **semaine** est identifiée par la date du jeudi où elle commence (ex. `2026-11-12`).
- BOT, cycle de saison (dates **calculées**, à vérifier sur les vidéos) : S20 a commencé le 22/10/2026 ; semaine de calcul le 19/11/2026 ; S21 le 26/11/2026. Le titre `S<n>-<w>` (saison n, semaine w) sert de contrôle de semaine.
- Éléments autorisés (ombres, successeur, Sung Jin Woo, compétences, bénédictions) : **ils changent chaque semaine**. Ils sont enregistrés dans `data/rules/<semaine>.json`, un bloc par classement (`poc`, `bot`, `gb`, `hotm`), **déduits des écrans par le pipeline** (jamais relevés à la main) : `true` dès qu'une run sûre montre l'élément, `false` si ≥ 5 runs sûres de 5 chaînes différentes ne le montrent pas, sinon `null` (inconnu : jamais traité comme interdit). Source et date de vérification dans chaque bloc.
- **Rythme des boss** (à vérifier sur les données) : BOT chaque jeudi ; POC par saison ; GB par mise à jour régulière ; HOTM toutes les 2 semaines. Le boss reste déduit des données chaque semaine (`_boss.json`).

## 4. Les étapes

### Étape 1 — Classements (automatisée)

1. **Recherche** : YouTube Data API v3, vidéos publiées depuis le dernier reset. Quota ≈ 100 recherches/jour : requêtes ciblées.
2. **Tri 1** : score dans le titre, la description ou les sous-titres (Whisper si commentaire oral). Score du titre = provisoire tant qu'il n'est pas confirmé à l'image.
3. **Tri 2** : score lisible sur la miniature (OCR).
4. **Tri 3** : images des 10 premières secondes et des 30 dernières, 1 image / 2 s (OCR).
5. **Tri 4** : vidéo entière, 1 image / 10 s (OCR).
6. Vidéo sans score après le tri 4 → liste `rejected` (identifiant + raison), jamais réanalysée.

Règles :
- **Joueur = chaîne YouTube** (`channel_id`) ; le pseudo en jeu n'est pas la clé (au BOT, il est seulement noté dans `player_ingame`). Une ligne par joueur (HOTM : par porte), toutes vidéos de la semaine confondues.
- Shorts inclus ; lives et rediffusions de live exclus.
- POC et GB : somme des 2 meilleures runs distinctes, qui peuvent venir de **2 vidéos différentes** (POC : équipe 1 + équipe 2 ; GB : groupe 1 + groupe 2 ; jamais deux runs de la même équipe ou du même groupe). Une seule run `sur` : le joueur est **classé** (total = cette run, note « une seule run ») ; une 2e run trouvée plus tard dans la semaine, dans la même vidéo ou une autre, complète le total. Une seule run provisoire : `a_verifier`.
- Égalité : la vidéo publiée en premier passe devant (GB : d'abord la somme des dégâts).
- Score arrondi (« 2.1B ») : provisoire ; on garde la valeur exacte dès qu'elle est lue à l'image.
- Doublons : même run ré-uploadée ou postée en 2 langues → on garde la vidéo de la chaîne d'origine (la plus ancienne).
- Boss de la semaine **déduit des données** : libellé le plus fréquent parmi les runs sûres, à partir de 3 vidéos (`_boss.json`). Run avec un autre libellé → `a_verifier` ; libellé de la semaine précédente → `rejected`.
- Toutes régions et langues (OCR multilingue, formats 1.2B / 억 / 万).
- Champ `confiance` : `sur` ou `a_verifier`.
- **Élément de la run** (`runs_detail[i].element`, `element_source`) : POC et GB, `light|fire|water|wind|dark|null`, lu à l'écran (losanges du HUD, chasseurs reconnus) et/ou dans le titre. Il distingue 2 runs d'un même joueur quand le groupe ou l'équipe n'est pas lu.
- Compteurs animés (RC, Final Score) : seule la valeur finale compte ; les valeurs croissantes lues avant sont des étapes de l'animation (note « compteur animé »).
- **Seul l'écran RESULT donne un score sûr, sans exception.** GB : le `Personal Record` est lu et contrôlé (`Time Left in Season` prouve la bonne semaine, sinon `rejected`, raison `semaine_precedente`) mais il ne donne aucun score : il attribue seulement le groupe d'une run filmée de même RC.
- POC et HOTM : le score retenu est « 이번 기록 » (score de cette run) de l'écran RESULT, **jamais** « 기존 기록 » (ancien record) ni le score de l'écran de composition.
- BOT : score = chrono de la dernière phase de l'écran `Results` (= chrono du bandeau du bas). Un seul classement (`bot.json`). Titre `S<n>-<w>` de la semaine précédente → `rejected` (`semaine_precedente`) ; vidéo BOT publiée pendant la semaine de calcul → `a_verifier`.
- Contrôles de cohérence :
  - POC : total = SJW + successeur + 3 chasseurs ;
  - HOTM : total = 클리어 (clear) + 증명 보너스 (bonus de preuve) ;
  - BOT : phases cumulées croissantes, dernière phase = chrono du bandeau = `Play Time` tronqué à la seconde ;
  - GB : `Player's Score` + les 6 `Hunter Rank` = `Final Score` (écran Results).
- Vidéo publiée moins de 3 h après le reset : note d'alerte « semaine précédente ? », jamais un rejet.
- Légendes ajoutées par l'auteur de la vidéo (titre, texte incrusté) : au mieux un score provisoire, à confirmer sur l'écran RESULT.
- HOTM : une ligne par joueur **et par porte** ; porte illisible (écran et titre) → `hotm-gate-inconnue.json`, jamais publié.
- *Décisions d'Alexis des 13 et 14/11/2026 (discussion 1 — Classements).* Détail complet : `docs/SPEC_ETAPE1.md` (état actuel ; historique dans `docs/archives/`).

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
- **Rotation** : relevée **automatiquement** dans les vidéos du top 10 (`data/rotations/`, format en section 6), jamais à la main. Un guide POC, GB ou HOTM peut servir **plusieurs semaines** tant que le boss et les règles ne changent pas.

### Étape 4 — Réseaux sociaux

| Réseau | Format | Langue |
| --- | --- | --- |
| YouTube | 4 vidéos/semaine, une chaîne, 2 pistes audio (FR + EN) | FR + EN |
| YouTube Shorts | Extraits verticaux | EN + sous-titres FR |
| TikTok | Clips verticaux de **1 à 3 min** (rémunération > 1 min) | Voix EN + sous-titres FR |
| Discord | Serveur communautaire, salon « classement de la semaine » | FR + EN |
| X | Top 3 de chaque classement en image (HOTM : par porte), **chaque mercredi** | FR + EN |
| Instagram Reels | Optionnel, réutilise les verticaux | EN + sous-titres FR |

- **Avant le lancement : rien n'est publié** (voir §2) ; un envoi de test sur YouTube se fait seulement en « Privé ».
- Même pseudo, même description, même photo de profil partout. Création des comptes : par Alexis.
- Intro et outro ≤ 5 s, renvoyant vers les autres comptes et le site.
- Classements publiés le **mercredi** (quasi définitifs avant le reset du jeudi 01h).
- Risque connu : 4 vidéos/semaine au même gabarit = risque de démonétisation pour contenu « produit en série ». Chaque vidéo doit apporter une analyse réellement différente.
- Seuils de monétisation : YouTube 1 000 abonnés + 4 000 h (8 000 h pour les candidatures dès le 01/02/2027) ou Shorts ; TikTok Creator Rewards 10 000 abonnés + 100 000 vues/30 j.
- Cocher « contenu modifié ou synthétique » sur YouTube (voix clonée), par prudence.

### Étape 5 — Site web

- **Avant le lancement : site non public** (Pages coupé, `noindex`, `robots.txt` « Disallow: / », déploiement manuel `deployer-site.yml`). Au lancement : retirer `noindex` et `robots.txt`, réactiver Pages (Source : GitHub Actions), lancer le workflow avec `lancement` = true.

- Site statique sur GitHub Pages, FR + EN, qui lit les JSON du dépôt.
- Pages : classement par mode (HOTM : **une page par porte**) → page build du joueur → fiches de la base de données → liens vers les réseaux (sur toutes les pages) → vidéos.
- Archives des semaines passées.
- Crédit et lien vers la vidéo source de chaque joueur ; moyen de demander le retrait.
- Mentions légales ; consentement cookies si statistiques ou publicité.
- Visuels : uniquement officiels autorisés (fan kit Netmarble) ou originaux.

## 5. Calendrier automatique (heure de Paris)

| Quand | Quoi | Où |
| --- | --- | --- |
| Tous les jours 19h00 | Nouvelles vidéos : tris 1-2, puis tris 3-4, builds du top 10, mise à jour du site | GitHub Actions (tris 1-2, site) + PC d'Alexis (tris 3-4) |
| Jeudi 01h00 | Passage final : classement de la semaine figé et archivé, nouvelle semaine ouverte | GitHub Actions + PC d'Alexis |
| Mercredi | Posts du classement (X, Discord) ; vidéos de la semaine | Alexis / outil de programmation |
| Après chaque passage | Contrôle des résultats + rapport court | Tâche planifiée Claude |

Avant le lancement, les lignes « Mercredi : posts » et « mise à jour du site » sont préparées mais non publiées (§2). Passages GitHub : `midi.yml` 12h00 (v43) + `daily.yml` 19h00 ; PC 19h30, 21h30, 23h30.

Note technique : les horaires GitHub Actions sont en UTC ; gérer le passage heure d'été / heure d'hiver.

## 6. Structure du dépôt GitHub

```
shadowledgerhq.github.io/
├── data/
│   ├── db/                  base de données du jeu (un JSON par catégorie) + patches.json
│   ├── icons/<categorie>/   banque d'icônes
│   ├── rules/<semaine>.json éléments autorisés par mode et par semaine
│   ├── runs/<semaine>/      classements publiés : poc.json, gb.json, bot.json, hotm-gate-<n>.json
│   │                        non publié (rank: null) : hotm-gate-inconnue.json
│   │                        internes : _lectures.json (lectures de score des tris, champ `regles`, entrée de classement.py), _videos.json (titre, chaîne, miniature, durée, mode_guess),
│   │                        _meta.json (fenêtre, gel), _boss.json (boss déduit), _rapport.md (rapport du passage)
│   ├── channels.json        chaînes YouTube suivies (channel_id, nom, playlist d'uploads, ajout manuel ou auto)
│   ├── builds/<semaine>/<mode>/   un JSON par build
│   ├── rotations/<semaine>/<mode>/<video_id>.json   rotation relevée automatiquement
│   ├── rejected/<semaine>.json
│   └── processed.json       vidéos déjà traitées ; `pc.sous_titres` = fait | absent | erreur
├── pipeline/                scripts Python
├── exports/<semaine>/       Excel et PowerPoint générés
├── videos/<semaine>/<mode>/ scripts FR/EN, storyboard
├── site/                    site statique
├── suivi/                   un SUIVI.md par discussion
└── .github/workflows/       daily.yml (19h), weekly.yml (jeudi 01h)
```

**Format d'une rotation** (`data/rotations/<semaine>/<mode>/<video_id>.json`) — **provisoire, non codé** (spécification à venir : `docs/SPEC_ROTATION.md`, discussion 3) : `{"video_id": "", "week": "", "mode": "", "run_start_t": 0, "events": [{"t": 0, "hunter": "", "slot": "", "source": "", "confidence": "sur | a_verifier"}], "limites": ""}`. `t` = secondes depuis `run_start_t` ; `hunter` = `id` de la base ; `slot` = compétence utilisée ; `source` = comment l'événement a été relevé ; `limites` = ce que le relevé ne couvre pas. Un événement non relevé n'est pas écrit (jamais complété à la main).

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

Les discussions d'étape décident **quoi** faire ; la discussion Code décide **comment** le coder. Chaque spécification est poussée dans `docs/` du dépôt avant d'être envoyée à Code ; Code pousse toujours sur une branche `claude/…` (fusion automatique dans `main`).

Les discussions 8 et 9 s'ouvrent directement sur le dépôt `shadowledgerhq/shadowledgerhq.github.io` dans Claude Code (claude.ai/code ; sinon `add_repo` en push) : elles lisent `CLAUDE.md` et le skill du dépôt. Les autres se font dans le Projet SLA sur claude.ai.

**Boîtes** : chaque discussion lit `claude/BOITE.md` et `docs/BOITE.md` au démarrage. Un message traité est retiré de `claude/BOITE.md` ; pour `docs/BOITE.md`, Code l'archive dans `docs/archives/BOITE.md` au plus tard 7 jours après son traitement.

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

**Boîte aux lettres (15/11/2026, rappel 17/11/2026).** Les discussions 8 (Code) et 9 (Base de données) écrivent dans le dépôt ; les discussions 1 à 7 n'y accèdent pas en continu. Tout message de 8 ou 9 pour les discussions 1 à 7 s'écrit dans `docs/BOITE.md`, dans la section du destinataire, au format `- [à traiter] AAAA-MM-JJ — de Code — message`. Le destinataire lit sa section au démarrage et passe les messages traités à `[traité]`. Alexis n'a pas à faire le courrier.

**Compteur (15/11/2026, rappel 17/11/2026).** « Compteur : commence chaque réponse par "Message n/15" (n = numéro de ta réponse précédente + 1). À partir de n = 15, ajoute "⚠ Discussion longue" et donne un seul message prêt à coller pour une nouvelle discussion : ligne de rôle (PROMPTS_DISCUSSIONS.md), SUIVI à jour, prochaine action précise. »

**Autonomie (15/11/2026, rappel 17/11/2026) et aucun relevé manuel.** Jamais « à relever à la main » : une donnée non relevée reste `null` ou « à vérifier ». « Ne demande jamais à Alexis une information que tu peux trouver toi-même (dépôt, slagate.com, forum Netmarble, vidéos YouTube, recherche web). Si c'est introuvable : hypothèse la plus prudente, marquée "à vérifier" avec sa source, et continue. Pour une décision : propose ton choix par défaut et avance. "Besoin d'Alexis" = seulement ce que lui seul peut faire (section 9). »

## 8. Ordre de réalisation

1. **Mise en place** : dépôt GitHub, clé API YouTube en secret, skill installé, documents dans le projet. *Fait le 12/11/2026.*
2. **Base de données + banque d'icônes** (discussion 9).
3. **Pipeline étape 1** (discussions 1 et 8), avec les images de référence des scores.
4. **Site v1** : classements (discussion 5).
5. **Étape 2** : builds du top 10 + PowerPoint + pages builds.
6. **Réseaux** : comptes, logo, échantillon de voix, premières vidéos (discussions 3 et 4).
7. **Tâche planifiée** de contrôle (discussion 7).
8. **Lancement** : feu vert d'Alexis, puis retrait de `noindex`/`robots.txt`, Pages, premières publications (§2).

## 9. Ce qu'Alexis seul peut faire

- [ ] Échantillon de voix (1 à 2 min, propre, sans bruit).
- [ ] Trace écrite de l'autorisation de Sohoven (à conserver).
- [ ] Couper GitHub Pages (Settings → Pages), puis donner le feu vert du lancement.
- [ ] Passer le nom TikTok en « Shadow Ledger » le 19/11/2026.
- Ouvrir les discussions 8 et 9 sur le dépôt (Claude Code).
- En continu : connexions et comptes, secrets (clés, GitHub), manipulations sur son PC (Planificateur de tâches, essais `pc.py`), mise à jour des instructions du Projet SLA, messages vers les discussions 8 et 9 (celles-ci n'ont pas de boîte : Alexis colle la demande).

Tout le reste (images de référence, libellés, listes d'éléments, données du jeu, recherches) est cherché par Claude lui-même (voir « Autonomie », section 7).

## 10. Points ouverts

- Le boss change-t-il chaque jeudi ? **Oui pour le BOT** (1 boss par semaine, source Netmarble). Une vidéo-guide BOT publiée le mercredi ne sert donc qu'un jour : la publier en début de semaine (vendredi ou samedi). POC par saison, GB par mise à jour régulière, HOTM toutes les 2 semaines (à vérifier) : boss déduit des données par la discussion 1.
- Déclaration des revenus (statut micro-entrepreneur) quand les plateformes paieront.
- Alignement complet sur `claude/CONTEXTE.md` du Projet (version du 26/11) : fichier absent du dépôt, §2 ci-dessus seule mise à jour faite ; à coller dans `docs/` pour finir (BOITE §6).
