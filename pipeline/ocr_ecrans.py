"""Texte OCR d'une image -> écran reconnu -> valeurs lues -> lectures (SPEC_ETAPE1 §3, tris 2 à 4).

L'OCR travaille sur l'image ENTIÈRE : les recadrages par zone sont [EN ATTENTE] des images de référence.
Les libellés reconnus sont ceux de la spec (client anglais : BOT, GB ; coréen : HOTM, POC). Un libellé ou un
nombre non lu vaut None : la lecture reste `a_verifier` (les contrôles arithmétiques de ecrans.py décident).
**Non éprouvé sur de vraies captures** : les tests utilisent des textes OCR synthétiques tirés de la spec.
"""
import re

import ecrans

_ENT = r"(\d{1,3}(?:[,.   ]\d{3})+|\d+)"        # 15 763 121 797 048 | 94,600 | 165
_SEP = r"[^\d\n]{0,8}"                                        # bruit entre le libellé et le nombre
_TEMPS = re.compile(r"(\d{1,2}):(\d{2})\.(\d{3})")


_RAGE = re.compile(r"rage\s*[gc]oun?t?\b", re.IGNORECASE)
_GROS_NOMBRES = re.compile(r"\d{4,}(?:[,.]\d{3})*|\d{1,3}(?:[,.]\d{3})+")


def normaliser(texte):
    """v11 : tolère les fautes d'OCR courantes du Rage Count (`Rage Gount`, `RageCount`, `Rage Coun`)."""
    return _RAGE.sub("Rage Count", texte or "")


def _entier(s):
    return int(re.sub(r"[,.   ]", "", s))


def _nombre_apres(libelle, texte, rx=_ENT):
    m = re.search(libelle + _SEP + rx, texte, re.IGNORECASE)
    return _entier(m.group(1)) if m else None


def _ligne_apres(titre, texte):
    m = re.search(titre + r"[^\n]*\n\s*([^\n]+)", texte, re.IGNORECASE)
    return m.group(1).strip() if m else None


def detecter(texte):
    """Type d'écran d'après ses libellés, ou None. `gb_record` avant `gb_results` ; HOTM avant POC."""
    t = normaliser(texte)
    bas = t.lower()
    if "personal record" in bas and ("total rage count" in bas or "group 1" in bas):
        return "gb_record"
    if "final score" in bas and ("hunter rank" in bas or "your points have been registered" in bas):
        return "gb_results"
    if "your points have been registered" in bas or "rage rewards" in bas:
        return "gb_results_partiel"   # v12 : écran Results en animation, valeurs pas (encore) lisibles
    if re.search(r"\bpoints\b", bas) and "boss rage count" in bas and chrono_hud(t) is not None:
        return "gb_combat"     # v11 : HUD pendant la run (jamais un écran de résultat)
    if "phase 1" in bas and "play time" in bas and _TEMPS.search(t):
        return "bot"
    if "합산" in t and ("증명" in t or "클리어" in t):
        return "hotm"
    if "이번" in t and ("플레이어 스코어" in t or "계승자 스코어" in t):
        return "poc"
    return None


def chrono_hud(texte):
    """Chrono du HUD GB en secondes : `mm:ss` (≤ 3 min) ou `ss.cc` (sous 1 min, ex. `10.45`) ; None si illisible.
    Les grands nombres (Points) sont retirés d'abord."""
    t = _GROS_NOMBRES.sub(" ", texte or "")
    for m in re.finditer(r"(?<!\d)(\d{1,2})[:;](\d{2})(?!\d)", t):
        if int(m.group(1)) <= 3 and int(m.group(2)) < 60:
            return int(m.group(1)) * 60 + int(m.group(2))
    for m in re.finditer(r"(?<![\d.,])(\d{1,2})\.(\d{2})(?!\d)", t):
        if int(m.group(1)) < 60:
            return int(m.group(1)) + int(m.group(2)) / 100
    return None


def lire_gb_combat(texte):
    """v11 : HUD du combat GB. Points (information), Boss Rage Count `xN`, chrono. Un élément illisible = None."""
    t = normaliser(texte)
    pts = re.search(r"points\W{0,6}(\d+(?:[,.]\d{3})+|\d+)", t, re.IGNORECASE)
    rc = re.search(r"boss\s*rage\s*count\W{0,6}[xX×]\s*(\d{1,3})(?!\d)", t, re.IGNORECASE)
    return {"points": _entier(pts.group(1)) if pts else None, "rage_count": int(rc.group(1)) if rc else None,
            "chrono": chrono_hud(t), "stage": None}


def lire_bot(texte):
    temps = [int(m) * 60 + int(s) + int(ms) / 1000 for m, s, ms in _TEMPS.findall(texte)]
    phases, chrono = temps, None
    if len(temps) >= 2 and abs(temps[-1] - temps[-2]) < 1e-3:   # le bandeau du bas répète la dernière phase
        phases, chrono = temps[:-1], temps[-1]
    pt = re.search(r"play\s*time\D{0,5}(\d{1,2}):(\d{2})", texte, re.IGNORECASE)
    return {"stage": _ligne_apres(r"\bResults\b", texte), "phases": phases, "chrono": chrono,
            "play_time": int(pt.group(1)) * 60 + int(pt.group(2)) if pt else None,
            "player_ingame": None, "armes_sjw": None}   # pseudo et armes : [EN ATTENTE] (icônes, recadrage)


def _valeurs_sous_libelles(texte):
    """Mise en page vue le 14/11 (écran Results qui s'affiche) : `Final Score` et `Rage Count` sont deux libellés sur
    une même ligne, leurs valeurs sur la ligne suivante (`1.601.097.999 19`). Retourne (final_score, rage_count)."""
    m = re.search(r"final\s*score[^\n]*rage\s*count[^\n]*\n\s*([^\n]+)", texte, re.IGNORECASE)
    if not m:
        return None, None
    nombres = re.findall(r"\d{1,3}(?:[.,]\d{3})+|\d+", m.group(1))
    if len(nombres) < 2:
        return None, None
    return _entier(nombres[0]), int(nombres[-1]) if re.fullmatch(r"\d{1,3}", nombres[-1]) else None


def _nombre_lignes_suivantes(libelle, texte, lignes=2):
    """Valeur écrite sur l'une des `lignes` lignes qui suivent le libellé (mise en page de l'écran Results en animation)."""
    m = re.search(libelle + r"[^\n]*\n((?:[^\n]*\n?){1,%d})" % lignes, texte, re.IGNORECASE)
    n = re.search(r"\d{1,3}(?:[.,]\d{3})+|\d{4,}", m.group(1)) if m else None
    return _entier(n.group(0)) if n else None


def lire_gb_results(texte):
    final_sous, rc_sous = _valeurs_sous_libelles(texte)
    return {"stage": _ligne_apres(r"\bResults\b", texte),
            "player_score": _nombre_apres(r"player'?s\s*score", texte) or _nombre_lignes_suivantes(r"player'?s\s*score", texte),
            "hunter_ranks": [_entier(x) for x in re.findall(r"hunter\s*rank\s*[1-6]" + _SEP + _ENT, texte, re.IGNORECASE)],
            "final_score": _nombre_apres(r"final\s*score", texte) or final_sous,
            "rage_count": _nombre_apres(r"rage\s*count", texte, r"(\d{1,3})(?!\d)") or rc_sous,
            "play_time": (re.search(r"play\s*time\D{0,5}(\d{1,2}:\d{2})", texte, re.IGNORECASE) or [None, None])[1],
            "new_record": "new record" in texte.lower()}


def lire_gb_record(texte):
    groupes = {}
    for g, rc, deg in re.findall(r"group\s*([12])" + _SEP + r"(\d{1,3})(?!\d)[^\d\n]{1,12}(\d+(?:[.,]\d+)?\s*[KMBT])\b", texte, re.IGNORECASE):
        groupes[int(g)] = {"rage_count": int(rc), "damage": deg.replace(" ", "").replace(",", ".")}
    tl = re.search(r"time\s*left\s*in\s*season\D{0,6}((?:\d+\s*d)?\s*(?:\d+\s*h)?\s*(?:\d+\s*m)?)", texte, re.IGNORECASE)
    return {"stage": None, "groups": groupes, "total_rage_count": _nombre_apres(r"total\s*rage\s*count", texte, r"(\d{1,4})(?!\d)"),
            "total_score": _nombre_apres(r"total\s*score", texte), "challenge_count": _nombre_apres(r"challenge\s*count", texte, r"(\d+)"),
            "time_left": tl.group(1).strip() if tl and tl.group(1).strip() else None}


def lire_hotm(texte):
    m = re.search(r"RESULT\s*[—–-]\s*([^\n]+)", texte)
    return {"clear": _nombre_apres(r"클리어", texte), "proof_bonus": _nombre_apres(r"증명\s*보너스", texte),
            "total": _nombre_apres(r"합산\s*결과", texte),
            "record": _nombre_apres(r"이번\s*기록", texte),     # jamais « 기존 기록 »
            "stage": m.group(1).strip() if m else None, "proof_level": None}


def lire_poc(texte):
    return {"record": _nombre_apres(r"이번\s*기록", texte), "sjw": _nombre_apres(r"플레이어\s*스코어", texte),
            "successor": _nombre_apres(r"계승자\s*스코어", texte), "hunters": None, "stage": None}


LECTEURS = {"gb_results_partiel": lire_gb_results, "gb_combat": lire_gb_combat, "bot": lire_bot, "gb_results": lire_gb_results, "gb_record": lire_gb_record, "hotm": lire_hotm, "poc": lire_poc}


def lectures_depuis_texte(texte, meta, config, source, t=None, zones=None):
    """Texte OCR d'une image -> lectures de la vidéo (liste, éventuellement vide)."""
    texte = normaliser(texte)
    type_ecran = detecter(texte)
    if type_ecran is None:
        return []
    ecran = {**LECTEURS[type_ecran](texte), "t": t}
    if type_ecran in ("gb_results", "gb_results_partiel"):
        ecran["stage"] = _boss_du_hud(texte, config) or ecran["stage"]     # v12 : nom normalisé si le boss est connu
        if zones:   # lecture ciblée (recadrage agrandi) : plus fiable que l'image entière
            ecran["stage"] = boss_connu(zones.get("boss"), config) or ecran["stage"]
            ecran["player_score"] = _nombre_zone(zones.get("joueur")) or ecran["player_score"]
        type_ecran = "gb_results"
    if type_ecran == "gb_combat":
        ecran["stage"] = _boss_du_hud(texte, config)
        l = ecrans.lecture_gb_combat(meta, ecran, config, source)
        return [l] if l else []
    if type_ecran == "bot":
        l = ecrans.lecture_bot(meta, ecran, config, source)
    elif type_ecran == "gb_results":
        l = ecrans.lecture_gb_results(meta, ecran, config, source)
    elif type_ecran == "gb_record":
        return ecrans.lectures_gb_record(meta, ecran, config)
    elif type_ecran == "hotm":
        l = ecrans.lecture_hotm(meta, ecran, config, source)
    else:
        l = ecrans.lecture_poc(meta, ecran, config, source)
    return [l] if l else []


def _nombre_zone(texte):
    """Nombre lu dans un recadrage (ex. Player's Score `313,099,049`) ; None s'il est trop court ou illisible."""
    m = re.search(r"\d{1,3}(?:[.,]\d{3}){2,}", texte or "")
    return _entier(m.group(0)) if m else None


def boss_connu(texte, config, seuil=0.75):
    """Nom de boss de `config.gb.boss_noms` reconnu dans un court texte (recadrage), avec tolérance aux fautes d'OCR."""
    import difflib
    lignes = [re.sub(r"[^A-Za-z ]", "", l).strip().lower() for l in (texte or "").splitlines()]
    for nom in (config.get("gb") or {}).get("boss_noms", ["Giant Statue"]):
        if any(l and difflib.SequenceMatcher(None, l, nom.lower()).ratio() >= seuil for l in lignes):
            return nom
    return None


def _boss_du_hud(texte, config):
    """Nom du boss en haut du HUD, seulement s'il figure dans `config.gb.boss_noms` : une cible secondaire
    (`Temple Altar`) n'est jamais prise comme `stage`."""
    for nom in (config.get("gb") or {}).get("boss_noms", ["Giant Statue"]):
        if re.search(re.sub(r"\s+", r"\\s*", re.escape(nom).replace("\\ ", " ")), texte, re.IGNORECASE):
            return nom
    return None


def regrouper_hud(lectures, config=None):
    """v12 : les lectures de combat (`detail.ecran == "combat"`, sans score) d'une vidéo sont regroupées par run (le
    chrono repart à la hausse : > `gb.hud_nouvelle_run_s`, 20 s). Par run, une lecture : chrono le plus bas,
    `hud_rage_count` le plus haut (information), et `damage` = `Points` de la lecture au chrono le plus bas SI ce
    chrono est ≤ `gb.hud_chrono_points_s` (5 s) : dégâts provisoires (`damage_exact: false`, `damage_source: hud`).
    Jamais un RC. Idempotent : les lectures déjà regroupées sont reprises comme lectures brutes."""
    cfg = (config or {}).get("gb") or {}
    seuil, chrono_max = cfg.get("hud_nouvelle_run_s", 20), cfg.get("hud_chrono_points_s", 5)
    est_hud = lambda l: (l.get("detail") or {}).get("ecran") == "combat"
    hud = [l for l in lectures if est_hud(l)]
    sortie = [l for l in lectures if not est_hud(l)]
    for vid in sorted({l["video_id"] for l in hud}):
        runs = []
        for l in sorted((x for x in hud if x["video_id"] == vid), key=lambda x: (x["t"] is None, x["t"] or 0)):
            if not runs or l["detail"]["chrono_hud"] > runs[-1][-1]["detail"]["chrono_hud"] + seuil:
                runs.append([])
            runs[-1].append(l)
        for run in runs:
            dernier = min(run, key=lambda x: x["detail"]["chrono_hud"])
            d = {**dernier["detail"], "hud_rage_count": max(x["detail"]["hud_rage_count"] for x in run)}
            points = d.get("hud_points") if d["chrono_hud"] <= chrono_max else None
            if points is not None:
                d.update(damage_exact=False, damage_source="hud")
            sortie.append({**dernier, "damage": points, "detail": d,
                           "notes": [f"HUD : Boss Rage Count x{d['hud_rage_count']}, chrono {d['chrono_hud']}"]})
    return sortie


def fusionner_results(lectures, config=None):
    """v12 : toutes les lectures de l'écran Results d'une vidéo (images successives de l'animation) : regroupées en
    écrans (images à moins de `gb.results_cluster_s` = 15 s l'une de l'autre), une lecture par écran : la plus complète
    (`detail.completude`, puis la plus tardive). Contrôle sans Hunter Rank (ecrans.controle_results_sans_hunter_rank)
    avec le HUD qui précède (≤ `gb.hud_results_fenetre_s`) ; `hud_rage_count` du HUD gardé pour information.
    Idempotent (`detail.lectures_identiques` cumule les images concordantes)."""
    cfg = (config or {}).get("gb") or {}
    ecart, fenetre = cfg.get("results_cluster_s", 15), cfg.get("hud_results_fenetre_s", 60)
    est_res = lambda l: (l["mode"] == "gb" and l["score_source"] in ("debut-fin", "video-complete")
                         and (l.get("detail") or {}).get("ecran") != "combat")
    resultats = sorted((l for l in lectures if est_res(l)), key=lambda l: (l["video_id"], l["t"] or 0))
    autres = [l for l in lectures if not est_res(l)]
    huds = [l for l in autres if (l.get("detail") or {}).get("ecran") == "combat"]
    ecrans_res, courant = [], []
    for l in resultats:
        if courant and (l["video_id"] != courant[-1]["video_id"] or (l["t"] or 0) - (courant[-1]["t"] or 0) > ecart):
            ecrans_res.append(courant)
            courant = []
        courant.append(l)
    if courant:
        ecrans_res.append(courant)
    sortie = list(autres)
    for groupe in ecrans_res:
        avec_rc = [l for l in groupe if l.get("score") is not None]
        if not avec_rc:          # écran vu sans Rage Count lisible : rien à classer
            continue
        best = max(avec_rc, key=lambda l: ((l.get("detail") or {}).get("completude", 0), l["t"] or 0))
        cle = (best.get("damage"), best["score"])
        identiques = sum((l.get("detail") or {}).get("lectures_identiques", 1) for l in avec_rc if (l.get("damage"), l["score"]) == cle)
        # champs manquants (boss, Player's Score, Play Time) repris des autres images du même écran
        manque = {}
        for l in sorted(groupe, key=lambda l: -(l.get("detail") or {}).get("completude", 0)):
            for champ, valeur in (("stage", l.get("stage")), ("player_score", (l.get("detail") or {}).get("player_score")),
                                  ("play_time", (l.get("detail") or {}).get("play_time"))):
                if valeur is not None and champ not in manque:
                    manque[champ] = valeur
        hud = max((h for h in huds if h["video_id"] == best["video_id"] and h["t"] is not None and best["t"] is not None
                   and 0 <= best["t"] - h["t"] <= fenetre), key=lambda h: h["t"], default=None)
        d = {**best["detail"], "lectures_identiques": identiques}
        for champ in ("player_score", "play_time"):
            if d.get(champ) is None and champ in manque:
                d[champ] = manque[champ]
        if hud:
            d["hud_rage_count"] = hud["detail"]["hud_rage_count"]
        lec = {**best, "stage": best.get("stage") or manque.get("stage"), "detail": d, "notes": [n for n in best["notes"] if not n.startswith("contrôle sans Hunter Rank :")]}
        if d.get("hunter_ranks_lus", 0) < 6 and not lec["exact"]:   # Hunter Rank illisibles : contrôle de remplacement
            ok, pb = ecrans.controle_results_sans_hunter_rank(lec, hud, config or {}, identiques)
            if ok:
                lec.update(exact=True, confidence="sur", notes=[n for n in lec["notes"] if not n.startswith("contrôle GB")]
                           + ["contrôle sans Hunter Rank"])
            else:
                lec["notes"] += [f"contrôle sans Hunter Rank : {p}" for p in pb]
        sortie.append(lec)
    return sortie


def dedoublonner_lectures(lectures):
    """Une même image d'écran est lue à plusieurs instants (1 image / 2 s) : une seule lecture par
    (vidéo, mode, groupe/équipe, score, dégâts) ; la plus tôt dans la vidéo est gardée."""
    vues, sortie = set(), []
    for l in sorted(lectures, key=lambda l: (l.get("t") is None, l.get("t") or 0)):
        cle = (l["video_id"], l["mode"], l.get("team"), l["score"], l.get("damage"), l["score_source"] == "record",
               l["t"] if l["score_source"] == "hud" else None)
        if cle not in vues:
            vues.add(cle)
            sortie.append(l)
    return sortie
