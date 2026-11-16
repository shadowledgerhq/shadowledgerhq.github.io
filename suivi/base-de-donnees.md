# SUIVI — 9 Base de données — 2026-11-16 (session 7 : db_les_deux soldés ; session 6 : noyaux ; détail complet dans suivi/archives/base-de-donnees_2026-11-16_detail.md)
## Fait
- Base : 1 319+ entrées dans 18 fichiers de `data/db/`, 449 icônes, `check_db` OK (0 erreur). Guide officiel Netmarble lu (rates.json, game_rules.json, mode_rewards.json) ; 686 notes du forum EN (netmarble_notes.json) ; 27 notices d'équilibrage (balance_history, patches.json) ; bénédictions 59/59 ; gemmes, statues, runes (83/83 avec parent et valeurs), compétences de Jinwoo.
- Veille Netmarble : `tools/veille_netmarble.py` (boards 13, 14, 32) + tâche planifiée `trig_012uiWvELXgfSfsFxx5JcrWC` (07:43 UTC) ; 16/11 : « Rien de nouveau », pas de `a_traiter.md`.
- Session 6 : `tools/classer_a_verifier.py` (champ `verif` sur les 92 changements a_verifier : 48 db_aucune, 37 db_les_deux = base déjà à jour, 5 douteux, 2 ancienne_seule) ; ultime non possédée = « Commander's Authority » (notes 12/10 et 22/10/2026, à vérifier) ; Truth: Mutilate et The Commander's Touch confirmés.
- Noyaux (`cores.json`, 18 + `core-rules`), depuis les captures d'Alexis : 18 noyaux Légendaires, texte FR de 15/18, ~50 échantillons observés ; limit break 10→15→20 (20 matériaux + 100 000 / 300 000 or), niveau supérieur 200 or/EXP, amélioration 15 000 or + 5 matériaux ; max Légendaires par palier (Attaque/Défense/PV % 36,79 / 53,34 / 58,49 ; flat Attaque-Défense 3953 / 5473, PV 7906 / 10946 ; option 2 4799 / 6644 / 7289) ; formule du « niveau d'amélioration de stat » = floor(moyenne des 2 stats de (valeur − min initial)/(max du palier − min initial)), vérifiée sur 14 relevés.
- Session 7 (16/11) : veille « Rien de nouveau » (pas de a_traiter.md). 37 `db_les_deux` + 2 `db_ancienne_seule` relus dans les notices : 36 déjà appliqués (faux positifs, Meilin Fisher inclus : PV T4 32 %, T5 24/24/64 s en base), 2 appliqués (Vulcan's Rage 20→10 instances, Winter Fang Silver Mark 70→80 %), 1 non stockable (Lee Bora T5 Attaque 10→20 %, `palier_non_stocke`). Champs `verif`/`verif_note` ; `classer_a_verifier.py` ignore les entrées avec `verif_note`.
## En cours
- Intégrer les notes détaillées du patch du 19/11 dès que `data/veille/a_traiter.md` existe (annonce 110809 seule pour l'instant).
- Noms EN à confirmer : Overshadow, Power Unlocked (absents des 686 notes), Shadow Step (cité en 2024, lien déduit), Commander's Authority.
## À faire
- Texte FR de 3 noyaux Corps : Armure du Protecteur féroce (noir/rouge), Membres du Veilleur (violet), Main droite du spectre antique (bleu glacé) ; couleurs déduites des familles.
- 53 `a_verifier` restants (48 db_aucune, 5 analyse_douteuse) ; sets d'artefacts rééquilibrés 4 fois sans valeurs publiées.
- Vides sans source publique : effets d'amplification des paliers 4-5, bonus d'enregistrement des runes (sauf 3 compétences), noms des matériaux de noyau, 86 armes sans icône, noms FR d'armes de chasseurs, JA/KO de gemmes.
## Besoin d'Alexis
- Rien. Abandonnés par Alexis : captures des paliers 4-5 d'amplification (pas d'accès), 3e limit break des noyaux (pas de ressources), noyaux Rare/Héroïque.
## Demandes de modif du skill
- rien
