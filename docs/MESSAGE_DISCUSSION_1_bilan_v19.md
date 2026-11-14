Discussion « Étape 1 — Classements ». Ton rôle : définir et contrôler les règles des classements des 4 modes (recherche YouTube, tris 1 à 4, calcul des scores, dédoublonnage, fichiers runs/rejected). Tu ne codes pas : tu rédiges les spécifications pour la discussion Code et tu vérifies les classements produits.

Bilan de la discussion Code : repli assoupli (SPEC v18 §3.1) codé (v19). Lis docs/SPEC_ETAPE1.md, suivi/code.md (section « En cours ») et docs/essais/ocr/_resume_6videos.json sur main.

1. Code : `ecrans.controle_results_sans_hunter_rank` : la condition 4 devient non bloquante si (a) Final Score / 1,02 ≤ dernier Points HUD (chrono ≤ 5 s, plausibles) ≤ Final Score, (b) Rage Count identique sur ≥ 3 images sans lecture discordante (étapes d'animation non comptées), (c) conditions 1 et 2 remplies. Notes : « contrôle sans Hunter Rank » + « Hunter Rank incohérents ignorés (HUD) ». Sans HUD, condition 4 obligatoire. 14 fichiers de test OK. `regles` reste 17.

2. Rejeu hors ligne des lectures sauvegardées de l'essai du 14/11 (code v19) : Oj_ 137 sur (note « Hunter Rank incohérents ignorés (HUD) ») ; T5dR 156 sur ; MJ2 160 a_verifier ; vYtR 162 a_verifier ; awb Results a_verifier (pas de HUD, sa ligne classée 189 vient du Personal Record) ; nh2D 332 sur. Conforme à tes attendus. Ce n'est PAS la validation réelle : l'essai du 14/11 a été lancé avec l'ancien code (regles 13).

3. Reste : Alexis relance les 6 vidéos avec le code à jour ; le nouveau _resume_6videos.json sera publié sur main. Contrôle alors : awb 189 (record), nh2D 332, T5dR 156 sur (+ note « écart titre/écran : titre 159 »), Oj_ 137 sur non additionné à 156 (note « groupes inconnus : 2e run non additionnée »), MJ2 160 et vYtR 162 a_verifier, Points HUD MJ2 rejetés, regles 17.
