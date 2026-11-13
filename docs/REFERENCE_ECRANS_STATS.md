# Écran de stats d'un personnage — lecture

Source : 1 capture fournie par Alexis le 12/11/2026 (client coréen, SJW niv. 170). Alexis indique que cet écran est identique dans tous les modes.

- Onglets : « 전체 » (tout), « 무기 » (arme), « 아티팩트 » (artefacts).
- Format d'une ligne : `pourcentage (valeur brute)`, ex. `50% (19191)`. Certaines lignes sont brutes (PV, attaque).
- Liste complète à conserver (confirmé par Alexis) : les 10 lignes du tableau ci-dessous. La dernière ligne est coupée par le bas de l'écran.

| Nom coréen | Sens probable | Valeur lue |
| --- | --- | --- |
| 체력 | PV | 98592 |
| 마력 | Mana | 4928 |
| 공격력 | Attaque | 195607 |
| 정밀도 | Précision | 82.94% (23413) |
| 방어력 | Défense | 73.42% (69055) |
| 치명타 확률 | Taux de critique | 50% (19191) |
| 치명타 피해 | Dégâts critiques | 220.16% (28517) |
| 재사용 대기시간 감소 | Réduction de recharge | 12.35% (5869) |
| 방어력 관통 | Pénétration de défense | 39.45% (32579) |
| 피해량 증가 | Augmentation des dégâts | 21.42% (13627) |

Les noms FR/EN ci-dessus sont des traductions probables, **à vérifier** sur la source avant d'alimenter `stats.json`.

Zone gauche de l'écran (attributs de base, lecture probable) : force 697, 10, 10, intelligence 650, sens 17 ; zone droite : puissance de combat 3 405 259 avec PV, attaque et défense en résumé. Non retenues dans `stats.json` tant qu'Alexis ne les demande pas.
