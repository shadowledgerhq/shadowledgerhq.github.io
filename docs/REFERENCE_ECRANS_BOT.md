# Écran de composition du BOT — lecture (client japonais)

Source : 5 captures fournies par Alexis le 12/11/2026 (même run, record 00:19.558). Les captures ne sont pas copiées dans le dépôt (images de tiers).
Seul ce qui est visible est noté ; rien n'est supposé.

## Zones communes à tous les onglets
- Haut : puissance du groupe (ex. 11 975 951).
- Bas gauche : boss (niveau 150), traits du boss (5 icônes), attributs recommandés (feu, ténèbres).
- Bas centre : puissance recommandée (50 000) et **record = chrono du run** (format mm:ss.mmm).
- Droite : **3 ombres** (01 à 03, colonne « 影の権能 ») et **successeur** (« 残影の力 », niv. 50, puissance 1 000 000).
- Gauche : SJW, puis 3 chasseurs (colonnes). Les onglets de la barre verticale gauche changent l'affichage.

## Onglets (barre verticale gauche, de haut en bas)
| Onglet | Ce qu'on y lit |
| --- | --- |
| 1. Équipe | Niveau, rareté (SSR), puissance et étoiles de chaque chasseur ; armes de chaque chasseur ; 2 armes de SJW (niv. 170, puissance SJW 9 226 468). |
| 2. Artefacts | 8 pièces par personnage (niv. 120, +20) ; pastilles de bonus de set (SJW : 2 et 2 ; chasseurs : 1 et 1). |
| 3. Compétences | Icônes de compétences par chasseur (sans niveau ni nom : reconnaissance par icône). |
| 4. Compétences SJW | 8 compétences de SJW (+5 chacune). |
| 5. Noyaux | 3 noyaux par personnage, niv. 25 / MAX, pourcentage de progression ; certains emplacements vides. |

## Conséquences pour la base de données
- Le client est **japonais** : ajouter `ja` (facultatif) dans `name`, utile pour relier les icônes aux ids.
- Les noms n'apparaissent pas sur la plupart des écrans : la reconnaissance se fait par **icônes** (banque d'icônes indispensable : artefacts, noyaux, compétences, armes, ombres, successeur).
- Les 3 ombres et le successeur sont présents au BOT : à confirmer comme « autorisés » (une capture n'est pas une règle).
- Les stats principales des persos ne sont pas visibles ici : onglet à fournir.
