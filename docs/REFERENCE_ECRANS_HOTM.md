# Écran de composition et de résultat du HOTM — lecture (client coréen)

Source : 5 captures fournies par Alexis le 13/11/2026 (une seule run). Les captures ne sont pas copiées dans le dépôt. Seul ce qui est visible est noté.

## Écran de composition
- Titre : « 플레이어 모드 » ; puissance de l'équipe 14 133 873.
- Haut droite : bouton **« 증명 설정 »** avec le niveau 931 (voir ci-dessous).
- SJW niv. 170, puissance 3 796 650, 2 armes SSR. 3 chasseurs niv. 170 SSR (puissances 2 486 153 / 2 485 491 / 2 447 784, lecture à confirmer). 3 ombres + successeur niv. 170 (2 242 640).
- Bas : boss niv. 150, 6 traits du boss, attribut recommandé (feu), puissance recommandée 12 530 000, « 제 1관문 » (porte 1) **94 600pt**.
- Mêmes onglets que BOT et POC (équipe/armes, artefacts, compétences, bénédictions de SJW, noyaux).

## Onglets complémentaires (4 captures du 13/11/2026, même run)
Structure identique au BOT et au POC ; rien de nouveau dans la mise en page.
- **Noyaux** : 3 par personnage, tous niv. 25 MAX, cadenas ; une pastille d'élément colorée (vert, bleu, violet, rouge) en haut à gauche de chaque noyau. Les noyaux d'un même emplacement ne sont pas les mêmes d'un personnage à l'autre.
- **Bénédictions de SJW** : 8, toutes « +5 » (correction d'Alexis : ce ne sont pas des compétences).
- **Compétences** : SJW affiche 4 grandes icônes (trois « +5 », une « +2 », une icône orange sans niveau ; le « +2 » appartient aux compétences, confirmé par Alexis) ; chaque chasseur affiche 8 icônes hexagonales (première = « i », informations) avec une petite pastille d'élément/type.
- **Artefacts** : 8 pièces par personnage, niv. 120 +20 ; pastilles en haut de chaque colonne : SJW 1·1, chasseur 1 : 2·2, chasseur 2 : 1·1, chasseur 3 : 2·2 (rouge pour « 2 », bleu pour « 1 ») : **sens non interprété**.
- Aucun nom d'objet visible : la reconnaissance se fait par icône, d'où la priorité de la banque d'icônes (artefacts, noyaux, compétences, armes).

## Mode sans Sung Jin Woo (« ハンターモード », 3 captures du 13/11/2026, client japonais)
Confirmé par Alexis : il existe un mode HOTM **sans SJW**. Autre run, autre boss.
- Titre : « ハンターモード » ; puissance de l'équipe 12 842 243 ; bouton « 証明設定 » niveau **935**.
- Pas de personnage à gauche : 3 chasseurs SSR niv. 170 (puissances 2 503 984 / 2 507 438 / 2 489 276), 3 ombres, successeur niv. 170 (2 193 023, autre successeur que dans le mode avec SJW).
- Seulement **4 onglets** : équipe/armes, artefacts, compétences, noyaux. Pas d'onglet bénédictions (propre à SJW).
- Bas : boss niv. 150, 5 traits, attribut recommandé (eau), puissance recommandée 12 550 000, « 第2関門 » (porte 2) **95 000pt**. Le mode avec SJW affichait « 第1関門 » 94 600pt : le lien porte/mode est une hypothèse, **à confirmer**.
- Artefacts : pastilles 1·1 / 2·2 / 2·2 ; noyaux : 3 par chasseur, niv. 25 MAX.
- Les règles HOTM sont donc **par sous-mode** (avec / sans SJW) : voir `data/rules/`.

## Fenêtre « 단련의 증명 » (preuve d'entraînement) — nouvelle catégorie
Le joueur choisit lui-même des handicaps qui rapportent des points. En-tête : niveau de preuve **931**, points acquis `94 600pt (+93 100pt)`, puissance prévue 12 530 000.
Chaque ligne : effet, niveau choisi / maximum (ex. 5/5, 40/40), coût en niveau de preuve.

| Effet (coréen, lecture) | Choisi | Coût |
| --- | --- | --- |
| Début de combat : PV −70 % et soins alliés réduits | 1/1 | 100 |
| Consommation périodique de la jauge de noyau | 1/1 | 100 |
| Dégâts de toutes les attaques sauf compétences d'arme réduits | 1/1 | 100 |
| Le boss obtient périodiquement « furie » (arrêtable par compétence QTE) | 1/1 | 100 |
| Si moins de 3 chasseurs [attribut lent] : dégâts infligés réduits, subis augmentés | 1/1 | 100 |
| Après usage de [ruée], dégâts réduits un temps (sauf [esquive extrême]) | 1/1 | 100 |
| Effet lié au boss 다보르카 (œil / orbes, gain d'empilement) | 1/1 | 50 |
| Effet lié au boss 다보르카 (poignards : dégâts et réduction de soin renforcés) | 1/1 | 50 |
| Attaque ennemie augmentée | 40/40 | 80 |
| PV ennemis augmentés | 3/40 | 6 |
| Précision alliée réduite | 5/5 | 25 |
| Taux et dégâts critiques ennemis augmentés | 5/5 | 25 |
| Effet [soin PV] allié réduit | 5/5 | 25 |
| Effet [soin mana] allié réduit | 5/5 | 25 |
| Effet [bouclier] allié réduit | 5/5 | 25 |
| Dégâts inévitables après 300 s | 1/1 | 10 |
| Comportement du boss plus imprévisible | 1/1 | 10 |

Les libellés sont une lecture approximative des captures, pas une traduction officielle.
**Vérification arithmétique** : la somme des coûts du tableau = 931 = niveau de preuve affiché.

## Écran de résultat (« RESULT — 기만자의 무대 »)
- Durée 04:34. Détail « 전투 결과 » : 클리어 (clear) 1 500 · 증명 보너스 (bonus de preuve) 93 100 · 합산 결과 (total) **94 600**.
- 기존 기록 (record précédent) 94 000 ; 이번 기록 (cette run) **94 600** (+600 en vert).
- Vérifications : 1 500 + 93 100 = 94 600 ; bonus de preuve = niveau de preuve × 100 (931 × 100 = 93 100). Observé sur une seule run : à confirmer sur d'autres.
- Même piège que le POC : deux scores affichés ; 이번 기록 est la run filmée (structure identique au POC, confirmation d'Alexis donnée pour le POC seulement).
- Le score HOTM dépend du réglage de difficulté choisi par le joueur : deux runs identiques en équipe peuvent avoir des scores très différents.

## Conséquences pour la base
- Nouvelle catégorie proposée : `proof_modifiers.json` (effet structuré, niveau max, coût par niveau, boss concerné éventuel). Ajoutée au schéma, saisie en dernier.
- Ombres et successeur présents ; SJW présent. Règles HOTM de la semaine : à confirmer par Alexis avant `data/rules/`.
