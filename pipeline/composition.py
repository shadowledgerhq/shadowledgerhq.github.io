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


def _sans_debut_de_visite(l, ignorer, ecart):
    """Retire les `ignorer` premières images de chaque visite d'un onglet (images consécutives, écart ≤ `ecart` s) :
    juste après le changement d'onglet, les icônes ne sont pas encore affichées (fondu : le fond/portrait se voit à leur place).
    Une visite d'une seule image est gardée telle quelle."""
    if not ignorer:
        return l
    visites, cur = [], []
    for t, im in l:
        if cur and t - cur[-1][0] > ecart:
            visites.append(cur)
            cur = []
        cur.append((t, im))
    if cur:
        visites.append(cur)
    return [x for v in visites for x in (v[ignorer:] if len(v) > ignorer else v)]


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
    ignorer = cfg["extraction"].get("ignorer_debut", 0)
    ecart = cfg["extraction"].get("visite_ecart_s", 3)
    for o, l in par.items():
        temps += [t for t, _ in l]                       # fenêtre de composition : toutes les images vues
        l = _sans_debut_de_visite(l, ignorer, ecart)
        pas = max(1, len(l) // n)
        choisies = l[::pas][:n]
        sortie[o] = [im for _, im in choisies]
    choisir_images.diagnostic = diag
    return sortie, ([min(temps), max(temps)] if temps else None)


def _gris(image, largeur=320):
    np = _np()
    h = max(1, round(image.height * largeur / image.width))
    return np.asarray(image.convert("L").resize((largeur, h))).astype(float)


def instabilites(images):
    """Pour chaque image d'une suite serrée, écart moyen (niveaux de gris) avec la plus ressemblante de ses voisines
    (précédente, suivante) : faible = écran stable. Pendant un fondu, l'image diffère des deux voisines."""
    g = [_gris(im) for im in images]
    d = [float(abs(g[i] - g[i + 1]).mean()) for i in range(len(g) - 1)]
    sortie = []
    for i in range(len(g)):
        voisins = ([d[i - 1]] if i > 0 else []) + ([d[i]] if i < len(d) else [])
        sortie.append(max(voisins) if voisins else 0.0)      # max : stable seulement si les deux voisines lui ressemblent
    return sortie


def choisir_stables(images_t, cfg):
    """`images_t` = [(t, image)] serrées (≈ 0,5 s). Retourne {onglet: [indices dans images_t]} : par onglet, au plus
    `max_par_onglet` images parmi les plus stables (écart ≤ minimum + `stabilite_tol`), réparties dans le temps.
    Évite les images en fondu au changement d'onglet (portraits visibles, icônes pâles)."""
    e = cfg["extraction"]
    n, tol = e["max_par_onglet"], e.get("stabilite_tol", 1.5)
    inst = instabilites([im for _, im in images_t])
    par = {}
    for i, (t, im) in enumerate(images_t):
        o = analyser_image(im, cfg)
        if o:
            par.setdefault(o, []).append(i)
    sortie = {}
    for o, idx in par.items():
        mini = min(inst[i] for i in idx)
        bons = [i for i in idx if inst[i] <= mini + tol]
        pas = max(1, len(bons) // n)
        sortie[o] = bons[::pas][:n]
    return sortie


def _lire_hors_composition(outils, cfg, autres, journal, ocr_debug, vid, toutes=None):
    """OCR rapide d'une image sur `hors_compo.pas` des images qui ne sont pas la composition ; écran reconnu -> OCR complet.
    Retourne [(ecran, texte)] (2 par type au plus ; `hors_compo.ocr_max` appels rapides au plus). Erreur d'OCR : image ignorée."""
    import ecrans_hors_compo as H
    h = cfg.get("hors_compo") or {}
    pas, maxi, langues = h.get("pas", 2), h.get("ocr_max", 120), h.get("langues", "jpn+eng")
    lus, vus, appels, vides, erreurs = [], {}, 0, 0, 0
    _lire_hors_composition.resume = resume = []        # diagnostic : (t, début du texte lu) de chaque image passée à l'OCR rapide
    forcer = 0                       # images lues malgré le pas : le panneau d'options des statues apparaît en fondu après la liste
    ids, k, kc, appels_compo = {str(p) for _, p in autres}, -1, -1, 0
    for t, png in (toutes or autres):
        est = toutes is None or str(png) in ids              # image « autre écran » ; les autres (classées composition) ne sont lues que juste après un écran reconnu
        k += 1 if est else 0
        kc += 0 if est else 1
        # popup `討伐支援` : le bouton jaune reste visible, l'image est classée composition → 1 image sur `compo_pas`, seul cet écran est gardé
        sonde = (not est and forcer <= 0 and h.get("compo_pas") and kc % h["compo_pas"] == 0 and appels_compo < h.get("compo_ocr_max", 12)
                 and sum(1 for e_, _ in lus if e_ == "subjugation") < (cfg["ecrans"].get("subjugation") or {}).get("lectures_max", 2))
        if appels >= maxi or (est and k % pas and forcer <= 0) or (not est and forcer <= 0 and not sonde):
            forcer -= 1
            continue
        appels_compo += 1 if sonde else 0
        forcer -= 1
        appels += 1
        try:
            rapide = outils.ocr(outils.reduire(png, h.get("largeur", 960)), langues, 11, 40)
            vides += 0 if rapide.strip() else 1
            resume.append((t, " | ".join(rapide.split())[:240]))
            ecran = H.detecter(rapide, cfg)
            if sonde and ecran != "subjugation":
                continue
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


def _ocr_zone(outils, png, zone, langues, psm, blanc, seuils=(170, None, 140, 200), valide=None, vote=False, psms=None):
    """Texte d'une zone (fractions x, y, l, h) agrandie ×3 ; `blanc` : liste blanche tesseract. Essais : brut puis noir et blanc à
    plusieurs seuils ; le premier texte qui satisfait `valide` (regex) l'emporte, sinon le premier texte non vide (ou "")."""
    premier, valides = "", []
    for seuil in seuils:
        crop = outils.recadrer(png, zone, 3, seuil)
        for ps in (psms or (psm,)):                  # plusieurs modes de segmentation : psm 7 perd parfois le « 1 » initial (essai 15/11 : 19 lu 9)
            texte = outils.ocr(crop, langues, ps, 20, ["-c", f"tessedit_char_whitelist={blanc}"] if blanc else None).strip()
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
            texte = _ocr_zone(outils, png, zone, "eng", 7, "0123456789,", valide=r"\d{1,3}(?:,\d{3})*|\d+", vote=True, psms=(7, 8, 13))
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
            g = _ocr_zone(outils, png, zn, "eng", 10, "EDCBAS", (None, 120, 180, 220), valide=r"[EDCBAS]", vote=True).strip()[:1]
            grades.append(g if g in list("EDCBAS") else None)
        reste = sorted(lum)[:-1]
        mediane = reste[len(reste) // 2]
        haut = max(range(len(lum)), key=lambda i: lum[i])
        selection = haut + 1 if lum[haut] >= z.get("seuil_selection", 80) and lum[haut] >= z.get("ratio_selection", 1.6) * max(mediane, 1) else None
        panneau = not texte or any(_n_ent in re.sub(r"\s+", "", texte) for _n_ent in e["statues"]["entete_options"]["ja"])     # panneau d'options visible ?
        options = [" ".join(_ocr_zone(outils, png, zn, e["statues"].get("langues", "jpn+eng"), 6, None, (None, 150)).split()) if panneau else "" for zn in z["options"]]
        og = [(_ocr_zone(outils, png, zn, "eng", 10, "EDCBAS", (None, 120, 180, 220), valide=r"[EDCBAS]", vote=True).strip()[:1] or None) if panneau else None for zn in z.get("options_grades", [])]
        effet = " ".join(_ocr_zone(outils, png, z["effet"], e["statues"].get("langues", "jpn+eng"), 6, None, (None, 150)).split()) if panneau and z.get("effet") else ""
        og = [g if g in list("EDCBAS") else None for g in og]
        journal(f"  statues zones t={t} : grades {grades}, sélection {selection}, options {list(zip(og, options))}")
        import json
        return [("statues_zone", json.dumps({"t": t, "grades": grades, "selection": selection, "options": options, "options_grades": og, "effet": effet}, ensure_ascii=False))]
    zs = e.get("subjugation", {}).get("zones")
    if ecran == "subjugation" and zs:
        from PIL import Image
        import json
        with Image.open(png) as im:
            gris = im.convert("L")
            W, H = gris.size
            def moyenne(zone):
                x, y, l, h = zone
                box = gris.crop((int(x * W), int(y * H), int((x + l) * W), int((y + h) * H)))
                return sum(box.getdata()) / max(1, box.size[0] * box.size[1])
            lum = [[round(moyenne(zn), 1) for zn in col] for col in zs["cases"]]
        cartes = [[" ".join(_ocr_zone(outils, png, zn, zs.get("langues", "jpn"), 6, None, (None, 150)).split()) for zn in col] for col in zs["cases"]]
        journal(f"  subjugation zones t={t} : luminosités {lum}, cartes {cartes}")
        return [("subjugation_zone", json.dumps({"t": t, "cartes": cartes, "lum": lum}, ensure_ascii=False))]
    return []


def _affiner_onglet(outils, cfg, chemin, onglet, temps, tmp):
    """Passe à `pas_tres_fin_s` (0,1 s) sur [min(temps) − marge, max(temps) + marge] : retourne les images (pleine taille) les plus
    stables de cet onglet (`choisir_stables`), ou None (échec, onglet absent : l'appelant garde le choix à 0,5 s)."""
    from PIL import Image
    e = cfg["extraction"]
    pas, marge = e["pas_tres_fin_s"], e.get("marge_tres_fin_s", 0.5)
    t0 = max(0, min(temps) - marge)
    try:
        trouvees = outils.images(chemin, [(t0, max(temps) + marge - t0 + pas, pas)], tmp, f"tf{onglet[:3]}")
        petites = []
        for t, png in trouvees:
            with Image.open(png) as im:
                rgb = im.convert("RGB")
                rgb.thumbnail((800, 800))
            petites.append((t, rgb))
        idx = choisir_stables(petites, cfg).get(onglet)
        if not idx:
            return None
        sortie = []
        for i in idx:
            with Image.open(trouvees[i][1]) as im:
                sortie.append(im.convert("RGB"))
        return sortie
    except Exception:
        return None


def _affiner(outils, cfg, chemin, fenetre, tmp, journal):
    """Seconde extraction à `pas_fin_s` (0,5 s) dans la fenêtre de composition ± `marge_fin_s` ; garde par onglet les images
    les plus stables (`choisir_stables`). Échec ou onglet absent : retombe sur le choix à `pas_s`. Mêmes valeurs de retour
    que `choisir_images` ; d'abord les images (réduites pour l'analyse, rechargées en pleine taille pour les gardées)."""
    from PIL import Image
    e = cfg["extraction"]
    t0 = max(0, fenetre[0] - e.get("marge_fin_s", 1))
    t1 = fenetre[1] + e.get("marge_fin_s", 1)
    try:
        trouvees = outils.images(chemin, [(t0, t1 - t0 + e["pas_fin_s"], e["pas_fin_s"])], tmp, "fin")
        petites = []
        for t, png in trouvees:
            with Image.open(png) as im:
                rgb = im.convert("RGB")
                rgb.thumbnail((800, 800))
            petites.append((t, rgb))
        choix = choisir_stables(petites, cfg)
        sortie = {}
        for o, idx in choix.items():
            sortie[o] = None
            if e.get("pas_tres_fin_s"):        # essai du 15/11 : onglet « artefacts » capté seulement en fondu à 0,5 s -> passe à 0,1 s
                sortie[o] = _affiner_onglet(outils, cfg, chemin, o, [trouvees[i][0] for i in idx], tmp)
            if not sortie[o]:
                sortie[o] = []
                for i in idx:
                    with Image.open(trouvees[i][1]) as im:
                        sortie[o].append(im.convert("RGB"))
        journal(f"  composition : affinage à {e['pas_fin_s']} s, {len(trouvees)} images, onglets : "
                f"{', '.join(f'{o} ×{len(l)}' for o, l in sortie.items()) or 'aucun'}")
        return sortie, fenetre
    except Exception as ex:
        journal(f"  composition : affinage impossible ({str(ex)[:100]}), choix à {e['pas_s']} s conservé")
        return None, fenetre


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
                    if e.get("pas_fin_s") and cache[cle][1]:
                        fin, fenetre = _affiner(outils, cfg, chemin, cache[cle][1], tmp, journal)
                        if fin:                                  # onglet absent à 0,5 s : on garde le choix à pas_s
                            cache[cle] = ({**cache[cle][0], **fin}, fenetre, None, ecrans)
                    if ocr_debug:                    # diagnostic (--garder-ocr) : images de composition retenues, pour définir les zones des onglets
                        Path(ocr_debug).mkdir(parents=True, exist_ok=True)
                        for onglet, ims in cache[cle][0].items():
                            for k, im in enumerate(ims):
                                im = im.copy()
                                im.thumbnail((1600, 900))
                                im.save(Path(ocr_debug) / f"{vid}_compo_{onglet}_{k}.jpg", quality=85)
                    journal(f"  composition {vid} : {d['images']} images, écran vu sur {d['ecran']}, onglet douteux sur {d['onglet_douteux']}, "
                            f"onglets : {', '.join(f'{o} ×{len(l)}' for o, l in cache[cle][0].items()) or 'aucun'}")
            except Exception as ex:                      # 429, ffmpeg, vidéo privée : build `pas_de_build`, raison notée
                cache[cle] = ({}, None, str(ex)[:160], [])
        images, t, err, ecrans = cache[cle]
        return images, {"t_composition": t, "erreur": err, "ecrans": ecrans, "ocr_resume": list(getattr(_lire_hors_composition, "resume", []))}
    return lire
