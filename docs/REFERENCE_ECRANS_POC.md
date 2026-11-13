# Écran de composition du POC — lecture (client coréen)

Source : 5 captures fournies par Alexis le 13/11/2026 (une seule run). Les captures ne sont pas copiées dans le dépôt. Seul ce qui est visible est noté.

## Zones communes
- Titre : « 플레이어 팀파이트 모드 » ; puissance de l'équipe 13 879 026.
- Flèches gauche/droite autour des 3 chasseurs : plusieurs équipes (POC = 2 runs). Bas : « 1팀 » suivi de `132 727 081 163 343 P` (probablement le score de l'équipe 1 : **à confirmer**).
- Bas gauche : boss (niv. 100), traits du boss, attributs recommandés (feu, eau) ; puissance recommandée 1 761 750.
- Boutons : 추천 편성 (équipe recommandée), 자동 편성 (équipe auto), 입장하기 (entrer), 토벌 정비 (haut droite, ouvre le soutien de subjugation).
- Droite : 3 ombres (« 그림자의 권능 », 01 à 03) et successeur (« 계승자 », niv. 170, puissance 2 260 588).
- Gauche : un personnage (cheveux gris, lunettes de soleil), très probablement SJW en costume (voir plus bas), puis 3 chasseurs.

## Onglet Équipe (capture complémentaire du 13/11/2026)
- Chaque chasseur : niv. 170, SSR, 5 étoiles, puissance 2 523 439 / 2 511 828 (lecture à confirmer) / 2 554 486, arme SSR avec « +100 ».
- Bandeau « 편성 고정 » (composition fixée) sur les 3 chasseurs et sur les 2 armes du personnage de gauche (« +200 ») : **en POC cette semaine, chasseurs et armes sont imposés**, non choisis par le joueur.
- Personnage de gauche : niv. 170, puissance **3 405 259**, identique à la puissance de combat de 성진우 sur l'écran de stats fourni le 12/11. Il s'agit donc très probablement de Sung Jin Woo avec un costume (à confirmer par Alexis).

## Onglets (barre verticale gauche) — mêmes que le BOT
Équipe/armes · Artefacts (8 pièces niv. 120 +20 ; pastilles de set : 2·2 / 1·1 / 1·1 / 2·2) · Compétences · Compétences du personnage de gauche (+5) · Noyaux (3 par personnage, niv. 25 MAX).

## Fenêtre « 토벌 지원 » (soutien de subjugation) — nouvelle catégorie
3 colonnes, 1 choix par colonne (compteur 1/1 ×3), pouce = recommandé, onglet « 토벌 숙련도 » (maîtrise) :
- Colonne 1 (bleue) : ATQ/DEF/PV +20 % · dégâts sur [과부하] +10 % · dégâts critiques +20 %.
- Colonne 2 (violette) : si Stacker/Supporter/Buster dans l'équipe, bonus pour [성진우, <rôle>] : effet d'infusion d'attribut +200 % / dégâts d'attribut +100 % / dégâts [과부하] +100 %.
- Colonne 3 (or) : successeur ATQ/DEF/PV max +200 % et dégâts +200 % · compétences avec infusion d'attribut de 성진우 +500 % · attaque normale/noyau/compétence d'arme de 성진우 +500 %.
Cette fenêtre cite Sung Jin Woo (성진우), cohérent avec le personnage de gauche (voir ci-dessus).
Rôles lus : 스태커 (Stacker), 서포터 (Supporter), 버스터 (Buster).

## Conséquences pour la base
- Nouvelle catégorie proposée : `subjugation_support.json` (colonne, effet structuré, condition de rôle) ; ajoutée au schéma.
- Ajouter le champ `role` (stacker/supporter/buster) aux chasseurs.
- Règles POC : ajouter à `data/rules/<semaine>.json` un champ `fixed_team` (composition imposée) pour le POC ; à remplir quand Alexis aura confirmé.
