# SUIVI — 8 Code — 2026-11-13
## Fait
- `pipeline/hotm_ecran.py` : lit la porte (제 N관문 / 第N関門 + points) et le titre du mode (플레이어 모드 = avec SJW, ハンターモード = sans SJW) dans le texte OCR. Renvoie `gate` {number, points} et `hunter_mode` (bool), `None` si illisible, plus des alertes pour `notes` (run en `a_verifier`).
- `pipeline/analyse_porte_mode.py` : tableau porte × mode sur `data/runs/*/hotm.json`, pour trancher l'hypothèse.
- Tests : `python3 pipeline/tests/test_hotm_ecran.py` (OK).
## En cours
- Le pipeline (recherche, tris 1-4) n'existe pas encore : `hotm_ecran` n'est branché nulle part. À appeler dans le tri 3/4 HOTM avec le recadrage « titre » (haut) et « porte » (bas gauche) de l'image de composition.
## À faire
- Recadrages OCR (coordonnées) à fixer sur de vraies images.
- Variantes anglaise/autres langues des titres : hypothèses non vérifiées (seuls ko et ja vus).
## Besoin d'Alexis
- Captures HOTM d'autres langues pour confirmer les libellés.
## Demandes de modif du skill
- Format « Run » : ajouter, HOTM seulement, `"gate": {"number": 1, "points": 94600}` et `"hunter_mode": false` (true = sans SJW).
