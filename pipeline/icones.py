"""Banque d'icônes et reconnaissance par recherche de gabarit (SPEC_ETAPE2 §0, §2.1). Gratuit : OpenCV
(`py -3 -m pip install opencv-python-headless`) + numpy + Pillow.

Chaque icône de référence (`data/icons/<categorie>/<id>.png`, 128×128, fond transparent) est rognée à son contenu, mise à
plusieurs échelles (fractions de la zone, donc indépendantes de la résolution) et cherchée dans la zone recadrée de l'image
(`cv2.matchTemplate`, `TM_CCOEFF_NORMED`, masque = transparence de l'icône). Le meilleur score par icône sert au classement.
Rien n'est deviné : sous le seuil ou sans écart suffisant avec le 2e candidat, `id` vaut None (-> `unmatched`).
Réglage sur une capture BOT japonaise (14/11/2026) : vrais noyaux 0,60-0,66 contre 0,39-0,57 pour le 2e ; emplacements vides
0,37-0,43. Seuils [À CONFIRMER] dans `pipeline/config/etape2.json`."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CATEGORIES = ("hunters", "weapons", "artifact_pieces", "cores", "shadows", "sjw_skills", "blessings", "successors",
              "subjugation_support")
ECHELLES = (0.5, 0.6, 0.7, 0.8)


def _cv():
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise SystemExit("OpenCV absent : py -3 -m pip install opencv-python-headless")
    return cv2, np


def _bgra(img):
    """PIL -> tableau BGRA rogné à la zone opaque (seuil alpha 40)."""
    cv2, np = _cv()
    a = np.asarray(img.convert("RGBA"))
    bgra = np.dstack([a[..., 2], a[..., 1], a[..., 0], a[..., 3]])
    ys, xs = np.where(bgra[..., 3] > 40)
    if len(ys) == 0:
        return None
    return np.ascontiguousarray(bgra[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def _bgr(img):
    cv2, np = _cv()
    a = np.asarray(img.convert("RGB"))
    return np.ascontiguousarray(a[..., ::-1])


class Banque:
    """Icônes de référence d'une catégorie, chargées à la demande."""

    def __init__(self, racine=RACINE, taille=None):
        self.dossier = Path(racine) / "data" / "icons"
        self._cache = {}

    def categorie(self, nom):
        if nom not in self._cache:
            from PIL import Image
            ref = {}
            d = self.dossier / nom
            for f in sorted(d.glob("*.png")) if d.exists() else []:
                try:
                    with Image.open(f) as im:
                        b = _bgra(im)
                except OSError:
                    continue
                if b is not None:
                    ref[f.stem] = b
            self._cache[nom] = ref
        return self._cache[nom]

    def ajouter(self, nom, identifiant, image):
        """Pour les tests : ajoute une référence en mémoire."""
        self.categorie(nom)[identifiant] = _bgra(image)


def _score(zone, ref, echelles):
    cv2, np = _cv()
    cote = min(zone.shape[:2])
    h, w = ref.shape[:2]
    meilleur = -1.0
    for e in echelles:
        s = e * cote / max(h, w)
        r = cv2.resize(ref, (max(8, round(w * s)), max(8, round(h * s))), interpolation=cv2.INTER_AREA)
        if r.shape[0] > zone.shape[0] or r.shape[1] > zone.shape[1]:
            continue
        masque = (r[..., 3] > 128).astype(np.uint8) * 255
        if masque.sum() == 0:
            continue
        out = np.nan_to_num(cv2.matchTemplate(zone, np.ascontiguousarray(r[..., :3]), cv2.TM_CCOEFF_NORMED, mask=masque),
                            nan=-1.0, posinf=-1.0, neginf=-1.0)
        meilleur = max(meilleur, float(out.max()))
    return meilleur


def reconnaitre(image, categorie, banque, seuil=0.55, ecart=0.05, restreint=None, echelles=ECHELLES):
    """Cherche dans `image` (PIL, déjà recadrée sur la zone) l'icône de `categorie` qui lui ressemble le plus. Retourne
    {"id", "score", "second", "ok", "best_id"} : `id` = candidat retenu seulement si score ≥ seuil et écart ≥ `ecart`
    avec le 2e candidat ; sinon `id` None et `best_id` garde le meilleur (pour `unmatched`). `restreint` = ids permis."""
    ref = banque.categorie(categorie)
    if restreint is not None:
        ref = {k: v for k, v in ref.items() if k in restreint}
    if not ref:
        return {"id": None, "score": 0.0, "second": 0.0, "ok": False, "best_id": None, "absente": True}
    zone = _bgr(image)
    notes = sorted(((_score(zone, g, echelles), k) for k, g in ref.items()), reverse=True)
    meilleur, ident = notes[0]
    second = notes[1][0] if len(notes) > 1 else 0.0
    ok = meilleur >= seuil and (meilleur - second) >= ecart
    return {"id": ident if ok else None, "score": round(meilleur, 3), "second": round(second, 3), "ok": ok, "best_id": ident}


def recadrer(image, zone):
    """`zone` = [x0, y0, x1, y1] en fractions de l'image."""
    w, h = image.size
    x0, y0, x1, y1 = zone
    return image.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
