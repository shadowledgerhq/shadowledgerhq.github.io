# SUIVI — 8 Code — 2026-11-13
## Fait
- `pipeline/sjw.py` : 6 emplacements de compétences SJW (skill_1, skill_2, ultimate, qte_1-3), `level` null accepté, complétude = 6 emplacements + 8 bénédictions, grille 3+3 du PowerPoint. Test : `python3 pipeline/tests/test_sjw.py`.
- `docs/REFERENCE_ECRANS_HOTM.md` : section Compétences corrigée (6 emplacements).
- `pipeline/hotm_ecran.py` : lit la porte (제 N관문 / 第N関門 + points) et le titre du mode (플레이어 모드 = avec SJW, ハンターモード = sans SJW) dans le texte OCR. Renvoie `gate` {number, points} et `hunter_mode` (bool), `None` si illisible, plus des alertes pour `notes` (run en `a_verifier`).
- `pipeline/analyse_porte_mode.py` : tableau porte × mode sur `data/runs/*/hotm.json`, pour trancher l'hypothèse.
- Tests : `python3 pipeline/tests/test_hotm_ecran.py` (OK).
## En cours
- Le pipeline (recherche, tris 1-4) n'existe pas encore : `hotm_ecran` n'est branché nulle part. À appeler dans le tri 3/4 HOTM avec le recadrage « titre » (haut) et « porte » (bas gauche) de l'image de composition.
## À faire
- Slide PowerPoint « Compétences SJW / SJW Skills » (grille 3+3) : à coder avec l'export PowerPoint (pas encore écrit).
- Recadrages OCR (coordonnées) à fixer sur de vraies images.
- Variantes anglaise/autres langues des titres : hypothèses non vérifiées (seuls ko et ja vus).
## Besoin d'Alexis
- Captures HOTM d'autres langues pour confirmer les libellés.
## Demandes de modif du skill
- Format « Build » : `sjw.skills` = liste de 6 objets {slot, id, level|null} (slots skill_1, skill_2, ultimate, qte_1, qte_2, qte_3).
- Format « Run » : ajouter, HOTM seulement, `"gate": {"number": 1, "points": 94600}` et `"hunter_mode": false` (true = sans SJW).
