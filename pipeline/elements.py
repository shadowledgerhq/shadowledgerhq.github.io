"""SPEC v30 §4.1 : élément d'une run GB / POC (Light, Fire, Water, Wind, Dark) et distinction des groupes / équipes.

Sources de l'élément d'une run, dans cet ordre (l'écran prime sur le titre) :
 1. chasseurs vus à l'écran : `detail.hunter_ids` (identifiants de `data/db/hunters.json`, lus par l'étape 2 ; [À VÉRIFIER] pas encore
    alimenté de façon fiable) -> élément majoritaire ;
 2. titre qui cite UN seul élément, vidéo à UNE seule run filmée du mode ;
 3. titre qui cite 2 éléments, vidéo à 2 runs filmées : chaque élément du titre va à la run dont les chasseurs l'ont ; si une seule
    run est lue à l'écran (et son élément figure dans le titre), l'autre reçoit l'élément restant.
Écran et titre en contradiction : `_contradiction`, la ligne passe `a_verifier`."""
import re
import unicodedata
from collections import Counter

ELEMENTS = ("light", "fire", "water", "wind", "dark")
FR = {"light": "Lumière", "fire": "Feu", "water": "Eau", "wind": "Vent", "dark": "Ténèbres"}
EN = {"light": "Light", "fire": "Fire", "water": "Water", "wind": "Wind", "dark": "Dark"}
SOURCES_TEXTE = ("titre", "description", "sous-titres")
NOTE_CONTRADICTION = "élément du titre contredit par l'écran"
_HANGUL = "가-힣"
_PARTICULES = "속성|속|을|를|이|가|의|은|는|로|으로|에|과|와"


def _sans_accents(t):
    sans = "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", sans).lower()          # NFC : les syllabes coréennes redeviennent un seul caractère


def _motif(mot):
    m = _sans_accents(mot)
    if re.fullmatch(r"[a-z]+", m):
        return rf"(?<![a-z]){m}(?![a-z])"
    if re.search(f"[{_HANGUL}]", m) and len(m) == 1:      # une syllabe (불, 물, 빛) : seule ou suivie d'une particule courante
        return rf"(?<![{_HANGUL}]){m}(?:{_PARTICULES})?(?![{_HANGUL}])"
    return re.escape(m)


def elements_du_titre(titre, config):
    """Éléments cités par le titre, dans l'ordre d'apparition (sans doublon). Mots : `config.elements_titre` (sans accents ni casse)."""
    t = _sans_accents(titre)
    trouves = []
    for el, mots in ((config or {}).get("elements_titre") or {}).items():
        if el.startswith("_"):
            continue
        pos = [m.start() for mot in mots for m in re.finditer(_motif(mot), t)]
        if pos:
            trouves.append((min(pos), el))
    return [el for _, el in sorted(trouves)]


def element_majoritaire(ids, hunters):
    """Élément le plus fréquent parmi les chasseurs vus (`hunters` : {id: élément}) ; égalité ou rien -> None."""
    c = Counter(hunters.get(i) for i in (ids or []) if hunters.get(i))
    if not c:
        return None
    (el, n), *reste = c.most_common()
    return el if not reste or reste[0][1] < n else None


def _filmee(r):
    return r.get("score_source") not in SOURCES_TEXTE and r.get("score_source") != "record"


def annoter(runs, titres, config, hunters):
    """GB et POC : renseigne `element`, `element_source` (`ecran` | `titre` | `titre+ecran` | None) et `_contradiction` (+ note) sur
    les runs FILMÉES de chaque vidéo. `titres` : {video_id: titre}. Modifie `runs` en place."""
    par_video = {}
    for r in runs:
        r.setdefault("element", None)
        r.setdefault("element_source", None)
        if r["mode"] in ("gb", "poc") and _filmee(r):
            par_video.setdefault(r["video_id"], []).append(r)
    for vid, rs in par_video.items():
        tit = elements_du_titre(titres.get(vid, ""), config)
        for r in rs:
            el = element_majoritaire((r.get("detail") or {}).get("hunter_ids"), hunters)
            if el:
                r["element"], r["element_source"] = el, "ecran"
                if tit and el not in tit:
                    r["_contradiction"] = True
                    if NOTE_CONTRADICTION not in r["notes"]:
                        r["notes"].append(NOTE_CONTRADICTION)
                elif tit:
                    r["element_source"] = "titre+ecran"
        libres = [r for r in rs if r["element"] is None]
        if len(tit) == 1 and len(rs) == 1 and libres:
            libres[0]["element"], libres[0]["element_source"] = tit[0], "titre"
        elif len(tit) == 2 and len(rs) == 2 and len(libres) == 1:
            connu = next(r["element"] for r in rs if r is not libres[0])
            if connu in tit:
                libres[0]["element"] = next(e for e in tit if e != connu)
                libres[0]["element_source"] = "titre+ecran"


def hunters_de(r):
    return set((r.get("detail") or {}).get("hunter_ids") or [])


def distinctes(a, b):
    """Deux runs d'un même joueur sont-elles de groupes / équipes différents ? `oui`, `non` ou `peut` (une équipe connue, l'autre non :
    additionnées mais ligne `a_verifier`, comportement v18 inchangé). Un chasseur commun vu à l'écran = même groupe, sans exception."""
    ha, hb = hunters_de(a), hunters_de(b)
    if ha & hb:
        return "non"
    ta, tb = a.get("team"), b.get("team")
    if ta in (1, 2) and tb in (1, 2):
        return "oui" if ta != tb else "non"
    ea, eb = a.get("element"), b.get("element")
    if ea and eb:
        return "oui" if ea != eb else "non"
    if (ta in (1, 2)) != (tb in (1, 2)):
        return "peut"
    return "non"


def note_distinction(a, b):
    """Note de ligne quand deux runs sont distinguées par l'élément (pas par le numéro d'équipe lu), sinon None."""
    if a.get("team") in (1, 2) and b.get("team") in (1, 2):
        return None
    sources = {a.get("element_source"), b.get("element_source")}
    if sources == {"ecran"}:
        return "groupes distingués par les chasseurs"
    if sources == {"titre"}:
        return f"groupes distingués par le titre ({EN[a['element']]} / {EN[b['element']]})"
    if None in sources:
        return None
    return "élément associé titre + chasseurs"
