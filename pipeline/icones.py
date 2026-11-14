"""Banque d'icônes et reconnaissance par comparaison d'images (SPEC_ETAPE2 §0, §2.1).
Gratuit : Pillow + numpy (pas d'OpenCV). La comparaison est une corrélation normalisée en niveaux de gris sur les pixels
opaques de l'icône de référence (`data/icons/<categorie>/<id>.png`, 128×128, fond transparent).
Rien n'est deviné : sous le seuil ou sans écart suffisant avec le 2e candidat, l'icône est `ok: False` (-> `unmatched`)."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CATEGORIES = ("hunters", "weapons", "artifact_pieces", "cores", "shadows", "sjw_skills", "blessings", "successors",
              "subjugation_support")


def _gris(img, taille):
    """(niveaux de gris 0-1, masque opaque) d'une image PIL redimensionnée à taille × taille."""
    import numpy as np
    rgba = img.convert("RGBA").resize((taille, taille))
    a = np.asarray(rgba, dtype=float) / 255.0
    gris = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    return gris, a[..., 3] > 0.5


class Banque:
    """Icônes de référence d'une catégorie, chargées à la demande."""

    def __init__(self, racine=RACINE, taille=32):
        self.dossier = Path(racine) / "data" / "icons"
        self.taille = taille
        self._cache = {}

    def categorie(self, nom):
        if nom not in self._cache:
            from PIL import Image
            ref = {}
            d = self.dossier / nom
            for f in sorted(d.glob("*.png")) if d.exists() else []:
                try:
                    with Image.open(f) as im:
                        ref[f.stem] = _gris(im, self.taille)
                except OSError:
                    continue
            self._cache[nom] = ref
        return self._cache[nom]

    def ajouter(self, nom, identifiant, image):
        """Pour les tests : ajoute une référence en mémoire."""
        self.categorie(nom)[identifiant] = _gris(image, self.taille)


def _ncc(a, b, masque):
    import numpy as np
    x, y = a[masque], b[masque]
    if x.size < 16:
        return 0.0
    x, y = x - x.mean(), y - y.mean()
    d = float(np.sqrt((x * x).sum() * (y * y).sum()))
    return float((x * y).sum() / d) if d > 1e-9 else 0.0


def reconnaitre(image, categorie, banque, seuil=0.80, ecart=0.05, restreint=None):
    """Compare `image` (PIL) aux icônes de `categorie`. Retourne
    {"id", "score", "second", "ok", "best_id"} : `id` = candidat retenu seulement si score ≥ seuil et écart ≥ `ecart`
    avec le 2e candidat ; sinon `id` None et `best_id` garde le meilleur (pour `unmatched`). `restreint` = ids permis."""
    ref = banque.categorie(categorie)
    if restreint is not None:
        ref = {k: v for k, v in ref.items() if k in restreint}
    if not ref:
        return {"id": None, "score": 0.0, "second": 0.0, "ok": False, "best_id": None, "absente": True}
    gris, _ = _gris(image, banque.taille)
    notes = sorted(((_ncc(gris, g, m), k) for k, (g, m) in ref.items()), reverse=True)
    meilleur, ident = notes[0]
    second = notes[1][0] if len(notes) > 1 else 0.0
    ok = meilleur >= seuil and (meilleur - second) >= ecart
    return {"id": ident if ok else None, "score": round(meilleur, 3), "second": round(second, 3), "ok": ok, "best_id": ident}


def recadrer(image, zone):
    """`zone` = [x0, y0, x1, y1] en fractions de l'image."""
    w, h = image.size
    x0, y0, x1, y1 = zone
    return image.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
