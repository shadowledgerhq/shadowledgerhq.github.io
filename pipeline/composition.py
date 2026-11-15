"""Écran de composition dans les images d'une vidéo (SPEC_ETAPE2 §0, §1.3) : détection de l'écran, de l'onglet actif, choix
des images à analyser, et fournisseur d'images pour `builds.calculer` (PC : yt-dlp + ffmpeg, comme les tris 3-4).
Détection par la disposition (bouton d'entrée jaune + onglet actif de la colonne de gauche), pas par le texte : valable pour
toutes les langues d'interface. Réglages dans `pipeline/config/etape2.json` (`extraction`)."""
import re
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


def _lire_hors_composition(outils, cfg, autres, journal, ocr_debug, vid, toutes=None):
    """OCR rapide d'une image sur `hors_compo.pas` des images qui ne sont pas la composition ; écran reconnu -> OCR complet.
    Retourne [(ecran, texte)] (2 par type au plus ; `hors_compo.ocr_max` appels rapides au plus). Erreur d'OCR : image ignorée."""
    import ecrans_hors_compo as H
    h = cfg.get("hors_compo") or {}
    pas, maxi, langues = h.get("pas", 2), h.get("ocr_max", 120), h.get("langues", "jpn+eng")
    lus, vus, appels, vides, erreurs = [], {}, 0, 0, 0
    _lire_hors_composition.resume = resume = []        # diagnostic : (t, début du texte lu) de chaque image passée à l'OCR rapide
    forcer = 0                       # images lues malgré le pas : le panneau d'options des statues apparaît en fondu après la liste
    ids, k = {str(p) for _, p in autres}, -1
    for t, png in (toutes or autres):
        est = toutes is None or str(png) in ids              # image « autre écran » ; les autres (classées composition) ne sont lues que juste après un écran reconnu
        k += 1 if est else 0
        if appels >= maxi or (est and k % pas and forcer <= 0) or (not est and forcer <= 0):
            forcer -= 1
            continue
        forcer -= 1
        appels += 1
        try:
            rapide = outils.ocr(outils.reduire(png, h.get("largeur", 960)), langues, 11, 40)
            vides += 0 if rapide.strip() else 1
            resume.append((t, " | ".join(rapide.split())[:240]))
            ecran = H.detecter(rapide, cfg)
            if ecran == "statues":
                forcer = h.get("suite_images", 3)
            plafond = (cfg["ecrans"].get(ecran) or {}).get("lectures_max", 2) if ecran else 2     # statues : le panneau d'options apparaît en fondu
            if not ecran or vus.get(ecran, 0) >= plafond:
                continue
            texte = outils.ocr(png, langues, 6, 120)
        except Exception as ex:                      # OCR trop lent / tesseract absent : on passe
            erreurs += 1
            if erreurs <= 3:
                journal(f"  hors composition t={t} : {str(ex)[:80]}")
            continue
        ecran = H.detecter(texte, cfg) or ecran
        vus[ecran] = vus.get(ecran, 0) + 1
        lus.append((ecran, texte))
        journal(f"  écran {ecran} lu à t={t} s")
        try:
            zl = _lire_zones(outils, cfg, ecran, png, t, journal, texte)
            lus += zl
            if ocr_debug:
                for nom_z, txt_z in zl:
                    (Path(ocr_debug) / f"{vid}_hors-compo_{t}_{nom_z}.txt").write_text(txt_z, encoding="utf-8")
        except Exception as ex:                      # recadrage/OCR de zone : jamais bloquant
            journal(f"  zones {ecran} t={t} : {str(ex)[:80]}")
        if ocr_debug:
            from pathlib import Path
            Path(ocr_debug).mkdir(parents=True, exist_ok=True)
            (Path(ocr_debug) / f"{vid}_hors-compo_{t}_{ecran}.txt").write_text(texte, encoding="utf-8")
            try:                                          # image réduite (JPEG) pour caler les zones de lecture à distance
                from PIL import Image as _Im
                with _Im.open(png) as im:
                    im = im.convert("RGB")
                    im.thumbnail((1600, 900))
                    im.save(Path(ocr_debug) / f"{vid}_hors-compo_{t}_{ecran}.jpg", quality=80)
            except Exception:
                pass
    journal(f"  hors composition : {len(autres)} images, {appels} lues par l'OCR rapide ({vides} sans texte, {erreurs} erreurs), "
            f"écrans reconnus : {', '.join(e for e, _ in lus) or 'aucun'}")
    return lus


def _ocr_zone(outils, png, zone, langues, psm, blanc, seuils=(170, None, 140, 200), valide=None, vote=False):
    """Texte d'une zone (fractions x, y, l, h) agrandie ×3 ; `blanc` : liste blanche tesseract. Essais : brut puis noir et blanc à
    plusieurs seuils ; le premier texte qui satisfait `valide` (regex) l'emporte, sinon le premier texte non vide (ou "")."""
    premier, valides = "", []
    for seuil in seuils:
        crop = outils.recadrer(png, zone, 3, seuil)
        texte = outils.ocr(crop, langues, psm, 20, ["-c", f"tessedit_char_whitelist={blanc}"] if blanc else None).strip()
        if texte and (valide is None or re.fullmatch(valide, texte)):
            if not vote:
                return texte
            valides.append(texte)
        premier = premier or texte
    if valides:                                     # vote : texte le plus fréquent (égalité : le plus long, un « 1 » fin est souvent perdu)
        return max(set(valides), key=lambda x: (valides.count(x), len(x)))
    return premier


def _lire_zones(outils, cfg, ecran, png, t, journal, texte=""):
    """Lectures par zone (SPEC v3, [À CONFIRMER] sur le PC : positions mesurées sur UNE vidéo JA 1920×1080). Retourne des lectures
    `("attributs_zone", "id: valeur" par ligne)` (fiche de SJW) ou `("statues_zone", json)` (grades, statue sélectionnée, options)."""
    if not hasattr(outils, "recadrer"):
        return []
    e = cfg["ecrans"]
    if ecran == "fiche_sjw" and e["fiche_sjw"].get("zones_attributs"):
        lignes = []
        for ident, zone in e["fiche_sjw"]["zones_attributs"].items():
            texte = _ocr_zone(outils, png, zone, "eng", 7, "0123456789,", valide=r"\d{1,3}(?:,\d{3})*|\d+", vote=True)
            lignes.append(f"{ident}: {texte}")
        journal(f"  fiche_sjw zones t={t} : " + " ; ".join(lignes))
        return [("attributs_zone", "\n".join(lignes))]
    z = e.get("statues", {}).get("zones")
    if ecran == "statues" and z:
        from PIL import Image
        with Image.open(png) as im:
            gris = im.convert("L")
            W, H = gris.size
            def moyenne(zone):
                x, y, l, h = zone
                box = gris.crop((int(x * W), int(y * H), int((x + l) * W), int((y + h) * H)))
                return sum(box.getdata()) / max(1, box.size[0] * box.size[1])
            lum = [moyenne(zn) for zn in z["selection"]]
        grades = []
        for zn in z["grades"]:
            g = _ocr_zone(outils, png, zn, "eng", 10, "EDCBAS", (None, 120, 180), valide=r"[EDCBAS]").strip()[:1]
            grades.append(g if g in list("EDCBAS") else None)
        reste = sorted(lum)[:-1]
        mediane = reste[len(reste) // 2]
        haut = max(range(len(lum)), key=lambda i: lum[i])
        selection = haut + 1 if lum[haut] >= z.get("seuil_selection", 80) and lum[haut] >= z.get("ratio_selection", 1.6) * max(mediane, 1) else None
        panneau = not texte or any(_n_ent in re.sub(r"\s+", "", texte) for _n_ent in e["statues"]["entete_options"]["ja"])     # panneau d'options visible ?
        options = [" ".join(_ocr_zone(outils, png, zn, e["statues"].get("langues", "jpn+eng"), 6, None, (None, 150)).split()) if panneau else "" for zn in z["options"]]
        og = [(_ocr_zone(outils, png, zn, "eng", 10, "EDCBAS", (None, 120, 180), valide=r"[EDCBAS]").strip()[:1] or None) if panneau else None for zn in z.get("options_grades", [])]
        og = [g if g in list("EDCBAS") else None for g in og]
        journal(f"  statues zones t={t} : grades {grades}, sélection {selection}, options {list(zip(og, options))}")
        import json
        return [("statues_zone", json.dumps({"t": t, "grades": grades, "selection": selection, "options": options, "options_grades": og}, ensure_ascii=False))]
    return []


def fournisseur_pc(outils, cfg, journal=None, ocr_debug=None):
    """Fournisseur d'images pour `builds.calculer(fournisseur=…)` : télécharge chaque vidéo une fois (`outils.telecharger`),
    extrait 1 image / `pas_s` s de 0 à `t_result` (`outils.images`), garde les images de l'écran de composition. Retourne
    `ctx -> ({onglet: [images]}, {"t_composition": [t0, t1], "erreur": texte | None, "ecrans": [(ecran, texte)]})`.
    v3 : les images qui ne sont PAS la composition passent par un OCR rapide (image réduite) ; un écran hors composition
    reconnu (`ecrans_hors_compo.detecter`) est relu en entier, 2 lectures au plus par type. `ocr_debug` : dossier où
    écrire les textes lus (diagnostic, `--garder-ocr`)."""
    from PIL import Image
    journal = journal or (lambda m: None)
    e = cfg["extraction"]
    cache = {}

    def lire(ctx):
        vid, t_fin = ctx["video_id"], ctx.get("t_result")
        fin = min(int(t_fin) if t_fin else e["fenetre_max_s"], e["fenetre_max_s"])
        debut = min(int(ctx.get("t_debut") or 0), max(fin - 1, 0))      # run 2 d'une même vidéo : on repart du résultat de la run 1
        cle = (vid, debut, fin)
        if cle not in cache:
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    journal(f"  composition {vid} : téléchargement…")
                    chemin = outils.telecharger(vid, tmp)
                    images_t, autres, toutes = [], [], []
                    for t, png in outils.images(chemin, [(debut, fin - debut, e["pas_s"])], tmp, "c"):
                        with Image.open(png) as im:
                            rgb = im.convert("RGB")
                        images_t.append((t, rgb))
                        toutes.append((t, png))
                        if not analyser_image(rgb, cfg):
                            autres.append((t, png))
                    ecrans = _lire_hors_composition(outils, cfg, autres, journal, ocr_debug, vid, toutes)
                    cache[cle] = (*choisir_images(images_t, cfg), None, ecrans)
                    d = choisir_images.diagnostic
                    journal(f"  composition {vid} : {d['images']} images, écran vu sur {d['ecran']}, onglet douteux sur {d['onglet_douteux']}, "
                            f"onglets : {', '.join(f'{o} ×{len(l)}' for o, l in cache[cle][0].items()) or 'aucun'}")
            except Exception as ex:                      # 429, ffmpeg, vidéo privée : build `pas_de_build`, raison notée
                cache[cle] = ({}, None, str(ex)[:160], [])
        images, t, err, ecrans = cache[cle]
        return images, {"t_composition": t, "erreur": err, "ecrans": ecrans, "ocr_resume": list(getattr(_lire_hors_composition, "resume", []))}
    return lire
