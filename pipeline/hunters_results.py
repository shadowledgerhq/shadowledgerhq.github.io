"""SPEC v31 §3.1 : identité des chasseurs d'une run par les PORTRAITS des 6 lignes « Hunter Rank » de l'écran Results GB.

Banque apprise `data/icons/hunters_results/<id>-<n>.png` (portrait recadré d'une ligne). Elle se remplit SEULEMENT quand l'identité
vient d'un build `sûr` de l'étape 2 de la même run : chaque ligne est comparée (SIFT + RANSAC, `portraits.correspondances`) aux cartes
`data/icons/hunters_cartes/<id>.png` des chasseurs du build, et apprise si le couple est sans ambiguïté. Banque vide = aucun
`hunter_ids`, sans erreur. Reconnaissance : mêmes seuils que `portraits.apparier_cartes` (`portraits.min_corr_biblio`, `rapport`).
Zones (fractions) dérivées de `config.gb.zones.rang_k` / `zones_successeur.rang_k` : `config.gb.portraits_results` [À CALIBRER sur la
capture MJ2iz5TFmvM_recherche_223]. POC : zones du RESULT [À CALIBRER], non faites."""
from pathlib import Path

DOSSIER = ("data", "icons", "hunters_results")
MAX_PAR_CHASSEUR = 4


def zones_portraits(config, successeur=False):
    """6 zones (x, y, largeur, hauteur) en fractions : portrait à gauche du nombre de chaque ligne `Hunter Rank`."""
    gb = (config or {}).get("gb") or {}
    p = gb.get("portraits_results") or {"x": 0.068, "w": 0.085, "dy": -0.012, "h": 0.068}
    rangs = (gb.get("zones_successeur") if successeur else gb.get("zones")) or {}
    return [(p["x"], rangs[f"rang_{k}"][1] + p["dy"], p["w"], p["h"]) for k in range(1, 7) if f"rang_{k}" in rangs]


def decouper(img, zones):
    w, h = img.size
    return [img.crop((int(x * w), int(y * h), int((x + lw) * w), int((y + lh) * h))) for x, y, lw, lh in zones]


def dossier(racine):
    return Path(racine).joinpath(*DOSSIER)


def charger_banque(racine):
    """{id: [images PIL]} ; {} si la banque n'existe pas ou est vide."""
    from PIL import Image
    sortie = {}
    d = dossier(racine)
    for f in sorted(d.glob("*.png")) if d.exists() else []:
        ident = f.stem.rsplit("-", 1)[0]
        try:
            with Image.open(f) as im:
                sortie.setdefault(ident, []).append(im.convert("RGB").copy())
        except OSError:
            continue
    return sortie


def reconnaitre(crops, banque, cfg):
    """[id | None] par ligne. Un id est retenu si n ≥ `min_corr_biblio` et n ≥ `rapport` × le meilleur des autres (autre chasseur sur la
    ligne, même chasseur sur une autre ligne). Banque vide : [None] * n."""
    if not banque:
        return [None] * len(crops)
    import portraits
    c = (cfg or {}).get("portraits") or {}
    mini, rapport = c.get("min_corr_biblio", 40), c.get("rapport", 2)
    m = [{k: max(portraits.correspondances(ref, cr) for ref in refs) for k, refs in banque.items()} for cr in crops]
    sortie = []
    for i, ligne in enumerate(m):
        best = max(ligne, key=ligne.get)
        autres = [v for k, v in ligne.items() if k != best] + [m[j][best] for j in range(len(m)) if j != i]
        sortie.append(best if ligne[best] >= mini and ligne[best] >= rapport * max(autres + [1]) else None)
    return sortie


def apprendre(racine, ids_build, crops, cartes, cfg):
    """Apprend les portraits des lignes dont l'identité est établie par le build : `cartes` = {id: image carte} des chasseurs du
    build (`portraits.charger_cartes`) ; une ligne est apprise si SA carte est la seule à dépasser le seuil. Retourne le nombre appris."""
    import portraits
    c = (cfg or {}).get("portraits") or {}
    mini, rapport = c.get("min_corr_biblio", 40), c.get("rapport", 2)
    cartes = {k: v for k, v in cartes.items() if k in set(ids_build)}
    if not cartes:
        return 0
    n_appris = 0
    for cr in crops:
        ligne = {k: max(portraits.correspondances(c, cr) for c in (carte if isinstance(carte, (list, tuple)) else [carte])) for k, carte in cartes.items()}
        best = max(ligne, key=ligne.get)
        if ligne[best] >= mini and ligne[best] >= rapport * max([v for k, v in ligne.items() if k != best] + [1]):
            d = dossier(racine)
            d.mkdir(parents=True, exist_ok=True)
            existants = sorted(d.glob(f"{best}-*.png"))
            if len(existants) < MAX_PAR_CHASSEUR:
                cr.convert("RGB").save(d / f"{best}-{len(existants) + 1}.png")
                n_appris += 1
    return n_appris


def lire(img, config, racine, successeur=False):
    """([id | None] * 6 | None, nombre reconnu). None si la banque est vide ou l'image n'est pas 16:9."""
    w, h = img.size
    if abs(w / h - 16 / 9) > 0.02:
        return None, 0
    banque = charger_banque(racine)
    if not banque:
        return None, 0
    ids = reconnaitre(decouper(img, zones_portraits(config, successeur)), banque, config)
    return ids, sum(1 for i in ids if i)
