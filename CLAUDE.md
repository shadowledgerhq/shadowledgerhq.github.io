# CLAUDE.md — Shadow Ledger (Projet SLA)

Ce dépôt contient tout le projet Shadow Ledger d'Alexis : classements hebdomadaires, builds, base de données du jeu, theorycraft, vidéos et site web pour *Solo Leveling: Arise* (modes POC, BOT, GB, HOTM).

## À lire en premier

- `docs/CONTEXTE.md` : la référence du projet (décisions, étapes, calendrier, structure). Il fait foi.
- `.claude/skills/shadow-ledger/SKILL.md` : conventions (glossaire, formats JSON, SUIVI.md, économie de crédits, checklists).
- `docs/PROMPTS_DISCUSSIONS.md` : rôle de chaque discussion.
- `suivi/<discussion>.md` : où en est chaque discussion. Reprendre à « En cours ».

Les sessions Claude Code sur ce dépôt servent surtout aux discussions **8 — Code** et **9 — Base de données**, qui doivent écrire des fichiers. Les autres discussions se font dans le Projet SLA sur claude.ai.

## Règles permanentes

1. Réponds en français. Le contenu public (site, vidéos, posts) existe en français et en anglais.
2. Gratuit d'abord : tout ce qu'un outil ou un site gratuit peut faire (Python, GitHub Actions, yt-dlp, OCR…) se fait hors de Claude. Claude écrit le code, vérifie et rédige.
3. Économise les crédits : réponses courtes, pas de reformulation, pas de récapitulatif, recherche web seulement si nécessaire, ne lis que les fichiers utiles.
4. Chaque session de travail se termine par la mise à jour de `suivi/<discussion>.md` (format du skill, 30 lignes max).
5. Ne présente jamais une estimation comme un fait vérifié. Chaque donnée de jeu cite sa source et sa date de vérification.
6. Source principale des données et builds : slagate.com (autorisation de Sohoven obtenue). Autres sites seulement si l'info y manque ou est douteuse.
7. Si une demande contredit `docs/CONTEXTE.md`, signale-le et demande avant d'agir.
8. Une règle du skill à changer → section « Demandes de modif du skill » du SUIVI, sans modifier le skill toi-même.
9. Si une demande relève d'une autre discussion (tableau « Aiguillage » de `docs/CONTEXTE.md`, section 7), ne la traite pas : indique la discussion à ouvrir et donne un message prêt à coller avec le contexte utile. Fais de même quand la session devient trop longue : conseille d'en ouvrir une neuve et fournis le prompt de démarrage + le dernier SUIVI.

## Git

- Dépôt public : **aucun secret dans le code**. La clé YouTube est dans le secret GitHub `YOUTUBE_API_KEY`.
- Choix d'Alexis : tout est automatique. Travaille sur ta branche `claude/…`, committe et **pousse** après chaque étape terminée. Le workflow `.github/workflows/auto-merge-claude.yml` (ajouté par Alexis) fusionne aussitôt la branche dans `main`. N'ouvre pas de pull request et ne demande pas à Alexis de fusionner.
- Avant de modifier des fichiers, récupère `main` (`git pull origin main`).
- Si la fusion automatique échoue (conflit), récupère `main`, résous le conflit sur ta branche et pousse à nouveau.
- Ne laisse jamais de travail non poussé en fin de session.
- Messages de commit en français, courts : `db: ajoute les sets d'artefacts`, `suivi: base de données`.

## Commandes

Aucune pour l'instant. La discussion 8 (Code) les ajoutera ici (installation Python, lancement du pipeline, tests).
