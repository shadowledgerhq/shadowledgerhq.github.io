# SPEC_ROTATION — relevé automatique de l'ordre des compétences — v1 (2026-11-17)

Demandeur : discussion 3 (Theorycraft). Code : discussion 8. Aucune action manuelle d'Alexis.
But : pour les meilleures runs, la liste horodatée des compétences utilisées pendant la run. Elle sert de timeline aux vidéos de l'étape 3b.

## 1. Périmètre
- BOT d'abord : top 3 de data/runs/<semaine>/bot.json (lignes provisoires acceptées). POC, GB et HOTM (top 3 par classement ou par porte) seulement une fois le BOT validé.
- Où : passage PC (pipeline/pc.py), après les tris 3-4, sur la vidéo déjà téléchargée (aucun second téléchargement). Le cloud ne peut pas télécharger YouTube (blocage anti-bot) : le PC est obligatoire.
- Une vidéo n'est traitée qu'une fois : data/processed.json, pc.rotation = fait | absent | erreur.
- Budget de départ : 3 vidéos par mode et par passage.

## 2. Méthode
1. Bornes de la run : run_start_t = première image où le HUD de combat est visible (boutons de compétences) ; run_end_t = première image de l'écran Results (détection existante, ecrans.py). Les images hors bornes sont ignorées. Vidéo à 2 runs (POC, GB) : un objet par run dans runs[], dans l'ordre de runs_detail.
2. Échantillonnage : 10 images/s entre les bornes, en 720p.
3. Calibration du HUD (format 16:9), dans pipeline/config/rotation.json : zones des boutons skill_1, skill_2, ultimate (chasseur actif), des boutons de SJW, des portraits de l'équipe et de la jauge de noyau. Établie à partir des images de wJ9CwjKwyco (client anglais), puis vérifiée sur a-923ClD9Rc (client japonais) et Lt84IhMjBvM. Format autre que 16:9 : limites ["format"] et aucun événement.
4. Détection (entre deux images successives) :
   - skill_1, skill_2, ultimate, sjw_* : le bouton passe de « prêt » à « en recharge » (assombrissement et chiffre de recharge). L'événement est daté à la première image en recharge. Le chiffre lu va dans cooldown_read.
   - core : la jauge de noyau se vide.
   - tag : le portrait du perso actif change. trigger = qte si une bannière ou un effet de QTE est reconnu, sinon inconnu (QTE et soutien ne sont pas distingués de façon sûre).
   - Les attaques de base ne sont pas relevées.
   - Deux détections du même bouton à moins de 0,5 s d'écart = un seul événement.
5. Confiance : sur si cooldown_read correspond à la recharge de la base (hunters.json, sjw_skills.json) à ±1 s près, ou si le perso est identifié et que l'ordre respecte les recharges ; sinon a_verifier.
6. Identité : hunter = id de la base si le portrait correspond (cartes de référence de la discussion 9, data/icons/hunters/), sjw pour Sung Jin Woo, sinon inconnu. Les compétences SJW (sjw.skills du build) donnent l'id de la compétence (skill_id) quand il est connu.
7. Images de tiers : aucune image complète de la vidéo n'est poussée. Seuls les recadrages des boutons et portraits (comme data/builds/.../_crops/) peuvent l'être, dans data/rotations/<semaine>/<mode>/_crops/.

## 3. Sortie : data/rotations/<semaine>/<mode>/<video_id>.json
{"spec": 1, "video_id": "wJ9CwjKwyco", "week": "2026-11-12", "mode": "bot", "gate": null, "run_id": "bot-2026-11-12-wJ9CwjKwyco",
 "runs": [{"run_index": 1, "run_start_t": 0.0, "run_end_t": 0.0, "duration_s": 0.0,
   "events": [{"t": 0.0, "t_run": 0.0, "hunter": "sjw | <id> | inconnu", "slot": "skill_1", "skill_id": null, "trigger": null, "cooldown_read": null, "source": "hud-recharge", "confidence": "a_verifier"}],
   "limites": []}]}
- slot : skill_1, skill_2, ultimate, core, tag, sjw_skill_1, sjw_skill_2, sjw_ultimate, sjw_qte.
- source : hud-recharge, portrait, jauge, ocr. confidence : sur, a_verifier.
- t = secondes dans la vidéo ; t_run = t − run_start_t. trigger seulement pour tag (qte | inconnu).
- limites : format, hud-non-trouve, bornes-incertaines, chasseurs-inconnus.
- Rapport du passage : data/rotations/<semaine>/_rapport.md (vidéos, nombre d'événements, a_verifier, limites).

## 4. Exemple réel : wJ9CwjKwyco (BOT 2026-11-12, X SLA, Baruka S20)
Déjà connu (à vérifier) :
- vidéo de 49 s (_videos.json) ; écran de composition à 38-46 s (build provisoire) ;
- chrono de la run : 19,926 s, lu sur la miniature (i.ytimg.com, 17/11/2026). bot.json indique 19,0 s (lu dans le titre). La capture Results de REFERENCE_ECRANS_BOT.md (13/11 : Baruka, phases cumulées 9,281 / 14,986 / 19,926 s) correspond probablement à cette run ;
- SJW : arme The Huntsman, QTE 1 Foulée de l'ombre (build provisoire).
Le cloud n'a pas pu télécharger la vidéo : les événements de l'exemple sont produits par le premier passage PC, puis recopiés ici en v2.
Critères d'acceptation :
- duration_s = 19,9 ± 0,5 s et run_end_t < 38 s (avant la composition) ;
- au moins un événement pour SJW et un pour chaque chasseur actif ;
- aucune compétence relancée avant la fin de sa recharge connue ;
- les phases du Results (9,281 / 14,986 s) tombent entre run_start_t et run_end_t.

## 5. Tests
- Tests unitaires (pipeline/tests/) : bouton prêt/en recharge sur images synthétiques, fusion des doublons à moins de 0,5 s, calcul de t_run.
- Test de bout en bout sur wJ9CwjKwyco, puis a-923ClD9Rc et Lt84IhMjBvM : fichiers produits, critères du §4 vérifiés dans le rapport.

## 6. Limites connues
- Attaques de base non relevées ; distinction QTE / soutien incertaine.
- Chasseurs inconnu tant que les cartes de référence (discussion 9) manquent.
- Recharges réduites par des effets (ex. Phantom Slash d'Il-Hwan, −1 à −1,7 s par attaque de base ou de noyau) : un écart avec la base ne veut pas dire erreur de lecture ; a_verifier dans ce cas.
