"""Libellés inconnus (SPEC_ETAPE1 v24 §4.5) : quand l'OCR d'une vidéo (coréen, japonais, autre langue sans libellés connus) trouve
un écran qui RESSEMBLE à un écran de score sans qu'aucun libellé soit reconnu, le texte brut et l'image sont gardés dans
`docs/essais/ocr/libelles_inconnus/<video_id>_<t>.{txt,jpg}` (3 images au plus par vidéo, espacées d'au moins `ECART_S` secondes).
La discussion 1 en tire les libellés et les ajoute à `config.*.libelles.<langue>`. Poussés avec le passage PC (`pc.Git.pousser`)."""
import re
from pathlib import Path

DOSSIER = ("docs", "essais", "ocr", "libelles_inconnus")
MAX_PAR_VIDEO = 3
ECART_S = 3
_GRAND_NOMBRE = re.compile(r"\d{1,3}(?:[,.\s]\d{3}){2,}|\d{7,}")      # au moins 7 chiffres (millions et plus), séparateurs tolérés
_CHRONO = re.compile(r"\b\d{1,2}:\d{2}[.,]\d{3}\b")


def ressemble_score(texte):
    """≥ 3 lignes portant chacune un grand nombre (≥ 7 chiffres), ou un chrono `mm:ss.mmm`."""
    if not texte:
        return False
    import ocr_ecrans
    if ocr_ecrans.ecran_exclu(texte):         # v29 : écrans exclus (composition, fiche de chasseur…) jamais collectés
        return False
    if _CHRONO.search(texte):
        return True
    return sum(1 for ligne in texte.splitlines() if _GRAND_NOMBRE.search(ligne)) >= 3


def a_garder(texte, type_ecran, deja):
    """`deja` = liste des `t` déjà gardés pour cette vidéo. Écran de score sans libellé reconnu, quota et espacement respectés."""
    return len(deja) < MAX_PAR_VIDEO and not type_ecran and ressemble_score(texte)


def espace(t, deja):
    return all(abs(t - x) >= ECART_S for x in deja)


def garder(racine, vid, t, texte, png):
    """Écrit `<vid>_<t>.txt` et `.jpg` (image réduite à 1600 px de large). Retourne le dossier. Jamais bloquant pour l'image."""
    d = Path(racine).joinpath(*DOSSIER)
    d.mkdir(parents=True, exist_ok=True)
    base = d / f"{vid}_{int(t)}"
    base.with_suffix(".txt").write_text(texte, encoding="utf-8")
    try:
        from PIL import Image
        with Image.open(png) as im:
            im = im.convert("RGB")
            im.thumbnail((1600, 900))
            im.save(base.with_suffix(".jpg"), quality=80)
    except Exception:
        pass
    return d
