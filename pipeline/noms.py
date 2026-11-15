"""Reconnaissance par le nom écrit (SPEC_ETAPE2 v3 §2.1) : un nom lu par OCR est comparé aux noms de la base
(`name.ja`, `name.ko`, `name.en`, `name.fr`). Aucune traduction, aucun nom inventé."""
import unicodedata
from difflib import SequenceMatcher

LANGUES = ("ja", "ko", "en", "fr")
SEUIL_NOM = 0.90          # [À CONFIRMER] config.seuil_nom


def normaliser(texte):
    """NFKC, sans espaces, sans `・` ni `·`, casse ignorée."""
    t = unicodedata.normalize("NFKC", str(texte or ""))
    for c in ("・", "·", "･", "·"):
        t = t.replace(c, "")
    return "".join(t.split()).casefold()


def noms_objet(obj):
    return [v for v in ((obj.get("name") or {}).get(l) for l in LANGUES) if isinstance(v, str) and v.strip()]


def apparier(lu, objets, seuil=SEUIL_NOM):
    """`objets` : {id: objet de la base}. Retourne {"id", "methode": "exact" | "approche" | None, "score", "candidats"}.
    Égalité exacte (après normalisation) sur un seul id -> exact ; sinon un seul candidat ≥ seuil -> approché ;
    plusieurs ex æquo ou aucun -> id None (le texte lu reste `unmatched`)."""
    n = normaliser(lu)
    if not n:
        return {"id": None, "methode": None, "score": 0.0, "candidats": []}
    exacts, notes = set(), {}
    for ident, o in objets.items():
        for nom in noms_objet(o):
            m = normaliser(nom)
            if not m:
                continue
            if m == n:
                exacts.add(ident)
            notes[ident] = max(notes.get(ident, 0.0), SequenceMatcher(None, n, m).ratio())
    if len(exacts) == 1:
        return {"id": next(iter(exacts)), "methode": "exact", "score": 1.0, "candidats": sorted(exacts)}
    if len(exacts) > 1:
        return {"id": None, "methode": None, "score": 1.0, "candidats": sorted(exacts)}
    bons = sorted((i for i, s in notes.items() if s >= seuil), key=lambda i: -notes[i])
    if len(bons) == 1:
        return {"id": bons[0], "methode": "approche", "score": round(notes[bons[0]], 3), "candidats": bons}
    return {"id": None, "methode": None, "score": round(max(notes.values(), default=0.0), 3), "candidats": bons}


def croiser(id_nom, id_icone):
    """Le nom prime sur l'icône ; s'ils diffèrent -> (id du nom, True = désaccord, build `a_verifier`, note `nom/icône en désaccord`)."""
    if id_nom is None:
        return id_icone, False
    return id_nom, bool(id_icone and id_icone != id_nom)
