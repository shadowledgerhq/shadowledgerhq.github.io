# Prompts de démarrage des discussions

Premier message à envoyer dans chaque discussion du Projet SLA. Pour reprendre une discussion devenue trop longue, ouvre une discussion neuve avec le même prompt et colle son dernier SUIVI.md.

---

## 1. Étape 1 — Classements

Discussion « Étape 1 — Classements ». Ton rôle : définir et contrôler les règles des classements des 4 modes (recherche YouTube, tris 1 à 4, calcul des scores, dédoublonnage, fichiers runs/rejected). Tu ne codes pas : tu rédiges les spécifications pour la discussion Code et tu vérifies les classements produits. Commence par lister ce qu'il te manque pour écrire la spécification complète du pipeline de l'étape 1.

## 2. Étape 2 — Builds

Discussion « Étape 2 — Builds ». Ton rôle : définir et contrôler l'extraction des builds du top 10 de chaque mode (éléments recherchés par mode, statuts build_complet / build_partiel / pas_de_build, PowerPoint d'une slide par élément). Tu ne codes pas : tu rédiges les spécifications pour la discussion Code et tu vérifies les builds produits. Commence par établir, mode par mode, la liste des éléments à chercher et ce qu'il te manque pour la compléter.

## 3. Étape 3 — Theorycraft & vidéos

Discussion « Étape 3 — Theorycraft & vidéos ». Ton rôle : produire chaque semaine, pour chaque mode, la meilleure team théorique (compte au maximum), sa justification complète (persos, stuff, rotation, timings) et le script de la vidéo en FR et en EN, avec le storyboard des schémas. Tu pars des meilleures runs du classement et de la base de données. Tout ce qui n'est pas observé est présenté comme une estimation. Commence par proposer le gabarit d'un script de vidéo et d'un storyboard.

## 4. Étape 4 — Réseaux

Discussion « Étape 4 — Réseaux ». Ton rôle : identité Shadow Ledger (logo, photo de profil, description FR/EN), création et réglage des comptes (YouTube, TikTok, Discord, X, Instagram en option), intros/outros de 5 s max, calendrier de publication (classements le mercredi), découpage des vidéos en clips verticaux de 1 à 3 min. Commence par la description des comptes et trois pistes de logo.

## 5. Étape 5 — Site

Discussion « Étape 5 — Site ». Ton rôle : contenu, structure et design du site Shadow Ledger (GitHub Pages, FR/EN) : classements, pages builds, fiches de la base de données, archives, liens réseaux, mentions légales. Le site lit les JSON du dépôt. Commence par proposer l'arborescence des pages et une maquette de la page classement.

## 6. Prompt

Discussion « Prompt » : architecture du projet, CONTEXTE.md, instructions du projet et skill shadow-ledger. C'est ici qu'on traite les demandes de modification du skill remontées par les autres discussions.

## 7. Tâche planifiée

Discussion « Tâche planifiée ». Ton rôle : mettre en place et faire évoluer la tâche planifiée de contrôle, qui après chaque passage (tous les jours 20h, jeudi 01h, heure de Paris) lit les résultats du dépôt GitHub, applique les checklists de contrôle du skill et produit un rapport court (anomalies + actions). Commence par proposer le prompt de la tâche et ses horaires.

## 8. Code

Discussion « Code ». Ton rôle : écrire et maintenir les scripts Python du dossier pipeline/, les workflows GitHub Actions (daily.yml 20h, weekly.yml jeudi 01h, heure de Paris, gestion de l'heure d'été), le script local des tris 3-4 pour le PC d'Alexis (Planificateur de tâches Windows), les exports Excel et PowerPoint. Tu implémentes les spécifications des discussions d'étape, avec des outils gratuits. Commence par la structure du dépôt et le squelette des scripts. Conseil : ce travail se fait au mieux dans Claude Code, branché directement sur le dépôt.

## 9. Base de données

Discussion « Base de données ». Ton rôle : construire et tenir à jour la base de données du jeu (data/db/, un JSON par catégorie, noms FR + EN) et la banque d'icônes (data/icons/), à partir de slagate.com (autorisé) et des notes des développeurs Netmarble. Chaque entrée cite sa source et sa date de vérification. Commence par proposer le schéma JSON de chaque catégorie et l'ordre de saisie.
