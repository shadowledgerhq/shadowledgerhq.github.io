# SPEC_ROTATION — relevé automatique de l'ordre des compétences — v2.1 (2026-11-18)

Demandeur : discussion 3 (Theorycraft). Code : discussion 8. Aucune action manuelle d'Alexis.
But : pour les meilleures runs, la liste horodatée des compétences utilisées pendant la run. Elle sert de timeline aux vidéos de l'étape 3b.

## 1. Périmètre
- BOT d'abord : top 3 de data/runs/<semaine>/bot.json (lignes provisoires acceptées). POC, GB et HOTM (top 3 par classement ou par porte) (BOT validé en v2 ; activés le 18/11 : top 3 par mode, HOTM par porte, v2.1).
- Où : passage PC (pipeline/pc.py), après les tris 3-4, sur la vidéo déjà téléchargée (aucun second téléchargement). Le cloud ne peut pas télécharger YouTube (blocage anti-bot) : le PC est obligatoire.
- Une vidéo n'est traitée qu'une fois : data/processed.json, pc.rotation = fait | absent | erreur.
- Budget de départ : 3 vidéos par mode et par passage.

## 2. Méthode
1. Bornes de la run : run_start_t = première image où le HUD est visible, c'est-à-dire où un bouton de compétence a une luminance ≥ 30 (seuil `visible_luminance`, réglable dans rotation.json) ; run_end_t = écran Results (runs_detail[i].t, détection existante, ecrans.py). Sans Results lu (ligne provisoire) : run_end_t = dernière image avec HUD et limite bornes-incertaines. Si un chrono provisoire existe (bot.json, titre ou miniature), l'écart duration_s − chrono est écrit dans _rapport.md. Les images hors bornes sont ignorées. **v1.4** : duration_s (temps vidéo) n'est jamais comparé au chrono à 0,5 s près (le HUD reste affiché pendant les transitions de phase et les ralentis). La run = le dernier groupe de segments de HUD avant le Results : on remonte les segments tant que la coupure ≤ `coupure_run_s` (10 s ; une cinématique d'ultime dure 6-7 s) ; une coupure plus longue = un essai précédent (limite `essais-precedents`, a-923ClD9Rc : 12,5-43 s puis 56,5-104 s). duration_s > 2,5 × chrono → limite bornes-incertaines (signalée, pas un échec). Vidéo à 2 runs (POC, GB) : un objet par run dans runs[], dans l'ordre de runs_detail. **v2.1 — fin de run au chrono final** : si t_game est lu et que le dernier t_game lu = chrono du Results (ou chrono provisoire) ± 0,5 s, run_end_t = t du premier événement dont t_game atteint ce chrono ; tout ce qui suit sort de la run (a-923ClD9Rc : fin à 97,9 s, le `sjw_skill_1` à 101,0 s avec t_game figé à 19.558 est exclu). Sinon : règle précédente.
2. Échantillonnage : 10 images/s entre les bornes, en 720p.
3. Calibration du HUD (format 16:9), dans pipeline/config/rotation.json : zones des boutons skill_1, skill_2, ultimate (chasseur actif), des boutons de SJW, des portraits de l'équipe et de la jauge de noyau. Établie à partir des images de wJ9CwjKwyco (client anglais), puis vérifiée sur a-923ClD9Rc (client japonais) et Lt84IhMjBvM. Format autre que 16:9 : limites ["format"] et aucun événement.
4. Détection (entre deux images successives) :
   - skill_1, skill_2, ultimate, sjw_* : le bouton passe de « prêt » à « en recharge » (assombrissement et chiffre de recharge). L'événement est daté à la première image en recharge. Le chiffre lu va dans cooldown_read : null tant que les zones ne sont pas calibrées ; l'OCR du chiffre est branché dans la même session que la calibration.
   - core : la jauge de noyau se vide.
   - tag : le portrait du perso actif change. trigger = qte si une bannière ou un effet de QTE est reconnu, sinon inconnu (QTE et soutien ne sont pas distingués de façon sûre).
   - Les attaques de base ne sont pas relevées.
   - Deux détections du même bouton à moins de 0,5 s d'écart = un seul événement.
   - **v2.1 — recharge entamée** : si la 1re lecture valide d'un bouton (au début de la run ou après des lectures vides) donne un chiffre < 0,6 × sa recharge de base connue (base de données ; SJW ultime : 60 s), c'est une recharge déjà en cours : aucun événement. Recharge de base inconnue : règle précédente. Nombre de cas écrit dans _rapport.md (`recharges-entamees`). Origine : a-923ClD9Rc, faux `sjw_ultimate` à t_game 13.456 et 15.461 (une seule recharge 08 → 02 déjà en cours).
   - **v2.1 — tag** : deux `tag` à moins de `tag_min_s` (4 s, réglable ; recharge du changement ≈ 5 s, wJ9CwjKwyco) = un seul événement, le premier. Le chiffre de recharge du changement est masqué dans la comparaison des portraits. Origine : a-923ClD9Rc, 15 `tag` à 0,5 s d'écart.
5. Confiance : sur si cooldown_read correspond à la recharge de la base (hunters.json, sjw_skills.json) à ±1 s près, ou si le perso est identifié et que l'ordre respecte les recharges ; sinon a_verifier.
6. Identité : hunter = id de la base si le portrait correspond (cartes de référence de la discussion 9, data/icons/hunters_cartes/, comparées par SIFT ; pas data/icons/hunters/, dont les illustrations ne sont pas celles des cartes du jeu), sjw pour Sung Jin Woo, sinon inconnu. Les compétences SJW (sjw.skills du build) donnent l'id de la compétence (skill_id) quand il est connu.
7. Images de tiers : aucune image complète de la vidéo n'est poussée. Seuls les recadrages des boutons et portraits (comme data/builds/.../_crops/) peuvent l'être, dans data/rotations/<semaine>/<mode>/_crops/. Exception, pour la calibration seulement : de grands recadrages du bas de l'image (≤ 960 px, 3 instants par vidéo) sont permis ; ils sont supprimés du dépôt dans le commit qui fixe les zones.

8. **t_game (v1.4)** : chrono du combat lu par l'OCR dans le HUD (zone `zones.chrono`, formats `mm:ss.mmm` ou `ss.mmm`) sur le recadrage 1080p le plus proche de chaque événement (± `t_game_tolerance_s` 0,5 s), seulement si le HUD est affiché ; illisible ou zone non calibrée = null. t_run reste le temps vidéo. Tant que `zones.chrono` est null, le passage garde 3 recadrages du haut de l'image (≤ 960 px) dans `_crops/` pour la calibrer (supprimés au commit de la zone).

## 3. Sortie : data/rotations/<semaine>/<mode>/<video_id>.json
{"spec": 1, "video_id": "wJ9CwjKwyco", "week": "2026-11-12", "mode": "bot", "gate": null, "run_id": "bot-2026-11-12-wJ9CwjKwyco",
 "runs": [{"run_index": 1, "run_start_t": 0.0, "run_end_t": 0.0, "duration_s": 0.0,
   "events": [{"t": 0.0, "t_run": 0.0, "hunter": "sjw | <id> | inconnu", "slot": "skill_1", "skill_id": null, "trigger": null, "cooldown_read": null, "t_game": null, "source": "hud-recharge", "confidence": "a_verifier"}],
   "limites": []}]}
- slot : skill_1, skill_2, ultimate, core, tag, sjw_skill_1, sjw_skill_2, sjw_ultimate, sjw_qte.
- source : hud-recharge, portrait, jauge, ocr. confidence : sur, a_verifier.
- t = secondes dans la vidéo ; t_game = chrono du combat (s) lu dans le HUD ou null ; t_run = t − run_start_t. trigger seulement pour tag (qte | inconnu).
- limites : format, hud-non-trouve, bornes-incertaines, chasseurs-inconnus.
- Rapport du passage : data/rotations/<semaine>/_rapport.md (vidéos, nombre d'événements, a_verifier, limites).

## 4. Exemple réel : wJ9CwjKwyco (BOT 2026-11-12, X SLA, Baruka S20)
Déjà connu (à vérifier) :
- vidéo de 49 s (_videos.json) ; écran de composition à 38-46 s (build provisoire) ;
- chrono de la run : 19,926 s, lu sur la miniature (i.ytimg.com, 17/11/2026). bot.json indique 19,0 s (lu dans le titre). La capture Results de REFERENCE_ECRANS_BOT.md (13/11 : Baruka, phases cumulées 9,281 / 14,986 / 19,926 s) correspond probablement à cette run ;
- SJW : arme The Huntsman, QTE 1 Foulée de l'ombre (build provisoire).
Relevé réel (passage PC v9, 18/11 soir ; `data/rotations/2026-11-12/bot/`) :
- wJ9CwjKwyco : run 0-37 s, 12 événements (4 SJW), `t_game` lu sur 12 sur 12 (2,366 → 19,384 s), phases du Results 9,281 / 14,986 / 19,926 s dans la fenêtre. Critères 1, 3, 5, 6 OK ; 2 et 4 non évaluables.
- a-923ClD9Rc (GUIDE « ▶▶0.5x », ralentis) : run 56,5-104 s (dernier groupe de HUD), 24 événements (4 SJW), `t_game` lu sur 20 sur 24 (2,219 → 19,558 s, croissant, dernier = chrono), phases du Results non lues (non évaluable). Critères 1, 3, 5, 6 OK ; 2 et 4 non évaluables ; limites `bornes-incertaines` (durée 2,4 × le chrono : ralentis) et `essais-precedents`.
Validé : les critères ci-dessus passent sur les deux vidéos de calibration. Chasseurs inconnus (`chasseurs-inconnus`) : événements de chasseurs non relevés tant que la composition n'est pas lue.
Critères d'acceptation (v1.4, contrôles du rapport ; « non évaluable » n'est pas un échec) :
1. duration_s ≥ chrono − 0,5 s ; si duration_s > 2,5 × chrono : limite bornes-incertaines (signalée, pas un échec) ;
2. fin avant la composition si son temps est connu (> 0), sinon non évaluable (a-923 et Lt84 : composition = 0 s) ;
3. au moins un événement pour SJW ;
4. au moins un événement par chasseur actif identifié ; chasseur inconnu : non évaluable ;
5. aucune compétence relancée avant la fin de sa recharge connue ;
6. si t_game est lu : croissant, dernier t_game ≤ chrono, et phases du Results dans [premier t_game ; chrono + 0,5 s] (validé par la discussion 3, 18/11 : la dernière phase = le chrono, donc l'intervalle [premier ; dernier t_game] ne peut pas la contenir) ; sinon non évaluable.

## 5. Tests
- Tests unitaires (pipeline/tests/) : bouton prêt/en recharge sur images synthétiques, fusion des doublons à moins de 0,5 s, calcul de t_run.
- Non-régression v2.1 sur a-923ClD9Rc : aucun `sjw_ultimate` entre t_game 13 et 16 ; aucun couple de `tag` à moins de 4 s ; aucun événement après t_game 19.558 sauf le premier qui l'atteint.
- Test de bout en bout sur wJ9CwjKwyco, puis a-923ClD9Rc et Lt84IhMjBvM : fichiers produits, critères du §4 vérifiés dans le rapport.

## 7. Mesures sur wJ9CwjKwyco (v1.3, 17/11 soir)
- Calibration faite (PC, 720p, touches affichées) : F = skill_1, C = skill_2, LEFT SHIFT = ultimate, Q = sjw_skill_1, E = sjw_skill_2, Z = sjw_ultimate (60 s), T = portrait ; R, souris, jauge de noyau, QTE non calibrés. Assignation confirmée par les chiffres de recharge lus sur la planche.
- La luminance ne sépare pas « prêt » et « recharge » (effets du jeu derrière les hexagones : 91 événements pour ~15 réels). Détection v1.3 : chiffre de recharge lu par l'OCR (pixels blancs du centre, 1080p, 1 lecture / 0,5 s), lancement = 1re lecture après « prêt », cooldown_read = médiane des 3 premières lectures ; même chiffre > 3 lectures de suite = icône, ignoré ; chiffres manqués puis compteur plus bas = suite de la recharge ; recharge déjà en cours à la 1re image = aucun événement.
- HUD affiché ou non : corrélation du bouton d'esquive (zone `ancre`, icône fixe) à sa vignette médiane ≥ 0,4. Les images sans HUD (écran noir, cinématique d'ultime : wJ9 16,5-23 s) sont ignorées.
- **Le chrono de jeu s'arrête pendant les cinématiques** : wJ9 = 37,0 s de vidéo pour 19,926 s de chrono (les chiffres de recharge reprennent à 24 s là où ils s'étaient arrêtés à 16,5 s). Le contrôle « durée = chrono ± 0,5 s » est donc faux pour une run avec cinématique : remplacé par durée − temps sans HUD = chrono ± 0,5 s (codé 17/11 : `rotation.temps_sans_hud`, champ `sans_hud_s` du run, images sans HUD de l'ancre à 0,5 s ; l'ancien contrôle reste seulement si le HUD est inconnu). [À CONFIRMER] sur le relevé réel.

## 6. Limites connues
- Attaques de base non relevées ; distinction QTE / soutien incertaine.
- Chasseurs inconnu tant que les cartes de référence (discussion 9) manquent.
- Recharges réduites par des effets (ex. Phantom Slash d'Il-Hwan, −1 à −1,7 s par attaque de base ou de noyau) : un écart avec la base ne veut pas dire erreur de lecture ; a_verifier dans ce cas.
