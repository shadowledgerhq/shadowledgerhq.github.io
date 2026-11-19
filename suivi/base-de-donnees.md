# SUIVI — 9 Base de données — 2026-11-19 (détail des sessions 1 à 11 : suivi/archives/base-de-donnees_2026-11-19_detail.md et _2026-11-16_detail.md)
## Fait
- Base : 18 fichiers dans `data/db/` (118 armes, 67 chasseurs), icônes de toutes les armes, cartes d'ombres (15), de chasseurs (58) et de puissances rémanentes (4) ; `check_db` OK, 0 erreur (19/11).
- Veille Netmarble : `tools/veille_netmarble.py` + tâche planifiée (07:43 UTC). 19/11 : 5 notes du patch intégrées (`netmarble_notes.json`, 691 notes), `a_traiter.md` vidé.
- 19/11 (session 11) équilibrage (notice 32/110996) : Sung Il-Hwan, Charlotte, Harper + armes Unbreakable Will, Prankster, Mischievous mis à jour dans les fiches ; multiplicateurs Lv.10 de Charlotte dans `patch_adjustments` (minimum Lv.1 inconnu).
- 19/11 : ajouts `thalia-de-rossi` (supporter Dark, SSR), `rosa-nera`, `kamish-wrath` (Dagger, Fire), `kamish-roar` (Polearm = hypothèse), noms FR et icônes de l'API slagate ; compétences et stats vides (aucune source chiffrée). Fiche `patches.json` « 2026-11-19 » (refonte du POC par paliers, armurerie, gemmes page 3, palier de combat 200, boss de guilde Dargo, etc.) ; annonce du 12/11 passée à « remplacée » ; `game_rules.json` : mise à jour du POC en `updates`.
- Outil `tools/apply_balance_notes.py` : option `--depuis AAAA-MM-JJ` (sans elle il écrase les vérifications manuelles et réécrit `patches.json`).
## En cours
- Cartes de chasseurs de tenues alternatives : attendent le rejeu PC `pc.py builds --semaine 2026-11-12 --refaire` (recadrages encore en 96 px au 19/11).
- Noms EN : Overshadow, Power Unlocked, Commander's Authority à vérifier en jeu.
## À faire
- 19/11 : recherche de sources — wiki Fandom : page Thalia De Rossi inexistante (404), aucune fiche chiffrée en ligne ; seulement des vidéos (YouTube/Reddit, aperçus sans valeurs). À relancer à la prochaine veille.
- Compléter Thalia De Rossi, Kamish's Wrath/Roar, Rosa Nera (compétences, paliers, stats) dès qu'une source existe (wiki Fandom, notes Netmarble) ; nom FR de Rosa Nera, type d'arme de Kamish's Roar.
- Règles du POC par paliers (durée, nombre de paliers, récompenses) : non publiées ; Dargo (boss de guilde) et Vulcan (DCZ) : pas de fiche.
- 15 `a_verifier` anciens (12 `fiche_anterieure_au_patch`, 3 `palier_non_stocke`) + 8 du 19/11 (Charlotte, valeurs Lv.10 déjà dans `patch_adjustments`).
- Vides sans source publique : amplification paliers 4-5, bonus d'enregistrement des runes, noms des matériaux de noyau, noms FR d'armes de chasseurs, JA/KO de gemmes.
## Besoin d'Alexis
- Rien (le rejeu PC du 12/11 est à lancer par Code).
## Demandes de modif du skill
- rien
