"""Lie un écran de stats de chasseur à sa carte de la composition (v18, essai POC v0tuXJNxudk du 15/11/2026).

Les icônes de `data/icons/hunters/` sont d'autres illustrations que les cartes du jeu : la reconnaissance par modèle échoue.
Mais l'écran de stats (`ハンター`) montre la MÊME illustration en grand que la carte de la composition : on compare par
points d'intérêt (SIFT + homographie RANSAC) le portrait de l'écran de stats aux cartes de l'onglet personnages. Le nom lu
par l'OCR sur l'écran de stats donne l'identité, le portrait donne la position (1 à 3). Gratuit : OpenCV + Pillow.
Mesuré : bonne carte 84 correspondances sûres, les deux autres 19 et 4 (seuils `portraits` dans `etape2.json`)."""

from pathlib import Path

LARGEUR = 640


def _cv():
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise SystemExit("OpenCV absent : py -3 -m pip install opencv-python-headless")
    return cv2, np


def _points(image, cv2, np):
    a = np.asarray(image.convert("L"))
    h, w = a.shape
    if w > LARGEUR:
        a = cv2.resize(a, (LARGEUR, max(1, round(h * LARGEUR / w))), interpolation=cv2.INTER_AREA)
    a = cv2.createCLAHE(2.0, (4, 4)).apply(a)
    return cv2.SIFT_create().detectAndCompute(a, None)


def correspondances(carte, portrait):
    """Nombre de correspondances cohérentes (RANSAC) entre deux images PIL ; 0 si trop peu de points."""
    cv2, np = _cv()
    k1, d1 = _points(carte, cv2, np)
    k2, d2 = _points(portrait, cv2, np)
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return 0
    paires = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    bonnes = [p[0] for p in paires if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(bonnes) < 4:
        return 0
    _, masque = cv2.findHomography(np.float32([k1[g.queryIdx].pt for g in bonnes]),
                                   np.float32([k2[g.trainIdx].pt for g in bonnes]), cv2.RANSAC, 5.0)
    return int(masque.sum()) if masque is not None else 0


def decouper_portrait(image, cfg):
    """Partie gauche de l'écran de stats (illustration du chasseur)."""
    x0, y0, x1, y1 = (cfg.get("portraits") or {}).get("zone_stats", [0.0, 0.05, 0.45, 0.72])
    w, h = image.size
    return image.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))


def decouper_cartes(image, zones, cfg):
    """Une image par carte de chasseur : la zone du visage élargie vers le bas (carte entière jusqu'aux armes)."""
    c = cfg.get("portraits") or {}
    haut, marge = c.get("carte_y", [0.15, 0.5]), c.get("carte_marge_x", 0.01)
    w, h = image.size
    sortie = []
    for z in zones:
        x0, _, x1, _ = z
        sortie.append(image.crop((round((x0 - marge) * w), round(haut[0] * h), round((x1 + marge) * w), round(haut[1] * h))))
    return sortie


def choisir(notes, cfg):
    """Index de la meilleure carte si ≥ `min_corr` correspondances et ≥ `rapport` × la 2e (défauts 25 et 2), sinon None."""
    c = cfg.get("portraits") or {}
    if not notes:
        return None
    ordre = sorted(range(len(notes)), key=lambda i: -notes[i])
    meilleur, second = notes[ordre[0]], (notes[ordre[1]] if len(notes) > 1 else 0)
    return ordre[0] if meilleur >= c.get("min_corr", 25) and meilleur >= c.get("rapport", 2) * max(second, 1) else None


def notes_cartes(portrait, cartes):
    return [correspondances(k, portrait) for k in cartes]


# --- bibliothèque de cartes apprises : `data/icons/hunters_cartes/<id>.png` ----------------------------------------------

DOSSIER_CARTES = ("data", "icons", "hunters_cartes")


def dossier_cartes(icones_dir):
    """`icones_dir` = dossier `data/icons` (celui de `icones.Banque`)."""
    return Path(icones_dir) / DOSSIER_CARTES[-1]


DOSSIER_OMBRES = "shadows_cartes"      # v33 : cartes d'ombres (recadrages des zones `shadows`), fournies par la base de données (discussion 9)


def identifiant(nom):
    """v7 §2.1 : `<id>.png` et `<id>--tenue<N>.png` (tenues alternatives) désignent le même chasseur : identifiant = partie avant « -- »."""
    return str(nom).split("--", 1)[0]


def _liste(v):
    return list(v) if isinstance(v, (list, tuple)) else [v]


def charger_cartes(icones_dir, sous_dossier=None):
    """Cartes de `data/icons/<sous_dossier>` (défaut : `hunters_cartes`), regroupées par identifiant : {id: [image, ...]}
    (`<id>.png`, `<id>--tenue<N>.png`)."""
    from PIL import Image
    sortie = {}
    d = Path(icones_dir) / sous_dossier if sous_dossier else dossier_cartes(icones_dir)
    for f in sorted(d.glob("*.png")) if d.exists() else []:
        try:
            with Image.open(f) as im:
                sortie.setdefault(identifiant(f.stem), []).append(im.convert("RGB").copy())
        except OSError:
            continue
    return sortie


def meilleures_correspondances(image, bibliotheque):
    """{id: meilleur nombre de correspondances parmi les cartes de l'id} ; `bibliotheque` = {id: image | [images]}."""
    return {k: max(correspondances(image, ref) for ref in _liste(refs)) for k, refs in bibliotheque.items()}


def apparier_cartes(cartes_vues, bibliotheque, cfg, cle_min="min_corr_biblio", defaut_min=40):
    """`cartes_vues` = {position: image} ; `bibliotheque` = {id: image | [images]} (plusieurs tenues par chasseur : meilleur score retenu, jamais de comparaison entre deux cartes du même chasseur). Retourne ({position: id}, matrice {position: {id: n}}).
    Un couple (position, id) est retenu si n ≥ `min_corr_biblio` (défaut 40 : le bruit atteint ~30 avec une seule carte connue)
    et n ≥ `rapport` × le meilleur des autres : autre chasseur de la bibliothèque sur cette carte, même chasseur sur une autre carte."""
    c = cfg.get("portraits") or {}
    mini, rapport = c.get(cle_min, defaut_min), c.get("rapport", 2)
    m = {p: meilleures_correspondances(im, bibliotheque) for p, im in cartes_vues.items()}
    sortie = {}
    for p, ligne in m.items():
        for k, n in ligne.items():
            autres = [v for k2, v in ligne.items() if k2 != k] + [m[p2][k] for p2 in m if p2 != p]
            if n >= mini and n >= rapport * max(autres + [1]):
                sortie[p] = k
    return sortie, m


def apprendre(icones_dir, ident, carte):
    """Enregistre la carte d'un chasseur identifié de façon sûre (nom OCR + portrait). Retourne True si nouvelle ; jamais d'écrasement."""
    d = dossier_cartes(icones_dir)
    f = d / f"{ident}.png"
    if f.exists():
        return False
    d.mkdir(parents=True, exist_ok=True)
    carte.convert("RGB").save(f)
    return True
