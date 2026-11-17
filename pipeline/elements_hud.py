"""SPEC v31 §3.1 : élément de chaque chasseur du panneau d'équipe du HUD de combat GB, lu sur la COULEUR du losange d'élément (haut
gauche de chaque portrait, colonne de droite). Sans identité du chasseur : alimente l'élément de la run (`elements.annoter`, priorité
`hunter_ids` > `elements_hud` > titre). Fonctions pures sur une image Pillow ou un chemin ; jamais d'exception (None)."""
import colorsys
import math


def _image(img):
    try:
        from PIL import Image
        if isinstance(img, (str, bytes)) or hasattr(img, "__fspath__"):
            with Image.open(img) as im:
                return im.convert("RGB").copy()
        return img.convert("RGB")
    except Exception:
        return None


def classer_teinte(h, teintes):
    """Teinte en degrés -> élément ou None (hors plage = couleur ambiguë)."""
    for el, plages in teintes.items():
        if any(a <= h <= b for a, b in plages):
            return el
    return None


def lire_losanges(img, cfg):
    """[élément | None] pour chaque losange de `cfg` (`config.elements_hud`). Teinte moyenne (vecteur) des pixels vifs de la zone ;
    moins de `pixels_min` pixels vifs : None. Format non 16:9 : [None] * n (zones non appliquées)."""
    zones = cfg.get("zones") or []
    im = _image(img)
    if im is None:
        return [None] * len(zones)
    w, h = im.size
    if abs(w / h - 16 / 9) > 0.02:
        return [None] * len(zones)
    sortie = []
    for x, y, lw, lh in zones:
        x0, y0 = int(x * w), int(y * h)
        x1, y1 = max(x0 + 1, int((x + lw) * w)), max(y0 + 1, int((y + lh) * h))
        c, s_, n = 0.0, 0.0, 0
        for yy in range(y0, min(y1, h)):
            for xx in range(x0, min(x1, w)):
                r, g, b = im.getpixel((xx, yy))
                hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if ss >= cfg.get("sat_min", 0.45) and vv >= cfg.get("val_min", 0.5):
                    c, s_, n = c + math.cos(hh * 2 * math.pi), s_ + math.sin(hh * 2 * math.pi), n + 1
        if n < cfg.get("pixels_min", 8):
            sortie.append(None)
            continue
        teinte = (math.degrees(math.atan2(s_, c)) + 360) % 360
        sortie.append(classer_teinte(teinte, cfg.get("teintes") or {}))
    return sortie


def element_de_la_run(images, mini_losanges=2, mini_images=2):
    """`images` = [[élément | None] par image HUD attachée à la run]. Élément strictement majoritaire, avec au moins `mini_losanges`
    losanges concordants sur au moins `mini_images` images ; sinon None."""
    from collections import Counter
    c = Counter(e for im in images for e in (im or []) if e)
    if not c:
        return None
    (el, n), *reste = c.most_common()
    if reste and reste[0][1] >= n:
        return None
    return el if n >= mini_losanges and sum(1 for im in images if el in (im or [])) >= mini_images else None
