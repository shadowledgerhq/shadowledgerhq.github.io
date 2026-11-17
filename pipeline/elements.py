"""SPEC v30 §4.1 : élément d'une run GB / POC (Light, Fire, Water, Wind, Dark) et distinction des groupes / équipes.

Sources de l'élément d'une run, dans cet ordre (l'écran prime sur le titre) :
 1. chasseurs vus à l'écran : `detail.hunter_ids` (identifiants de `data/db/hunters.json` : (a) build `sûr` de l'étape 2 de la même run,
    sinon (b) portraits des 6 lignes « Hunter Rank » du Results, `hunters_results.py`) -> élément majoritaire ; sinon, sans identité,
    `detail.elements_hud` (couleur des losanges du HUD, `elements_hud.py`) -> élément strictement majoritaire (≥ 2 losanges, ≥ 2 images) ;
 2. titre qui cite UN seul élément, vidéo à UNE seule run filmée du mode ;
 3. titre qui cite 2 éléments, vidéo à 2 runs filmées : chaque élément du titre va à la run dont les chasseurs l'ont ; si une seule
    run est lue à l'écran (et son élément figure dans le titre), l'autre reçoit l'élément restant.
Écran et titre en contradiction : `_contradiction`, la ligne passe `a_verifier`."""
import json
import re
import unicodedata
from pathlib import Path

import elements_hud
from collections import Counter

ELEMENTS = ("light", "fire", "water", "wind", "dark")
FR = {"light": "Lumière", "fire": "Feu", "water": "Eau", "wind": "Vent", "dark": "Ténèbres"}
EN = {"light": "Light", "fire": "Fire", "water": "Water", "wind": "Wind", "dark": "Dark"}
SOURCES_TEXTE = ("titre", "description", "sous-titres")
NOTE_CONTRADICTION = "élément du titre contredit par l'écran"
_HANGUL = "가-힣"


def _sans_accents(t):
    sans = "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", sans).lower()          # NFC : les syllabes coréennes redeviennent un seul caractère


def _motif(mot):
    """v31 : un mot d'UN seul caractère (빛 불 물 光 火 水 風 闇) ne compte que isolé : bordé par un début / une fin de titre, une espace,
    une ponctuation ou un chiffre (`水篠旬`, `괴물`, `화상` : aucun élément ; `석상 불 160` : fire). Les mots plus longs (바람, 암흑, mots
    latins) gardent la règle précédente (mot latin entier ; sous-chaîne pour le CJK)."""
    m = _sans_accents(mot)
    if len(m) == 1 and not re.fullmatch(r"[a-z]", m):
        return rf"(?<![^\W\d_]){re.escape(m)}(?![^\W\d_])"       # isolé : pas de lettre (hangul, kana, kanji…) accolée ; chiffres et ponctuation permis
    if re.fullmatch(r"[a-z]+", m):
        return rf"(?<![a-z]){m}(?![a-z])"
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


def charger_builds(racine_data, week):
    """v31 (a) : builds de l'étape 2 de la semaine, `sûrs` : [(mode, video_id, t_result, [ids de chasseurs])]."""
    sortie = []
    for f in sorted((Path(racine_data) / "builds" / week).glob("*/*.json")):
        try:
            b = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ids = [h.get("id") for h in b.get("hunters") or [] if h.get("id")]
        if b.get("confidence") == "sur" and ids and b.get("status") != "pas_de_build":
            sortie.append((b.get("mode"), b.get("video_id"), b.get("t_result"), ids))
    return sortie


def ids_du_build(builds, r, delai=10):
    """Identifiants des chasseurs du build `sûr` de la même run (même vidéo et même mode ; `t_result` à `delai` s du `t` de la run, ou
    seul build de la vidéo pour une seule run) ; [] sinon."""
    memes = [b for b in builds or [] if b[0] == r["mode"] and b[1] == r["video_id"]]
    proches = [b for b in memes if b[2] is not None and r.get("t") is not None and abs(b[2] - r["t"]) <= delai]
    return (proches or (memes if len(memes) == 1 else [(None, None, None, [])]))[0][3]


def _filmee(r):
    return r.get("score_source") not in SOURCES_TEXTE and r.get("score_source") != "record"


def annoter(runs, titres, config, hunters, builds=None):
    """GB et POC : renseigne `element`, `element_source` (`ecran` | `titre` | `titre+ecran` | None) et `_contradiction` (+ note) sur
    les runs FILMÉES de chaque vidéo. `titres` : {video_id: titre} ; `builds` : `charger_builds`. Modifie `runs` en place.
    Priorité : `hunter_ids` (build sûr, sinon portraits du Results) > `elements_hud` > titre."""
    par_video = {}
    for r in runs:
        r.setdefault("element", None)
        r.setdefault("element_source", None)
        if r["mode"] in ("gb", "poc") and _filmee(r):
            par_video.setdefault(r["video_id"], []).append(r)
    for vid, rs in par_video.items():
        tit = elements_du_titre(titres.get(vid, ""), config)
        for r in rs:
            ids = ids_du_build(builds, r) or (r.get("detail") or {}).get("hunter_ids")
            if ids:
                r["detail"] = {**(r.get("detail") or {}), "hunter_ids": list(ids)}
            el = element_majoritaire(ids, hunters) or elements_hud.element_de_la_run((r.get("detail") or {}).get("elements_hud_images") or [])
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
