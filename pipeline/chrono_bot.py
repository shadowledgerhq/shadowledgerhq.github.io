"""SPEC_ETAPE1 v34 §4.1 : chronos BOT incomplets (sans millièmes) et lectures de plusieurs sources de la même vidéo.

Une lecture de chrono sans millisecondes (`19s`, `19초`, `Play Time 00:19`) vaut l'intervalle [N ; N + 0,999] ; au dixième (`19.9`)
[19,900 ; 19,999] ; au centième [19,92 ; 19,929]. Pour une vidéo dont les seules lectures sont provisoires (titre, description, sous-titres,
miniature) :
  (a) une lecture plus précise d'une AUTRE source, compatible (dans l'intervalle, ou partie entière N − 1 : le texte a pu arrondir),
      remplace la lecture incomplète ; note `titre arrondi : 19s` ;
  (b) sans lecture plus précise, la ligne est triée à la borne haute de l'intervalle (rang prudent), note `chrono incomplet : rang
      prudent` ; le score affiché reste celui qui a été lu (clé de tri dans `_tri`) ;
  (c) une lecture précise incompatible (hors de l'intervalle, ou deux lectures précises qui diffèrent d'au moins 1 s) : `a_verifier`, note
      `titre/miniature en désaccord` (noms des deux sources).
(v34.1, décision d'Alexis) Un chrono BOT lu dans un texte qui finit par `00` (`19.900`, `40.000`) est un arrondi : traité comme une lecture
au dixième ([19,900 ; 19,999]), note `chrono fini par 00 : arrondi probable, à vérifier dans la vidéo`. Ne vaut pas pour un écran Results.
Fonctions pures, testées (`tests/test_v34.py`)."""
import re
import scores

SOURCES = ("titre", "description", "sous-titres", "miniature")
PRIORITE = {s: i for i, s in enumerate(SOURCES)}
NOTE_RANG_PRUDENT = "chrono incomplet : rang prudent"
NOTE_00 = "chrono fini par 00 : arrondi probable, à vérifier dans la vidéo"
ARRONDI = {"titre": "titre arrondi", "description": "description arrondie", "sous-titres": "sous-titres arrondis",
           "miniature": "miniature arrondie"}
_RE_SCORE = re.compile(r"^score provisoire \((titre|description|sous-titres|miniature)\) : (.+)$")
_RE_AUTRE = re.compile(r"^(titre|description|sous-titres|miniature) : (.+)$")


def bornes(valeur, decimales):
    """(bas, haut) de l'intervalle d'une lecture à `decimales` chiffres après la virgule (0 à 3)."""
    d = max(0, min(3, int(decimales)))
    return round(valeur, 3), round(valeur + (10 ** -d - 0.001 if d < 3 else 0.0), 3)


def _lecture_brut(source, brut, plage=None):
    """{source, brut, valeur, lo, hi, precis} d'un texte brut (`19s`, `19.926`), ou None si ce n'est pas un chrono plausible."""
    for c in scores.chronos(brut or ""):
        if plage and not plage[0] <= c["valeur"] <= plage[1]:
            continue
        arrondi00 = c["decimales"] == 3 and round(c["valeur"] * 1000) % 100 == 0       # v34.1 : `19.900`, `40.000` = arrondi au dixième
        lo, hi = bornes(c["valeur"], 1 if arrondi00 else c["decimales"])
        return {"source": source, "brut": c["brut"], "valeur": c["valeur"], "lo": lo, "hi": hi, "precis": lo == hi, "arrondi00": arrondi00}
    return None


def lectures_de_la_run(r, plage=None):
    """Toutes les lectures de chrono portées par une run provisoire : sa lecture principale (`score_source` + note `score provisoire (…)`),
    et les autres sources notées (`description : 19.926`, `sous-titres : …`, `miniature : …`). Les écarts de lecture d'écran ne sont pas lus."""
    sortie = []
    for n in r.get("notes", []):
        m = _RE_SCORE.match(n)
        if m:
            lec = _lecture_brut(m.group(1), m.group(2), plage)
            if lec:
                sortie.append({**lec, "principale": True})
            continue
        m = _RE_AUTRE.match(n)
        if m:
            lec = _lecture_brut(m.group(1), m.group(2), plage)
            if lec:
                sortie.append(lec)
    if not any(x.get("principale") for x in sortie) and r.get("score") is not None and r.get("score_source") in SOURCES:
        sortie.insert(0, {"source": r["score_source"], "brut": str(r["score"]), "valeur": r["score"], "lo": r["score"],
                          "hi": r["score"], "precis": True, "principale": True})
    return sortie


def compatible(incomplete, precise):
    """La lecture précise est-elle compatible avec l'intervalle de la lecture incomplète ? Dans l'intervalle, ou partie entière N − 1
    (texte arrondi vers le haut : `20s` pour 19,926)."""
    v = precise["valeur"]
    return incomplete["lo"] <= v <= incomplete["hi"] or incomplete["lo"] - 1 <= v < incomplete["lo"]


def _prime(lecture):
    return PRIORITE.get(lecture["source"], 9)


def reconcilier_video(runs):
    """`runs` : les runs BOT PROVISOIRES (lecture de texte, `t` absent) d'UNE même vidéo. Retourne (run retenue, [runs écartées]).
    La run retenue (copie de la principale) porte `_tri` (clé de tri) et les notes de la v34 ; `score` / `score_source` sont ceux qui ont
    été lus (ou ceux de la lecture précise qui remplace une lecture arrondie)."""
    runs = sorted(runs, key=lambda r: PRIORITE.get(r.get("score_source"), 9))
    base = runs[0]
    lectures = []
    for r in runs:
        for x in lectures_de_la_run(r):
            if not any(y["source"] == x["source"] and y["valeur"] == x["valeur"] for y in lectures):
                lectures.append(x)
    lectures.sort(key=_prime)
    out = {**base, "notes": list(base["notes"])}
    ecartees = runs[1:]
    principale = next((x for x in lectures if x["source"] == base.get("score_source") and x["valeur"] == base["score"]), None)
    if principale is None:
        return out, ecartees
    precises = [x for x in lectures if x["precis"] and x is not principale]
    if principale["precis"]:
        for x in precises:                                            # (c) deux lectures précises différentes
            if abs(x["valeur"] - principale["valeur"]) >= 1:
                _noter(out, f"{principale['source']}/{x['source']} en désaccord")
                break
        return out, ecartees
    # lecture principale incomplète
    ok = [x for x in precises if compatible(principale, x)]
    if ok:                                                            # (a) remplacée par la lecture précise compatible
        x = ok[0]
        out["score"], out["score_source"] = x["valeur"], x["source"]
        out["notes"] = [n for n in out["notes"] if not _RE_SCORE.match(n) or n.startswith(f"score provisoire ({x['source']})")]
        if not any(_RE_SCORE.match(n) for n in out["notes"]):
            out["notes"].insert(0, f"score provisoire ({x['source']}) : {x['brut']}")
        _noter(out, f"{ARRONDI.get(principale['source'], 'lecture arrondie')} : {principale['brut']}")
        out["notes"] = [n for n in out["notes"] if n != f"{x['source']} : {x['brut']}"]
        out.pop("_tri", None)
        for y in precises:
            if y is not x and not compatible(principale, y) and abs(y["valeur"] - x["valeur"]) >= 1:
                _noter(out, f"{x['source']}/{y['source']} en désaccord")
                break
        return out, ecartees
    if precises:                                                      # (c) précise incompatible
        _noter(out, f"{principale['source']}/{precises[0]['source']} en désaccord")
    out["_tri"] = principale["hi"]                                    # (b) rang prudent
    _noter(out, NOTE_RANG_PRUDENT)
    if principale.get("arrondi00"):
        _noter(out, NOTE_00)
    return out, ecartees


def _noter(run, note):
    if note not in run["notes"]:
        run["notes"].append(note)


def est_provisoire_texte(r):
    """Run issue d'un texte (titre, description, sous-titres, miniature lue comme texte) et non d'une image de la vidéo."""
    return r.get("score_source") in SOURCES and r.get("t") is None and r.get("exact") is False and not (r.get("detail") or {}).get("ecran")


def reconcilier(runs):
    """Applique `reconcilier_video` à chaque vidéo BOT à lectures provisoires ; retourne la nouvelle liste de runs (ordre conservé).
    Les runs d'écran (`debut-fin`, `video-complete`) ne sont jamais touchées. Une run `exact` ou `sûre` n'a pas de clé `_tri`."""
    par_video = {}
    for r in runs:
        if r.get("mode") == "bot" and est_provisoire_texte(r):
            par_video.setdefault(r["video_id"], []).append(r)
    if not par_video:
        return runs
    remplace, retire = {}, set()
    for vid, groupe in par_video.items():
        retenue, ecartees = reconcilier_video(groupe)
        remplace[id(_premiere(groupe))] = retenue
        retire |= {id(x) for x in ecartees}
    sortie = []
    for r in runs:
        if id(r) in retire:
            continue
        sortie.append(remplace.get(id(r), r))
    return sortie


def _premiere(groupe):
    """La run de priorité la plus haute du groupe (celle qui sert de base à `reconcilier_video`)."""
    return sorted(groupe, key=lambda r: PRIORITE.get(r.get("score_source"), 9))[0]


# --- v35 : lecture d'écran BOT qui échoue à son contrôle ------------------------------------------------------------------------

NOTE_ECART_IMPROBABLE = "écart improbable : à confirmer par l'écran"
SOURCES_TEXTE = ("titre", "description", "sous-titres", "miniature")


def echec_controle_bot(l):
    """Lecture d'écran BOT dont le contrôle a échoué (note `contrôle BOT : …`, ex. `temps de jeu 19 ≠ dernière phase tronquée 18`) : elle ne
    donne JAMAIS un score (ni sûr ni provisoire) ; `temps de jeu non lu` et `temps instable` ne sont pas des échecs de contrôle."""
    return (l.get("mode") == "bot" and l.get("score_source") not in SOURCES_TEXTE and (l.get("detail") or {}).get("phases") is not None
            and l.get("confidence") != "sur" and any(n.startswith("contrôle BOT :") for n in l.get("notes", [])))


def _est_texte(l):
    return l.get("score_source") in SOURCES_TEXTE or bool((l.get("detail") or {}).get("texte_miniature"))


def appliquer_echecs_ecran(lectures):
    """Marque `detail.sans_score` (idempotent, retiré si la lecture est devenue sûre) sur les lectures d'écran BOT en échec de contrôle ; elles
    restent dans `_lectures.json` avec leur note. Cas particulier : si la SEULE différence avec une lecture de texte de la même vidéo est la
    partie entière (millièmes identiques) et que la partie entière du texte est égale au Play Time, la lecture de texte est gardée, `a_verifier`,
    avec la note `écran : partie entière mal lue (18 → 19 par Play Time et titre)`. Modifie sur place ; retourne les lectures marquées."""
    echecs = []
    for l in lectures:
        if l.get("mode") != "bot" or l.get("score_source") in SOURCES_TEXTE or (l.get("detail") or {}).get("phases") is None:
            continue
        d = l.setdefault("detail", {})
        if echec_controle_bot(l):
            d["sans_score"] = True
            echecs.append(l)
        else:
            d.pop("sans_score", None)
    for l in echecs:
        phases = [p for p in l["detail"].get("phases") or [] if isinstance(p, (int, float))]
        pt = l["detail"].get("play_time")
        if not phases or not isinstance(pt, int):
            continue
        p = phases[-1]
        for t in lectures:
            if t.get("video_id") != l["video_id"] or t.get("mode") != "bot" or not _est_texte(t) or t.get("score") is None:
                continue
            s = t["score"]
            if round(s % 1, 3) == round(p % 1, 3) and int(s) == pt and int(p) != pt:
                note = f"écran : partie entière mal lue ({int(p)} → {int(s)} par Play Time et titre)"
                if note not in t["notes"]:
                    t["notes"].append(note)
                t["confidence"], t["exact"] = "a_verifier", False
    return echecs


def ecart_improbable(totaux, seuil=0.7, minimum=5):
    """Valeur en dessous de laquelle un score BOT provisoire est improbable : `seuil` × médiane des scores provisoires (`totaux`, ≥ `minimum`
    lignes), sinon None."""
    v = sorted(totaux)
    if len(v) < minimum:
        return None
    n = len(v)
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
    return seuil * med


def noter_virgule_miniature(lectures, note="miniature : virgule lue comme point"):
    """v35.1, au recalcul : une lecture de miniature déjà stockée dont le texte lu (`detail.brut_miniature`, ou `detail.texte_miniature` s'il
    contient du texte) a une virgule reçoit la note, sans relire la miniature. Modifie sur place ; retourne le nombre de lectures notées."""
    n = 0
    for l in lectures:
        d = l.get("detail") or {}
        brut = d.get("brut_miniature") or (d.get("texte_miniature") if isinstance(d.get("texte_miniature"), str) else "")
        if d.get("texte_miniature") and "," in (brut or "") and note not in l.get("notes", []):
            l.setdefault("notes", []).append(note)
            n += 1
    return n
