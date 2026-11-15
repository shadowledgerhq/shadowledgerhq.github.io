"""Écran de composition dans les images d'une vidéo (SPEC_ETAPE2 §0, §1.3) : détection de l'écran, de l'onglet actif, choix
des images à analyser, et fournisseur d'images pour `builds.calculer` (PC : yt-dlp + ffmpeg, comme les tris 3-4).
Détection par la disposition (bouton d'entrée jaune + onglet actif de la colonne de gauche), pas par le texte : valable pour
toutes les langues d'interface. Réglages dans `pipeline/config/etape2.json` (`extraction`)."""
import tempfile
from pathlib import Path

ONGLETS = ("personnages", "artefacts", "competences", "benedictions", "noyaux")


def _np():
    import numpy as np
    return np


def bouton_present(image, cfg):
    """Le bouton jaune d'entrée (bas droite) est visible : on est sur l'écran de composition."""
    np = _np()
    a = np.asarray(image.convert("RGB")).astype(int)
    h, w = a.shape[:2]
    x0, y0, x1, y1 = cfg["extraction"]["bouton"]
    r = a[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    if r.size == 0:
        return False
    return float(((r[..., 0] > 200) & (r[..., 1] > 150) & (r[..., 2] < 110)).mean()) >= cfg["extraction"]["seuil_bouton"]


def onglet_actif(image, cfg):
    """Clé de l'onglet actif (`personnages`… `noyaux`) ou None : l'icône active est la plus blanche de la colonne de gauche."""
    np = _np()
    e = cfg["extraction"]["colonne_onglets"]
    a = np.asarray(image.convert("RGB")).astype(int)
    h, w = a.shape[:2]
    r, x = int(e["rayon"] * h), int(e["x"] * w)
    blancs = []
    for fy in e["y"]:
        y = int(fy * h)
        reg = a[max(0, y - r):y + r, max(0, x - r):x + r]
        blancs.append(float((reg.min(axis=2) > 205).mean()) if reg.size else 0.0)
    ordre = sorted(range(len(blancs)), key=lambda i: -blancs[i])
    meilleur, second = blancs[ordre[0]], blancs[ordre[1]]
    if meilleur < e["seuil_blanc"] or meilleur < e["rapport_2e"] * second:
        return None
    return ONGLETS[ordre[0]]


def analyser_image(image, cfg):
    """Onglet de l'écran de composition vu sur l'image, ou None (autre écran, onglet douteux, image de transition)."""
    return onglet_actif(image, cfg) if bouton_present(image, cfg) else None


def choisir_images(images_t, cfg):
    """`images_t` = [(t, image)] dans l'ordre du temps. Retourne ({onglet: [images]}, [t_min, t_max]) : au plus
    `max_par_onglet` images par onglet, réparties sur la durée où l'onglet est vu ; ([], None) si aucune."""
    n = cfg["extraction"]["max_par_onglet"]
    par = {}
    diag = {"images": len(images_t), "ecran": 0, "onglet_douteux": 0}
    for t, im in images_t:
        o = analyser_image(im, cfg)
        if bouton_present(im, cfg):
            diag["ecran"] += 1
            diag["onglet_douteux"] += 0 if o else 1
        if o:
            par.setdefault(o, []).append((t, im))
    sortie, temps = {}, []
    for o, l in par.items():
        pas = max(1, len(l) // n)
        choisies = l[::pas][:n]
        sortie[o] = [im for _, im in choisies]
        temps += [t for t, _ in l]
    choisir_images.diagnostic = diag
    return sortie, ([min(temps), max(temps)] if temps else None)


def fournisseur_pc(outils, cfg, journal=None):
    """Fournisseur d'images pour `builds.calculer(fournisseur=…)` : télécharge chaque vidéo une fois (`outils.telecharger`),
    extrait 1 image / `pas_s` s de 0 à `t_result` (`outils.images`), garde les images de l'écran de composition. Retourne
    `ctx -> ({onglet: [images]}, {"t_composition": [t0, t1], "erreur": texte | None})`."""
    from PIL import Image
    journal = journal or (lambda m: None)
    e = cfg["extraction"]
    cache = {}

    def lire(ctx):
        vid, t_fin = ctx["video_id"], ctx.get("t_result")
        fin = min(int(t_fin) if t_fin else e["fenetre_max_s"], e["fenetre_max_s"])
        cle = (vid, fin)
        if cle not in cache:
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    journal(f"  composition {vid} : téléchargement…")
                    chemin = outils.telecharger(vid, tmp)
                    images_t = []
                    for t, png in outils.images(chemin, [(0, fin, e["pas_s"])], tmp, "c"):
                        with Image.open(png) as im:
                            images_t.append((t, im.convert("RGB")))
                    cache[cle] = (*choisir_images(images_t, cfg), None)
                    d = choisir_images.diagnostic
                    journal(f"  composition {vid} : {d['images']} images, écran vu sur {d['ecran']}, onglet douteux sur {d['onglet_douteux']}, "
                            f"onglets : {', '.join(f'{o} ×{len(l)}' for o, l in cache[cle][0].items()) or 'aucun'}")
            except Exception as ex:                      # 429, ffmpeg, vidéo privée : build `pas_de_build`, raison notée
                cache[cle] = ({}, None, str(ex)[:160])
        images, t, err = cache[cle]
        return images, {"t_composition": t, "erreur": err}
    return lire
