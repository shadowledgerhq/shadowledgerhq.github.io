"""Relevé automatique de l'ordre des compétences d'une run (SPEC_ROTATION.md v1, discussion 3).

Passage PC, après les tris 3-4, sur la vidéo DÉJÀ téléchargée : images à 10/s entre les bornes de la run (720p), états des boutons
(« prêt » -> « en recharge »), jauge de noyau, portrait actif (tag), fusion des doublons < 0,5 s, confiance par les recharges de la base.
Sortie : `data/rotations/<semaine>/<mode>/<video_id>.json` + `_rapport.md`. Aucune image complète n'est gardée (SPEC §2.7) : seulement
des recadrages dans `data/rotations/<semaine>/<mode>/_crops/`.

Les zones du HUD (`config/rotation.json`, `zones`) sont `null` tant que le HUD n'a pas été calibré [À CALIBRER] sur wJ9CwjKwyco : le fichier
porte alors `limites: ["hud-non-trouve"]`, aucun événement n'est inventé, et quelques recadrages de grandes zones du HUD sont gardés pour
la calibration. Les fonctions de détection sont pures (images PIL + zones en fractions `[x0, y0, x1, y1]`) et testées sur des images synthétiques."""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "pipeline" / "config" / "rotation.json"
SLOTS = ("skill_1", "skill_2", "ultimate", "core", "tag", "sjw_skill_1", "sjw_skill_2", "sjw_ultimate", "sjw_qte")
BOUTONS_HUNTER = ("skill_1", "skill_2", "ultimate")
BOUTONS_SJW = ("sjw_skill_1", "sjw_skill_2", "sjw_ultimate", "sjw_qte")
TYPE_BASE = {"skill_1": "skill_1", "skill_2": "skill_2", "ultimate": "ultimate"}      # `type` des compétences dans `hunters.json`


def charger_config(chemin=CONFIG):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


# --- mesures sur les images ---------------------------------------------------------------------------------------------

def _np():
    import numpy as np
    return np


def recadrer(image, zone):
    w, h = image.size
    return image.crop((round(zone[0] * w), round(zone[1] * h), round(zone[2] * w), round(zone[3] * h)))


def luminance(image, zone):
    """Luminance moyenne (0-255) de la zone."""
    np = _np()
    return float(np.asarray(recadrer(image, zone).convert("L"), dtype=float).mean())


def remplissage(image, zone, seuil=128):
    """Part (0-1) des pixels de la zone plus clairs que `seuil` : jauge de noyau pleine / vide."""
    np = _np()
    a = np.asarray(recadrer(image, zone).convert("L"), dtype=float)
    return float((a >= seuil).mean())


def vignette(image, zone, taille=16):
    np = _np()
    return np.asarray(recadrer(image, zone).convert("L").resize((taille, taille)), dtype=float)


def format_16_9(taille, tolerance=0.02):
    return bool(taille) and taille[1] > 0 and abs(taille[0] / taille[1] - 16 / 9) <= tolerance


# --- détection -----------------------------------------------------------------------------------------------------------

def etats_bouton(serie, cfg):
    """`serie` = [(t, luminance)] d'un bouton -> [(t, "pret" | "recharge")]. Référence = 90e centile de la série (bouton prêt) ; « en
    recharge » sous `pret_ratio` × référence. Un bouton dont la luminance ne varie pas (écart < `variation_min`) est toujours prêt."""
    np = _np()
    if not serie:
        return []
    valeurs = np.array([v for _, v in serie])
    ref = float(np.percentile(valeurs, 90))
    if ref <= 0 or (valeurs.max() - valeurs.min()) / max(ref, 1e-9) < cfg.get("variation_min", 0.2):
        return [(t, "pret") for t, _ in serie]
    seuil = cfg.get("pret_ratio", 0.6) * ref
    return [(t, "pret" if v >= seuil else "recharge") for t, v in serie]


def transitions_recharge(etats, confirmation=2):
    """Temps (1re image en recharge) des passages « prêt » -> « en recharge », confirmés sur `confirmation` images de suite."""
    sortie, prec = [], "pret"
    for i, (t, e) in enumerate(etats):
        if prec == "pret" and e == "recharge" and all(x[1] == "recharge" for x in etats[i:i + confirmation]) and len(etats[i:i + confirmation]) == confirmation:
            sortie.append(t)
        prec = e
    return sortie


def transitions_jauge(serie, cfg):
    """`serie` = [(t, remplissage)] : instants où la jauge de noyau se vide (pleine -> vide en moins de `jauge_duree_s`)."""
    haut, bas, duree = cfg.get("jauge_pleine", 0.6), cfg.get("jauge_vide", 0.2), cfg.get("jauge_duree_s", 0.3)
    sortie, dernier_haut = [], None
    for t, v in serie:
        if v >= haut:
            dernier_haut = t
        elif v <= bas and dernier_haut is not None and t - dernier_haut <= duree + 1e-9:
            sortie.append(t)
            dernier_haut = None
        elif v <= bas:
            dernier_haut = None
    return sortie


def changements_portrait(vignettes, cfg):
    """`vignettes` = [(t, tableau)] du portrait actif -> temps où il change (écart moyen entre deux images > `portrait_diff`) ; un changement
    n'est compté qu'une fois par `fusion_s`."""
    np = _np()
    sortie, prec, dernier = [], None, -1e9
    for t, v in vignettes:
        if prec is not None and float(np.abs(v - prec).mean()) > cfg.get("portrait_diff", 25) and t - dernier >= cfg.get("fusion_s", 0.5):
            sortie.append(t)
            dernier = t
        prec = v
    return sortie


# --- détection par le chiffre de recharge (v3) --------------------------------------------------------------------------

def hud_present(vignettes, seuil=0.4):
    """`vignettes` = [(t, tableau)] d'un bouton qui ne change jamais (esquive, zone `ancre`) -> {t: bool} : le HUD est affiché quand la vignette
    ressemble (corrélation ≥ `seuil`) à la vignette médiane de la série (le HUD est affiché la plupart du temps). Cinématiques d'ultime,
    écrans noirs et Results : faux. Mesuré sur wJ9CwjKwyco : HUD ≥ 0,85 (≥ 0,5 si le bouton porte un chiffre), sans HUD ≤ 0,23."""
    np = _np()
    if not vignettes:
        return {}
    mediane = np.median(np.array([v.ravel() for _, v in vignettes]), axis=0)

    def corr(a, b):
        a, b = a - a.mean(), b - b.mean()
        d = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(a @ b) / d if d > 0 else 0.0
    return {t: corr(v.ravel(), mediane) >= seuil for t, v in vignettes}


def etats_par_chiffres(lectures, pret_min=2):
    """`lectures` = [(t, valeur | None | "hors")] d'un bouton (valeur = chiffre de recharge lu, None = aucun chiffre, "hors" = HUD absent) ->
    [(t, "pret" | "recharge")] sans les images « hors ». Un « prêt » isolé (moins de `pret_min` images sans chiffre de suite) dans une recharge
    est un chiffre mal lu : il reste « recharge »."""
    lues = [(t, v) for t, v in lectures if v != "hors"]
    etats = [(t, "pret" if v is None else "recharge") for t, v in lues]
    i = 0
    while i < len(etats):
        if etats[i][1] == "pret":
            j = i
            while j < len(etats) and etats[j][1] == "pret":
                j += 1
            if 0 < i and j < len(etats) and j - i < pret_min:
                etats[i:j] = [(t, "recharge") for t, _ in etats[i:j]]
            i = j
        else:
            i += 1
    return etats


def lecture_chiffres(frames, zone, ocr, presents, pas_s=0.5, maxi=99):
    """Une lecture du chiffre de recharge toutes les `pas_s` s : [(t, valeur | None | "hors")]. Valeur hors 0-`maxi` = None."""
    sortie, dernier = [], None
    for t, im in frames:
        if dernier is not None and t - dernier < pas_s - 1e-6:
            continue
        dernier = t
        if presents and not presents.get(t, True):
            sortie.append((t, "hors"))
            continue
        v = lire_recharge(ocr(recadrer(im, zone)))
        sortie.append((t, v if v is not None and 0 <= v <= maxi else None))
    return sortie


def lectures_ocr(recadrages, boutons, ocr, presents, brut=None):
    """`recadrages` = [(t, {zone: image PIL recadrée})] (1080p, toutes les `ocr_pas_s` s) -> {bouton: [(t, valeur | None | "hors")]}. `brut` (liste,
    optionnelle) reçoit (bouton, t, texte OCR) pour la calibration."""
    sortie = {b: [] for b in boutons}
    for t, zs in recadrages:
        for b in boutons:
            if presents and not presents.get(t, True):
                sortie[b].append((t, "hors"))
                continue
            texte = ocr(zs[b])
            if brut is not None:
                brut.append((b, t, texte))
            v = lire_recharge(texte)
            sortie[b].append((t, v if v is not None and 0 <= v <= 99 else None))
    return sortie


def purger_constantes(lectures, maxi=3):
    """Un chiffre identique sur plus de `maxi` lectures de suite n'est pas un compte à rebours (il change chaque seconde) mais une partie de l'icône
    lue comme un chiffre (wJ9CwjKwyco : l'icône de E lue « 4 » sur 20 s de suite) : ces lectures deviennent None."""
    sortie, i = list(lectures), 0
    while i < len(sortie):
        v = sortie[i][1]
        j = i
        while j < len(sortie) and sortie[j][1] == v:
            j += 1
        if v not in (None, "hors") and j - i > maxi:
            sortie[i:j] = [(t, None) for t, _ in sortie[i:j]]
        i = max(j, i + 1)
    return sortie


def _suite_de_recharge(lectures, t, lu):
    """Vrai si la recharge qui commence en `t` (chiffre `lu`) n'est que la suite de la précédente : chiffres manqués par l'OCR pendant
    quelques secondes, le compteur est plus bas qu'avant et le temps affiché écoulé (images sans HUD exclues : le chrono de jeu s'arrête)
    ne dépasse pas ce qu'il restait (+ 1,5 s)."""
    if lu is None:
        return False
    avant = [(i, v) for i, (tt, v) in enumerate(lectures) if tt < t and v not in (None, "hors")]
    if not avant:
        return False
    i0, v0 = avant[-1]
    i1 = next(i for i, (tt, _) in enumerate(lectures) if tt >= t)
    pas = (lectures[1][0] - lectures[0][0]) if len(lectures) > 1 else 0.5
    ecoule = sum(1 for _, v in lectures[i0 + 1:i1] if v != "hors") * pas
    return lu < v0 and ecoule <= v0 + 1.5


def transitions_chiffres(lectures, confirmation=2):
    """Instants (1re image avec chiffre) où un bouton passe de « prêt » à « en recharge », avec la recharge lue (médiane des 3 premières lectures de
    la recharge : un chiffre mal lu au début ne la fausse pas). Un bouton déjà en recharge à la 1re image n'a pas d'instant de lancement connu :
    aucun événement. -> [(t, valeur)]"""
    lectures = purger_constantes(lectures)
    etats = etats_par_chiffres(lectures)
    val = [(t, v) for t, v in lectures if v not in (None, "hors")]
    if not etats:
        return []
    sortie, prec = [], etats[0][1]
    for i, (t, e) in enumerate(etats):
        if i and prec == "pret" and e == "recharge" and all(x[1] == "recharge" for x in etats[i:i + confirmation]) and len(etats[i:i + confirmation]) == confirmation:
            premiers = [v for tt, v in val if tt >= t][:3]
            lu = sorted(premiers)[len(premiers) // 2] if premiers else None
            if not _suite_de_recharge(lectures, t, lu):
                sortie.append((t, lu))
        prec = e
    return sortie


def fusionner_doublons(evenements, ecart=0.5):
    """Deux détections du MÊME bouton (`slot`) à moins de `ecart` s = un seul événement (le plus tôt)."""
    gardes, dernier = [], {}
    for e in sorted(evenements, key=lambda e: e["t"]):
        if e["slot"] in dernier and e["t"] - dernier[e["slot"]] < ecart:
            continue
        dernier[e["slot"]] = e["t"]
        gardes.append(e)
    return gardes


def lire_recharge(texte):
    """Chiffre de recharge lu par l'OCR (`7.3`, `12`, `0:08`) -> secondes, ou None."""
    import re
    m = re.search(r"(\d{1,2})[.,](\d)\b", texte or "") or re.search(r"\b(\d{1,3})\b", texte or "")
    if not m:
        return None
    return float(f"{m.group(1)}.{m.group(2)}") if m.lastindex == 2 else float(m.group(1))


def preparer_chiffre(image, seuil=170, boite=(0.12, 0.22, 0.88, 0.78), hauteur=90):
    """Chiffre de recharge d'un bouton -> image noir sur blanc pour tesseract : centre de l'hexagone, min(R, V, B) (les chiffres sont blancs)
    agrandi à `hauteur` px (bicubique) puis seuillé à `seuil`, marge blanche. Essai tesseract 5 sur des chiffres 0-18, 60 (police grasse 16 px) :
    hauteur 90 + psm 7 = 15/15 lus ; 60 ou 40 px, psm 8 ou 13 : des chiffres manqués. L'image entière en gris ne lisait presque rien."""
    import numpy as np
    from PIL import Image, ImageOps
    w, h = image.size
    c = image.convert("RGB").crop((round(boite[0] * w), round(boite[1] * h), round(boite[2] * w), round(boite[3] * h)))
    g = Image.fromarray(np.asarray(c).astype(int).min(axis=2).astype("uint8"))
    g = g.resize((max(1, round(g.width * hauteur / max(1, g.height))), hauteur), Image.BICUBIC)
    return ImageOps.expand(Image.fromarray(np.where(np.asarray(g) >= seuil, 0, 255).astype("uint8")), border=30, fill=255)


def ocr_recharge(outils, tmp, seuil=170):
    """`ocr(image PIL) -> texte` pour `releves_run` : chiffre de recharge d'un bouton (`preparer_chiffre`, tesseract, chiffres seulement, un mot).
    `outils.ocr` = `pc.Outils.ocr`. Ne lève jamais : texte vide si l'OCR échoue (cooldown_read reste null)."""
    from pathlib import Path
    compteur = [0]

    def ocr(image):
        try:
            compteur[0] += 1
            png = Path(tmp) / f"_recharge_{compteur[0]}.png"
            preparer_chiffre(image, seuil).save(png)
            try:
                return outils.ocr(png, langues="eng", psm=7, timeout=30, extra=["-c", "tessedit_char_whitelist=0123456789."])
            finally:
                png.unlink(missing_ok=True)
        except Exception:
            return ""
    return ocr


# --- identité et confiance -----------------------------------------------------------------------------------------------

def recharge_base(db, hunter, slot, skill_id=None):
    """Recharge (s) de la base : `sjw_skills.json` pour les boutons de SJW (par `skill_id`), `hunters.json` pour un chasseur identifié ; None sinon."""
    if slot.startswith("sjw_"):
        return ((db.get("sjw_skills") or {}).get(skill_id) or {}).get("cooldown") if skill_id else None
    h = (db.get("hunters") or {}).get(hunter)
    for s in (h or {}).get("skills") or []:
        if s.get("type") == TYPE_BASE.get(slot):
            return s.get("cooldown")
    return None


def evaluer_confiance(evenements, db, tolerance=1.0):
    """SPEC §2.5 : `sur` si `cooldown_read` = recharge de la base ± `tolerance` s, ou si le perso est identifié, la recharge connue et l'ordre la
    respecte (même bouton jamais relancé avant la fin de la recharge) ; sinon `a_verifier` (les recharges réduites par des effets : jamais une erreur
    de lecture en soi). Modifie et retourne les événements."""
    derniers = {}
    for e in sorted(evenements, key=lambda e: e["t"]):
        base = recharge_base(db, e["hunter"], e["slot"], e.get("skill_id"))
        cle = (e["hunter"], e["slot"])
        respecte = base is None or cle not in derniers or e["t"] - derniers[cle] >= base - tolerance
        if e["slot"] in ("core", "tag") or base is None:
            e["confidence"] = "a_verifier"
        elif e.get("cooldown_read") is not None:
            e["confidence"] = "sur" if abs(e["cooldown_read"] - base) <= tolerance else "a_verifier"
        else:
            e["confidence"] = "sur" if e["hunter"] not in ("inconnu", None) and respecte else "a_verifier"
        if not respecte:
            e["confidence"] = "a_verifier"
        derniers[cle] = e["t"]
    return evenements


def identifier_portrait(image, cartes, cfg):
    """Id du chasseur dont la carte de référence (`portraits.correspondances`, SIFT) correspond au portrait ; `inconnu` sans carte ou ambiguïté."""
    if not cartes:
        return "inconnu"
    import portraits as P
    notes = {k: P.correspondances(image, ref) for k, ref in cartes.items()}
    ordre = sorted(notes, key=lambda k: -notes[k])
    meilleur, second = notes[ordre[0]], (notes[ordre[1]] if len(ordre) > 1 else 0)
    mini = (cfg.get("portraits") or {}).get("min_corr", 25)
    return ordre[0] if meilleur >= mini and meilleur >= 2 * max(second, 1) else "inconnu"


# --- une run -------------------------------------------------------------------------------------------------------------

def releves_run(frames, zones, cfg, db=None, cartes=None, skills_sjw=None, ocr=None, t_debut=0.0, lectures=None):
    """`frames` = [(t, image PIL)] entre les bornes ; `zones` = {bouton: [x0,y0,x1,y1], "core": …, "portrait": …, "qte": …}. Retourne la liste des
    événements (sans `t_run` : ajouté par `construire_run`) et les limites. `skills_sjw` = {bouton SJW: skill_id} (build). `ocr(image) -> texte`
    optionnel pour `cooldown_read`."""
    db, evenements, limites = db or {}, [], []
    if not frames:
        return [], ["bornes-incertaines"]
    presents = {}
    if zones.get("ancre"):
        presents = hud_present([(t, vignette(im, zones["ancre"])) for t, im in frames], cfg.get("ancre_corr", 0.4))
    # portrait actif : segments (début, id)
    actif = [(frames[0][0], "inconnu")]
    if zones.get("portrait"):
        vign = [(t, vignette(im, zones["portrait"])) for t, im in frames if presents.get(t, True)]
        coupes = [frames[0][0]] + changements_portrait(vign, cfg)
        par_t = dict(frames)
        actif = [(t, identifier_portrait(recadrer(par_t[t], zones["portrait"]), cartes, cfg)) for t in coupes]
        for t, ident in actif[1:]:
            banniere = bool(zones.get("qte")) and luminance(par_t[t], zones["qte"]) >= cfg.get("qte_luminance", 150)
            evenements.append({"t": t, "hunter": ident, "slot": "tag", "skill_id": None, "trigger": "qte" if banniere else "inconnu",
                               "cooldown_read": None, "source": "portrait"})
    else:
        limites.append("chasseurs-inconnus")

    def hunter_a(t):
        courant = actif[0][1]
        for t0, ident in actif:
            if t0 <= t:
                courant = ident
        return courant

    par_t = dict(frames)
    par_chiffres = cfg.get("detection") == "ocr" and ocr is not None
    for bouton in BOUTONS_HUNTER + BOUTONS_SJW:
        if not zones.get(bouton):
            continue
        sjw = bouton.startswith("sjw_")
        if lectures is not None or par_chiffres:
            lect = lectures.get(bouton, []) if lectures is not None else lecture_chiffres(frames, zones[bouton], ocr, presents, cfg.get("ocr_pas_s", 0.5))
            for t, lu in transitions_chiffres(lect):
                evenements.append({"t": t, "hunter": "sjw" if sjw else hunter_a(t), "slot": bouton,
                                   "skill_id": (skills_sjw or {}).get(bouton) if sjw else None, "trigger": None, "cooldown_read": lu, "source": "hud-recharge"})
            continue
        serie = [(t, luminance(im, zones[bouton])) for t, im in frames]
        for t in transitions_recharge(etats_bouton(serie, cfg)):
            lu = None
            if ocr:
                i = next((k for k, (tt, _) in enumerate(frames) if tt == t), None)
                lu = lire_recharge(ocr(recadrer(frames[min(i + 1, len(frames) - 1)][1], zones[bouton]))) if i is not None else None
            evenements.append({"t": t, "hunter": "sjw" if sjw else hunter_a(t), "slot": bouton,
                               "skill_id": (skills_sjw or {}).get(bouton) if sjw else None, "trigger": None, "cooldown_read": lu, "source": "hud-recharge"})
    if zones.get("core"):
        serie = [(t, remplissage(im, zones["core"], cfg.get("jauge_seuil_pixel", 128))) for t, im in frames]
        for t in transitions_jauge(serie, cfg):
            evenements.append({"t": t, "hunter": hunter_a(t), "slot": "core", "skill_id": None, "trigger": None, "cooldown_read": None, "source": "jauge"})
    evenements = fusionner_doublons(evenements, cfg.get("fusion_s", 0.5))
    if any(e["hunter"] == "inconnu" for e in evenements if e["slot"] in BOUTONS_HUNTER + ("core", "tag")) and "chasseurs-inconnus" not in limites:
        limites.append("chasseurs-inconnus")
    return evaluer_confiance(evenements, db, cfg.get("tolerance_recharge_s", 1.0)), limites


def construire_run(index, t_debut, t_fin, evenements, limites):
    """Objet `runs[i]` de la SPEC §3 : `t_run` = t − run_start_t ; trigger seulement pour `tag`."""
    sortie = []
    for e in sorted(evenements, key=lambda e: e["t"]):
        x = {"t": round(e["t"], 2), "t_run": round(e["t"] - t_debut, 2), "hunter": e["hunter"], "slot": e["slot"], "skill_id": e.get("skill_id"),
             "trigger": e.get("trigger") if e["slot"] == "tag" else None, "cooldown_read": e.get("cooldown_read"), "source": e["source"],
             "confidence": e.get("confidence", "a_verifier")}
        sortie.append(x)
    return {"run_index": index, "run_start_t": round(t_debut, 2) if t_debut is not None else None,
            "run_end_t": round(t_fin, 2) if t_fin is not None else None,
            "duration_s": round(t_fin - t_debut, 2) if t_debut is not None and t_fin is not None else None,
            "events": sortie, "limites": list(dict.fromkeys(limites))}


def fichier(ctx, runs):
    return {"spec": 1, "video_id": ctx["video_id"], "week": ctx["week"], "mode": ctx["mode"], "gate": ctx.get("gate"), "run_id": ctx.get("run_id"), "runs": runs}


# --- critères d'acceptation (SPEC §4, BOT) ---------------------------------------------------------------------------------

def controles_bot(fich, chrono_s=None, t_composition=None, phases=(), db=None, tolerance=1.0):
    """[(nom, ok | None, détail)] : durée = chrono ± 0,5 s, fin avant la composition, ≥ 1 événement SJW et 1 par chasseur actif, aucune recharge
    relancée trop tôt, phases du Results entre les bornes. `None` = non évaluable (donnée absente)."""
    db = db or {}
    r = (fich.get("runs") or [{}])[0]
    ev = r.get("events") or []
    sortie = []
    d = r.get("duration_s")
    sortie.append(("durée = chrono ± 0,5 s", None if d is None or chrono_s is None else abs(d - chrono_s) <= 0.5, f"durée {d} s, chrono {chrono_s} s" + ("" if d is None or chrono_s is None else f", écart {d - chrono_s:+.2f} s")))
    fin = r.get("run_end_t")
    sortie.append(("fin avant la composition", None if fin is None or t_composition is None else fin < t_composition, f"fin {fin} s, composition {t_composition} s"))
    sjw = any(e["hunter"] == "sjw" for e in ev)
    sortie.append(("≥ 1 événement SJW", sjw if ev else None, f"{sum(1 for e in ev if e['hunter'] == 'sjw')} événement(s)"))
    chasseurs = {e["hunter"] for e in ev if e["hunter"] not in ("sjw", "inconnu")}
    actifs = {e["hunter"] for e in ev if e["slot"] == "tag" and e["hunter"] != "sjw"}
    sortie.append(("≥ 1 événement par chasseur actif", None if not actifs else actifs <= chasseurs, f"actifs {sorted(actifs)}, avec événement {sorted(chasseurs)}"))
    trop_tot, derniers = [], {}
    for e in ev:
        base = recharge_base(db, e["hunter"], e["slot"], e.get("skill_id"))
        cle = (e["hunter"], e["slot"])
        if base is not None and cle in derniers and e["t"] - derniers[cle] < base - tolerance:
            trop_tot.append(f"{e['hunter']}/{e['slot']} à {e['t']} s")
        derniers[cle] = e["t"]
    sortie.append(("aucune recharge relancée trop tôt", (not trop_tot) if ev else None, "; ".join(trop_tot) or "ok"))
    ph = [p for p in phases if p is not None]
    debut = r.get("run_start_t")
    sortie.append(("phases du Results entre les bornes", None if not ph or debut is None or fin is None else all(debut <= debut + p <= fin + 0.5 for p in ph), f"phases {ph}"))
    return sortie


# --- rapport -------------------------------------------------------------------------------------------------------------

def rapport(semaine, racine=RACINE):
    """Texte de `data/rotations/<semaine>/_rapport.md` : une ligne par vidéo (événements, `a_verifier`, limites)."""
    dossier = Path(racine) / "data" / "rotations" / semaine
    lignes = [f"# Rapport des rotations — semaine {semaine}", ""]
    fichiers = sorted(dossier.glob("*/*.json")) if dossier.exists() else []
    f_ctrl = dossier / "_controles.json"
    controles = json.loads(f_ctrl.read_text(encoding="utf-8")) if f_ctrl.exists() else {}
    if not fichiers:
        lignes.append("Aucune rotation relevée.")
    for f in fichiers:
        d = json.loads(f.read_text(encoding="utf-8"))
        for r in d["runs"]:
            ev = r["events"]
            lignes.append(f"- {d['mode']} · {d['video_id']} · run {r['run_index']} : {len(ev)} événement(s), "
                          f"{sum(1 for e in ev if e['confidence'] != 'sur')} à vérifier, durée {r['duration_s']} s, limites : {', '.join(r['limites']) or 'aucune'}")
            for nom, ok, detail in controles.get(d["video_id"]) or []:
                lignes.append(f"  - {'OK' if ok else ('NON ÉVALUABLE' if ok is None else 'ÉCHEC')} : {nom} ({detail})")
    return "\n".join(lignes) + "\n"


def ecrire(ctx, fich, racine=RACINE, controles=None):
    """Écrit `<video_id>.json` (format de la SPEC §3, sans champ en plus), les contrôles d'acceptation dans `_controles.json` et le rapport de la
    semaine ; retourne le chemin."""
    dossier = Path(racine) / "data" / "rotations" / ctx["week"] / ctx["mode"]
    dossier.mkdir(parents=True, exist_ok=True)
    f_ctrl = dossier.parent / "_controles.json"
    if controles is not None:
        tous = json.loads(f_ctrl.read_text(encoding="utf-8")) if f_ctrl.exists() else {}
        tous[ctx["video_id"]] = controles
        f_ctrl.write_text(json.dumps(tous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chemin = dossier / f"{ctx['video_id']}.json"
    chemin.write_text(json.dumps(fich, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dossier.parent / "_rapport.md").write_text(rapport(ctx["week"], racine), encoding="utf-8")
    return chemin


# --- sélection et passage PC ---------------------------------------------------------------------------------------------

def selection(semaine, racine=RACINE, cfg=None, config_builds=None):
    """[(mode, ligne)] : top `top` (3) des modes de `cfg.modes` (BOT d'abord ; lignes provisoires acceptées), dans l'ordre du classement."""
    import builds
    cfg = cfg or charger_config()
    top = builds.modes_du_top(semaine, racine, config_builds or builds.charger_config())
    sortie = []
    for mode in cfg.get("modes", ["bot"]):
        sortie += [(mode, l) for n, l in top if (l.get("mode") or n.split("-")[0]) == mode][:cfg.get("top", 3)]
    return sortie


def a_traiter(semaine, processed, racine=RACINE, cfg=None, config_builds=None):
    """video_id à relever ce passage : sélection du top 3 par mode, sans `pc.rotation` (fait | absent | erreur) à la version courante,
    au plus `budget_par_mode` par mode (SPEC §1)."""
    cfg = cfg or charger_config()
    par_mode, sortie = {}, []
    for mode, ligne in selection(semaine, racine, cfg, config_builds):
        vid = ligne.get("video_id")
        p = (processed.get(vid) or {}).get("pc") or {}
        deja = p.get("rotation") in ("fait", "absent", "erreur") and p.get("rotation_version", 0) >= cfg.get("version", 1)
        if vid and not deja and par_mode.get(mode, 0) < cfg.get("budget_par_mode", 3) and vid not in sortie:
            par_mode[mode] = par_mode.get(mode, 0) + 1
            sortie.append(vid)
    return sortie


def contexte(semaine, vid, racine=RACINE, cfg=None, config_builds=None):
    """Contexte d'une vidéo de la sélection : mode, gate, run_id, ligne, t (Results lu au tri 3-4 si connu), chrono (BOT)."""
    for mode, ligne in selection(semaine, racine, cfg, config_builds):
        if ligne.get("video_id") == vid:
            d = (ligne.get("runs_detail") or [{}])[0]
            ctx = {"video_id": vid, "week": semaine, "mode": mode, "gate": ligne.get("gate"), "run_id": ligne.get("run_id"),
                   "ligne": ligne, "t_result": d.get("t"), "chrono_s": ligne["score"]["total"] if mode == "bot" else None}
            b = Path(racine) / "data" / "builds" / semaine / (ligne.get("dossier") or mode) / f"{ligne.get('run_id')}-1.json"
            if b.exists():          # début de l'écran de composition (le build provisoire) : la run se termine avant
                bj = json.loads(b.read_text(encoding="utf-8"))
                tc = bj.get("t_composition")
                ctx["t_composition"] = tc[0] if tc else None
                par_slot = {x.get("slot"): x.get("id") for x in ((bj.get("sjw") or {}).get("skills") or [])}
                ctx["skills_sjw"] = {"sjw_skill_1": par_slot.get("skill_1"), "sjw_skill_2": par_slot.get("skill_2"),
                                     "sjw_ultimate": par_slot.get("ultimate"), "sjw_qte": par_slot.get("qte_1")}       # id de la compétence (build)
            lec = Path(racine) / "data" / "runs" / semaine / "_lectures.json"
            if lec.exists():
                for l in json.loads(lec.read_text(encoding="utf-8")):
                    if l.get("video_id") == vid and l.get("mode") == "bot" and (l.get("detail") or {}).get("phases"):
                        ctx["phases"] = [p for p in l["detail"]["phases"] if isinstance(p, (int, float))]
                        break
            return ctx
    return None


def diagnostic_crops(ctx, frames, cfg, racine=RACINE):
    """Zones du HUD non calibrées : quelques recadrages de GRANDES zones (jamais l'image entière, SPEC §2.7) pour la calibration, dans
    `data/rotations/<semaine>/<mode>/_crops/`. Retourne les chemins écrits."""
    d = cfg.get("diagnostic") or {}
    if not frames or not d.get("zones"):
        return []
    dossier = Path(racine) / "data" / "rotations" / ctx["week"] / ctx["mode"] / "_crops"
    dossier.mkdir(parents=True, exist_ok=True)
    pas = max(1, len(frames) // (d.get("images", 3) + 1))
    ecrits = []
    for k in range(1, d.get("images", 3) + 1):
        t, im = frames[min(k * pas, len(frames) - 1)]
        for nom, zone in d["zones"].items():
            c = recadrer(im.convert("RGB"), zone)
            c.thumbnail((d.get("largeur", 960), d.get("largeur", 960)))
            f = dossier / f"{ctx['video_id']}_{nom}_{int(t * 10):05d}.jpg"
            c.save(f, quality=85)
            ecrits.append(f)
    return ecrits


def planche_zones(ctx, images, zones, cfg, racine=RACINE, extra=None):
    """Calibration : une planche (lignes = boutons calibrés, colonnes = une image tous les `scan_pas_s`) des recadrages des SEULES zones de boutons
    (jamais l'image entière, SPEC §2.7) + les séries de luminance, dans `_crops/` du mode. Seulement si `cfg.planche` est vrai. Retourne le chemin."""
    if not cfg.get("planche") or not images:
        return None
    from PIL import Image, ImageDraw
    noms = [b for b in BOUTONS_HUNTER + BOUTONS_SJW + ("portrait", "ancre") if zones.get(b)]
    if not noms:
        return None
    ts = sorted(images)
    lc, hc = 46, 50
    feuille = Image.new("RGB", (lc * len(ts), 14 + hc * len(noms)), "black")
    dessin = ImageDraw.Draw(feuille)
    for j, t in enumerate(ts):
        if abs(t - round(t)) < 1e-6 and int(round(t)) % 2 == 0:
            dessin.text((j * lc + 2, 1), f"{t:g}s", fill=(255, 255, 0))
        for i, nom in enumerate(noms):
            feuille.paste(recadrer(images[t].convert("RGB"), zones[nom]).resize((lc, hc)), (j * lc, 14 + i * hc))
    dossier = Path(racine) / "data" / "rotations" / ctx["week"] / ctx["mode"] / "_crops"
    dossier.mkdir(parents=True, exist_ok=True)
    f = dossier / f"{ctx['video_id']}_planche.jpg"
    feuille.convert("RGB").save(f, quality=80)
    (dossier / f"{ctx['video_id']}_series.json").write_text(json.dumps(
        {"pas_s": cfg.get("scan_pas_s", 0.5), "lignes": noms, "t": ts, "luminance": {n: [round(luminance(images[t], zones[n]), 1) for t in ts] for n in noms}},
        indent=0), encoding="utf-8")
    if extra:
        (dossier / f"{ctx['video_id']}_ocr.json").write_text(json.dumps(extra, ensure_ascii=False, indent=0), encoding="utf-8")
    return f


def passage_video(outils, chemin, ctx, cfg, db, tmp, journal=lambda m: None, ocr=None, cartes=None, racine=RACINE, duree_s=None, t_composition=None):
    """Relevé d'UNE vidéo déjà téléchargée. Retourne l'état de `pc.rotation` : `fait` | `absent` | `erreur`. Bornes : début = 1re image où un bouton de
    compétence est visible (balayage à `scan_pas_s`), fin = `ctx.t_result` (Results lu aux tris 3-4) sinon dernière image avec HUD (`bornes-incertaines`)."""
    zones = {k: v for k, v in (cfg.get("zones") or {}).items() if v}
    fin_max = min(ctx.get("t_result") or duree_s or 60, cfg.get("duree_max_s", 120))
    balayage = outils.images(chemin, [(0, fin_max, cfg.get("scan_pas_s", 0.5))], tmp, prefixe="rs", hauteur=cfg.get("hauteur", 720))
    from PIL import Image
    images = {t: Image.open(p).convert("RGB") for t, p in balayage}
    limites = []
    if images and not format_16_9(next(iter(images.values())).size):
        run = construire_run(1, None, None, [], ["format"])
        ecrire(ctx, fichier(ctx, [run]), racine)
        return "absent"
    if not any(zones.get(b) for b in BOUTONS_HUNTER + BOUTONS_SJW):
        diagnostic_crops(ctx, sorted(images.items()), cfg, racine)
        run = construire_run(1, None, None, [], ["hud-non-trouve"])
        ecrire(ctx, fichier(ctx, [run]), racine)
        journal("  rotation : HUD non calibré (config/rotation.json), recadrages de calibration gardés")
        return "absent"
    if zones.get("ancre"):
        pres = hud_present([(t, vignette(im, zones["ancre"])) for t, im in sorted(images.items())], cfg.get("ancre_corr", 0.4))
        visibles = [t for t in sorted(pres) if pres[t]]
    else:
        visibles = [t for t, im in sorted(images.items()) if any(luminance(im, zones[b]) >= cfg.get("visible_luminance", 30) for b in zones if b in BOUTONS_HUNTER + BOUTONS_SJW)]
    if not visibles:
        run = construire_run(1, None, None, [], ["hud-non-trouve"])
        ecrire(ctx, fichier(ctx, [run]), racine)
        return "absent"
    t_debut = visibles[0]
    if ctx.get("t_result"):
        t_fin = float(ctx["t_result"])
    else:
        t_fin = visibles[-1] + cfg.get("scan_pas_s", 0.5)
        limites.append("bornes-incertaines")
    pas = 1 / cfg.get("fps", 10)
    lectures, extra = None, None
    if cfg.get("detection") == "ocr" and ocr and cfg.get("hauteur_ocr"):
        boutons = [b for b in BOUTONS_HUNTER + BOUTONS_SJW if zones.get(b)]
        pas_ocr = cfg.get("ocr_pas_s", 0.5)
        recadrages = []
        for t, chemin_png in outils.images(chemin, [(t_debut, max(t_fin - t_debut, pas_ocr), pas_ocr)], tmp, prefixe="ro", hauteur=cfg["hauteur_ocr"]):
            with Image.open(chemin_png) as im:
                im = im.convert("RGB")
                recadrages.append((t, {n: recadrer(im, zones[n]).copy() for n in boutons + (["ancre"] if zones.get("ancre") else [])}))
        pres = hud_present([(t, vignette(zs["ancre"], [0, 0, 1, 1])) for t, zs in recadrages], cfg.get("ancre_corr", 0.4)) if zones.get("ancre") else {}
        brut = []
        lectures = lectures_ocr(recadrages, boutons, ocr, pres, brut)
        extra = {"hauteur": cfg["hauteur_ocr"], "hud": {str(t): bool(v) for t, v in pres.items()},
                 "brut": {b: [[t, x] for bb, t, x in brut if bb == b] for b in boutons}}
    planche_zones(ctx, images, zones, cfg, racine, extra)
    frames = [(t, Image.open(p).convert("RGB")) for t, p in outils.images(chemin, [(t_debut, max(t_fin - t_debut, pas), pas)], tmp, prefixe="rf", hauteur=cfg.get("hauteur", 720))]
    sjw = ctx.get("skills_sjw") or {}
    evenements, lim = releves_run(frames, zones, cfg, db, cartes, sjw, ocr, t_debut, lectures)
    run = construire_run(1, t_debut, t_fin, evenements, limites + lim)
    fich = fichier(ctx, [run])
    controles = [list(c) for c in controles_bot(fich, ctx.get("chrono_s"), t_composition if t_composition is not None else ctx.get("t_composition"),
                                                ctx.get("phases") or (), db, cfg.get("tolerance_recharge_s", 1.0))] if ctx["mode"] == "bot" else None
    ecrire(ctx, fich, racine, controles)
    return "fait"
