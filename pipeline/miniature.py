"""SPEC_ETAPE1 v34 §3 : tri 2, texte de la miniature (PC : tesseract ; la miniature se télécharge sur i.ytimg.com, sans yt-dlp).

Les miniatures portent un texte stylisé (gros chiffres blancs cerclés de sombre) que l'OCR de l'image entière lit mal (« 19. n926 » pour
19.926). On lit donc plusieurs prétraitements (image grise, masque des pixels blancs à plusieurs seuils, sur l'image entière et sur ses
bandes haute et basse), chacun sous plusieurs `psm`, et on garde un score seulement si la MÊME valeur sort d'au moins `accord_min` lectures.
Le texte passe ensuite par les règles du tri 1 (`scores.py` : plage plausible, hypothèses exclues, chrono nu `\\d{1,3}[.,:;]\\d{3}` isolé au BOT)
et donne une lecture provisoire : `score_source = "miniature"`, `exact = false`, `a_verifier`, `detail.texte_miniature = true`.
Une miniature qui ressemble à un écran RESULT est en plus lue comme un écran (`ocr_ecrans.lectures_depuis_texte`, source `miniature`)."""
import re
import urllib.request
from collections import Counter
from pathlib import Path

import scores
import tri1

DEFAUTS = {"actif": True, "accord_min": 2, "accord_seul": 3, "accord_stop": 3, "seuils": [200, 225], "psm_chiffres": [7, 11], "psm_texte": [11, 6],
           "echelle": 2, "timeout_s": 40, "urls": ["maxresdefault", "hqdefault"],
           "regions": {"plein": [0, 0, 1, 1], "bas": [0, 0.7, 1, 1], "bas-gauche": [0, 0.7, 0.6, 1], "bas-droite": [0.4, 0.7, 1, 1],
                       "haut": [0, 0, 1, 0.3], "haut-gauche": [0, 0, 0.6, 0.3], "haut-droite": [0.4, 0, 1, 0.3]}}
CHIFFRES = ["-c", "tessedit_char_whitelist=0123456789.,:;"]


_GROS_NOMBRE = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d{3}){2,}(?![\d])")      # 11.736.161.929 : tableau de scores, pas un chrono


def reglages(config):
    return {**DEFAUTS, **(config.get("miniature") or {})}


def telecharger(vid, tmp, cfg, ouvrir=None, journal=lambda m: None):
    """Chemin de la miniature (`maxresdefault`, sinon `hqdefault`) ou None. Ne lève jamais."""
    ouvrir = ouvrir or (lambda url: urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
    for nom in cfg["urls"]:
        try:
            with ouvrir(f"https://i.ytimg.com/vi/{vid}/{nom}.jpg") as rep:
                donnees = rep.read()
            if len(donnees) > 2000:
                chemin = Path(tmp) / f"{vid}_miniature_{nom}.jpg"
                chemin.write_bytes(donnees)
                return chemin
        except Exception as e:                       # 404 (pas de maxresdefault), réseau : on essaie la suivante
            journal(f"  miniature {nom} : {e}")
    return None


def variantes(chemin, tmp, cfg):
    """Générateur de (étiquette, png) : image grise entière, puis masque des pixels blancs (noir sur blanc) par région et par seuil (PIL + numpy).
    Le fichier est supprimé par l'appelant."""
    from PIL import Image
    import numpy as np
    im = Image.open(chemin).convert("RGB")
    larg, haut = im.size
    tmp = Path(tmp)
    p = tmp / "_min_gris.png"
    im.convert("L").save(p)
    yield "gris", p
    a = np.asarray(im).astype(int)
    for region, (fx0, fy0, fx1, fy1) in cfg["regions"].items():
        sub = a[int(fy0 * haut):int(fy1 * haut), int(fx0 * larg):int(fx1 * larg)]
        if sub.size == 0:
            continue
        for seuil in cfg["seuils"]:
            masque = sub.min(axis=2) >= seuil
            img = Image.fromarray(np.where(masque, 0, 255).astype("uint8"))
            img = img.resize((img.width * cfg["echelle"], img.height * cfg["echelle"]))
            p = tmp / f"_min_{region}_{seuil}.png"
            img.save(p)
            yield f"{region}-{seuil}", p


def lire_textes(outils, chemin, tmp, cfg, langues="eng", modes=("bot",), config=None):
    """Textes OCR des variantes. Au BOT : lecture des chiffres seulement (liste blanche `0-9.,:;s`, `psm` 7 et 11) : le chrono est un gros
    nombre stylisé dont le point est sinon lu comme un chiffre (`192926`) ; les autres modes : texte libre (`psm_texte`). Arrêt dès qu'une
    valeur atteint `accord_stop` lectures identiques. Une variante trop lente ou en erreur donne un texte vide."""
    textes = []
    for _, png in variantes(chemin, tmp, cfg):
        essais = []
        if "bot" in modes:          # chiffres : anglais seul, quelle que soit la langue de la vidéo
            essais += [(psm, CHIFFRES, "eng") for psm in cfg["psm_chiffres"]]
        if any(m != "bot" for m in modes):
            essais += [(psm, None, langues) for psm in cfg["psm_texte"]]
        for psm, extra, langue in essais:
            try:
                textes.append(outils.ocr(png, langue, psm, cfg["timeout_s"], extra) or "")
            except Exception:
                textes.append("")
        Path(png).unlink(missing_ok=True)
        if config is not None and all((voter(textes, m, config, cfg["accord_stop"]) is not None) for m in modes):
            break
    return textes


def voter(textes, mode, config, accord_min=2):
    """Valeur du score lue à l'identique par au moins `accord_min` textes (règles du tri 1 : `scores.candidats`, hors hypothèses), ou None.
    Au BOT, seul un chrono à millièmes (`\\d{1,3}[.,:;]\\d{3}` ou `mm:ss.mmm`) compte : un chrono arrondi (`19s`, `7 s`) est trop souvent
    du bruit de l'OCR sur une image stylisée (essai du 17/11 sur 33 miniatures BOT : `7.0`, `10.0`, `130.0`, `149.0` sans millièmes, tous faux).
    Retourne {"valeur", "brut", "votes", "autres": [valeurs]} ; égalité de votes : le premier lu."""
    p = scores.plage(mode, config)
    if p is None:
        return None
    compte, brut, ordre, virgule = Counter(), {}, [], set()
    for original in textes:
        vus = set()
        # v35.1 : sur une miniature lue en chiffres seuls (liste blanche) au BOT, la virgule entre deux chiffres est un point mal lu (`19,926` =
        # 19.926, sans unité exigée) ; la règle v35 « virgule + 3 chiffres = chrono seulement avec une unité » vaut pour titre, description et sous-titres
        texte = re.sub(r"(?<=\d),(?=\d)", ".", original) if mode == "bot" else original
        for c in scores.candidats(texte, mode, p, config):
            if mode == "bot" and c.get("decimales") != 3:          # BOT : seul un chrono à millièmes (`19.926`) est lu sur une miniature
                continue
            if scores.est_hypothese(texte, c["pos"], c["pos"] + len(c["brut"]), config) or c["valeur"] in vus:
                continue
            vus.add(c["valeur"])
            if "," in original[c["pos"]:c["pos"] + len(c["brut"])]:
                virgule.add(c["valeur"])
            compte[c["valeur"]] += 1
            brut.setdefault(c["valeur"], c["brut"])
            if c["valeur"] not in ordre:
                ordre.append(c["valeur"])
    retenus = [v for v in ordre if compte[v] >= accord_min]
    if not retenus:
        return None
    v = max(retenus, key=lambda x: (compte[x], -ordre.index(x)))
    return {"valeur": v, "brut": brut[v], "votes": compte[v], "autres": [x for x in retenus if x != v], "virgule": v in virgule}


def _texte_canonique(mode, vote):
    """Texte relu par `tri1.lectures_texte` : chrono à 3 décimales au BOT (séparateur `.`), sinon le texte lu."""
    if mode == "bot":
        return f"{vote['valeur']:.3f}"
    return vote["brut"]


NOTE_VIRGULE = "miniature : virgule lue comme point"
MOTS_ECRAN_RESULTS = ("phase", "result", "結果")


def est_capture_results(textes):
    """v35 : la miniature est une capture d'écran Results (mots Phase / RESULT / Results / 結果 lus par l'OCR, majuscules et espaces ignorés) :
    elle n'est jamais lue comme du texte, seule la détection d'écran du tri 2 (dernière phase, `pc.traiter_miniature`) s'applique."""
    bas = re.sub(r"\s+", "", " ".join(t for t in textes if t)).lower()
    return any(m in bas for m in MOTS_ECRAN_RESULTS)


def lectures_texte(vid, meta, textes, config):
    """Lectures provisoires (une par mode du `mode_guess` qui a un score voté), `score_source = "miniature"`. Aucune pour une capture d'écran
    Results (v35, `est_capture_results`)."""
    if est_capture_results(textes):
        return []
    cfg = reglages(config)
    sortie = []
    for mode in meta.get("mode_guess", []):
        if mode == "bot" and any(_GROS_NOMBRE.search(t) for t in textes):
            continue        # écran de scores à grands nombres (Hunter Rank…) : un « 60.278 » y est un morceau de nombre, pas un chrono
        vote = voter(textes, mode, config, cfg["accord_min"])
        if not vote:
            continue
        lecs, _ = tri1.lectures_texte({**meta, "mode_guess": [mode]}, [("miniature", _texte_canonique(mode, vote))], config)
        for lec in lecs:
            lec["detail"]["texte_miniature"] = True
            lec["detail"]["votes_miniature"] = vote["votes"]
            if vote.get("virgule"):
                lec["notes"].append(NOTE_VIRGULE)
            if vote["autres"]:
                lec["notes"].append("miniature, autres valeurs lues : " + ", ".join(str(x) for x in vote["autres"]))
            sortie.append(lec)
    return sortie


def lire(vid, meta, outils, config, tmp, langues="eng", telecharger_fn=None, journal=lambda m: None):
    """Tri 2 d'une vidéo. Retourne (lectures_texte, texte_plein | None, état) : les lectures provisoires du texte de la miniature, le texte OCR
    de l'image entière (détection d'un écran RESULT) et l'état (`fait` | `absent` = miniature introuvable | `erreur` = rien n'est marqué,
    la miniature sera relue au prochain passage). L'absence de tesseract (`OutilAbsent`) remonte à l'appelant."""
    cfg = reglages(config)
    chemin = telecharger(vid, tmp, cfg, telecharger_fn, journal)
    if chemin is None:
        return [], None, "absent"
    try:
        modes = tuple(meta.get("mode_guess", [])) or ("bot",)
        textes = lire_textes(outils, chemin, tmp, cfg, langues, modes, config)
        plein = outils.ocr(chemin, langues, 6, cfg["timeout_s"], None) or ""
    except Exception as e:
        if type(e).__name__ == "OutilAbsent":
            raise
        journal(f"  miniature : {e}")
        return [], None, "erreur"
    finally:
        Path(chemin).unlink(missing_ok=True)
    return lectures_texte(vid, meta, textes + [plein], config), plein, "fait"
