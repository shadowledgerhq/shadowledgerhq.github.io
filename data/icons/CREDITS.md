# Icônes

- **Source** : slagate.com (Sohoven), images référencées par `GET api.slagate.com/api/references`, récupérées le 13/11/2026 avec l'accord d'Alexis (routes GET publiques, icônes comprises).
- **Droits** : les illustrations d'origine appartiennent à Netmarble / Solo Leveling: ARISE ; la mise en forme des images appartient à Slagate. Toute publication doit créditer Slagate.com (Sohoven). `robots.txt` de slagate.com indique `ai-train=no` : ne pas utiliser ces images pour entraîner une IA.
- **Format** : PNG 128×128, fond transparent, proportions conservées (outil : `tools/fetch_icons.py`).
- **Organisation** : `data/icons/<categorie>/<id>.png` ; pièces d'artefacts : `artifact_pieces/<id-du-set>--<emplacement>.png`.
- **Armes de Sung Jin-Woo sans icône Slagate (26)** : `data/icons/weapons/<id>.png`, fichiers « <nom> Icon.png » du wiki Fandom Solo Leveling: ARISE (texte du wiki CC BY-SA ; illustrations © Netmarble), récupérés le 17/11/2026, redimensionnés en 128×128 comme les autres ; source dans le champ `icon_source` de chaque entrée de `weapons.json`.
- **Cartes de référence** : `data/icons/hunters_cartes/esil-radiru.png` (recadrage de la capture POC `docs/essais/composition/poc_personnages_ja.png`, 17/11/2026) ; `data/icons/shadows_cartes/{beste,greed}.png` (mêmes captures, zones `shadows` de `etape2.json`). Pas de contrainte de droits au-delà de celle du jeu.
