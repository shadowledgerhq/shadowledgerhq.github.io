# CLAUDE.md — Shadow Ledger (Projet SLA)

**Règles prioritaires (discussions 8 et 9 ; mises à jour le 15/11/2026)**

- **Compteur** : commence chaque réponse par « Message n/15 » (n = numéro de ta réponse précédente + 1). À partir de n = 15, ajoute « ⚠ Discussion longue » et donne un seul message prêt à coller pour une nouvelle discussion : ligne de rôle (PROMPTS_DISCUSSIONS.md, qui rappelle le droit de pousser dans ta zone), SUIVI à jour, prochaine action précise.
- **Autonomie** : ne demande jamais à Alexis une information que tu peux trouver toi-même (dépôt, slagate.com, forum Netmarble, vidéos YouTube, recherche web). Si c'est introuvable : hypothèse la plus prudente, marquée « à vérifier » avec sa source, et continue. Pour une décision : propose ton choix par défaut et avance. « Besoin d'Alexis » = seulement ce que lui seul peut faire (CONTEXTE.md, section 9).
- **Aucun relevé manuel** : ne jamais écrire « à relever à la main » ; une donnée non relevée reste `null` ou « à vérifier ».
- **Boîte** : pour un message vers les discussions 1 à 7, écris-le dans `docs/BOITE.md` (section du destinataire, format « - [à traiter] AAAA-MM-JJ — de Code — message »). Au démarrage, lis aussi `docs/BOITE.md` (sections 8-9 : messages des autres discussions pour toi ; Alexis te dit « lis ta boîte ») ; un message pour une autre discussion n'est **jamais recopié** à Alexis : annonce-le en une ligne (« Message de Code pour Classements dans docs/BOITE.md ») ; Code archive les messages traités dans `docs/archives/BOITE.md` au plus tard 7 jours après.

Ce dépôt contient tout le projet Shadow Ledger d'Alexis : classements hebdomadaires, builds, base de données du jeu, theorycraft, vidéos et site web pour *Solo Leveling: Arise* (modes POC, BOT, GB, HOTM).

## À lire en premier

- `docs/CONTEXTE.md` : la référence du projet (décisions, étapes, calendrier, structure). Il fait foi.
- `.claude/skills/shadow-ledger/SKILL.md` : conventions (glossaire, formats JSON, SUIVI.md, économie de crédits, checklists).
- `docs/PROMPTS_DISCUSSIONS.md` : rôle de chaque discussion.
- `suivi/<discussion>.md` : où en est chaque discussion. Reprendre à « En cours ».

Les discussions **8 — Code** et **9 — Base de données** s'ouvrent directement sur ce dépôt. Les discussions 1 à 7 se font dans le Projet SLA sur claude.ai et peuvent aussi pousser ici (accès `add_repo` en push, accepté par Alexis une fois par session). **Chaque discussion n'écrit que dans sa zone** (tableau « Droit de pousser », `docs/CONTEXTE.md` §7) ; hors de sa zone, elle écrit un message au propriétaire.

## Règles permanentes

1. Réponds en français. Le contenu public (site, vidéos, posts) existe en français et en anglais.
2. Gratuit d'abord : tout ce qu'un outil ou un site gratuit peut faire (Python, GitHub Actions, yt-dlp, OCR…) se fait hors de Claude. Claude écrit le code, vérifie et rédige.
3. Économise les crédits : réponses courtes, pas de reformulation, pas de récapitulatif, recherche web seulement si nécessaire, ne lis que les fichiers utiles.
4. Tiens `suivi/<discussion>.md` à jour et pousse-le à chaque étape (format du skill, 30 lignes max). **Ne l'affiche pas** à Alexis en fin de réponse : il n'est donné qu'au message 15, dans le message prêt à coller pour la nouvelle session.
5. Ne présente jamais une estimation comme un fait vérifié. Chaque donnée de jeu cite sa source et sa date de vérification.
6. Source principale des données et builds : slagate.com (autorisation de Sohoven obtenue). Autres sites seulement si l'info y manque ou est douteuse.
7. Si une demande contredit `docs/CONTEXTE.md`, signale-le et demande avant d'agir.
8. Une règle du skill à changer → section « Demandes de modif du skill » du SUIVI, sans modifier le skill toi-même.
9. Si une demande relève d'une autre discussion (tableau « Aiguillage » de `docs/CONTEXTE.md`, section 7), ne la traite pas : écris le message dans la boîte du destinataire (`docs/BOITE.md`, section du destinataire) avec le contexte utile, et dis seulement à Alexis « Message de <discussion> pour <discussion> dans docs/BOITE.md ». Ne recopie jamais le message. Quand la session devient trop longue : conseille d'en ouvrir une neuve et fournis le prompt de démarrage + le dernier SUIVI.
10. Au 15e message d'Alexis dans une session (puis à chaque nouveau message), signale-le en tête de réponse et recommande d'ouvrir une nouvelle session. Donne un seul message prêt à coller : la ligne de rôle de la discussion (`docs/PROMPTS_DISCUSSIONS.md`), le SUIVI à jour, et la prochaine action précise.

## Git

- Dépôt public : **aucun secret dans le code**. La clé YouTube est dans le secret GitHub `YOUTUBE_API_KEY`.
- Choix d'Alexis : tout est automatique. Travaille sur ta branche `claude/…`, committe et **pousse** après chaque étape terminée. Le workflow `.github/workflows/auto-merge-claude.yml` (ajouté par Alexis) fusionne aussitôt la branche dans `main`. N'ouvre pas de pull request et ne demande pas à Alexis de fusionner.
- Avant de modifier des fichiers, récupère `main` (`git pull origin main`).
- Si la fusion automatique échoue (conflit), récupère `main`, résous le conflit sur ta branche et pousse à nouveau.
- Ne laisse jamais de travail non poussé en fin de session.
- Messages de commit en français, courts : `db: ajoute les sets d'artefacts`, `suivi: base de données`.

## Commandes

- Avant pytest : `pip install opencv-python-headless` (sans OpenCV, 17 tests échouent à tort).
- Contrôle de la base : `python3 pipeline/check_db.py` (ajouter `--verbose` pour lister tous les avertissements). Code de sortie 1 s'il y a une erreur bloquante ; écrase `data/db/_rapport.md`. Lancé aussi par `.github/workflows/check-db.yml` à chaque push touchant `data/db/` ou `data/icons/`.
- Tests : `python3 -m pytest -q pipeline/tests` (ou chaque fichier `python3 pipeline/tests/test_<x>.py`).
- Pipeline étape 1 (stdlib, Python ≥ 3.9) : `python3 pipeline/etape1.py daily|weekly [--force] [--maintenant ISO]` (recherche YouTube + tri 1 + classement + rapport ; clé dans la variable `YOUTUBE_API_KEY`) ; `python3 pipeline/etape1.py classement [--semaine AAAA-MM-JJ]` ; `python3 pipeline/etape1.py relire [--semaine …]` (rejoue le tri 1 avec les règles actuelles, puis recalcule) ou `python3 pipeline/classement.py [AAAA-MM-JJ]` (recalcul seul).
- Paramètres de l'étape 1 : `pipeline/config/etape1.json` (requêtes, plages plausibles, quota, créneaux).
- pc.py (2000+ lignes) : le scinder en modules quand une spec touche ce fichier, sans changer son comportement, tests verts.
- Étape 2 (builds, SPEC_ETAPE2) : `python3 pipeline/builds.py [AAAA-MM-JJ] [--force]` (écrit `data/builds/<semaine>/…` + `_rapport.md`) puis `python3 pipeline/export_pptx.py [semaine] [--mode] [--sortie]` (`exports/<semaine>/builds/`, `pip install python-pptx opencv-python-headless`). Sur le PC : `python3 pipeline/pc.py builds [--semaine …] | [--video ID --mode bot]` (images de composition, `pipeline/composition.py`). Réglages (seuils par catégorie, masques, onglets, zones, extraction) : `pipeline/config/etape2.json`. Tests : `python3 pipeline/tests/test_etape2.py`.
- Rotation BOT (SPEC_ROTATION v2) : `py -3 pipeline\pc.py daily --video <ID>` relève la rotation des vidéos du top 3 BOT (`pipeline/config/rotation.json`, `version` à augmenter pour refaire) → `data/rotations/<semaine>/bot/<ID>.json` + `_rapport.md` ; diagnostic OCR dans `_crops/<ID>_ocr.json`. Tests : `python3 pipeline/tests/test_rotation.py`.
- Analyse porte × mode HOTM : `python3 pipeline/analyse_porte_mode.py`.
