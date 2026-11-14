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


def _rangs(texte):
    """`Hunter Rank k <score>` -> liste de 6 valeurs (None = rang non lu)."""
    rangs = [None] * 6
    for k, v in re.findall(r"hunter\s*rank\s*([1-6])" + _SEP + _ENT, texte, re.IGNORECASE):
        rangs[int(k) - 1] = _entier(v)
    return rangs


def lire_gb_results(texte):
    final_sous, rc_sous = _valeurs_sous_libelles(texte)
    return {"stage": _ligne_apres(r"\bResults\b", texte),
            "player_score": _nombre_apres(r"player'?s\s*score", texte) or _nombre_lignes_suivantes(r"player'?s\s*score", texte),
            "hunter_ranks": _rangs(texte),
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


def _entier_court(texte):
    m = re.search(r"(?<!\d)(\d{1,3})(?!\d)", texte or "")
    return int(m.group(1)) if m else None


def _temps_zone(texte):
    m = re.search(r"(\d{1,2}):(\d{2})", texte or "")
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def interpreter_zones(zones, config):
    """Textes lus dans les zones ciblées (`config.gb.zones`) -> valeurs (None = illisible)."""
    return {"stage": boss_connu(zones.get("boss"), config), "player_score": _nombre_zone(zones.get("joueur")),
            "hunter_ranks": [_nombre_zone(zones.get(f"rang_{k}")) for k in range(1, 7)],
            "final_score": _nombre_zone(zones.get("final")), "rage_count": _entier_court(zones.get("rage")),
            "play_time": _temps_zone(zones.get("temps"))}


def _appliquer_zones(ecran, zones, config):
    """v13 : la valeur d'une zone ciblée prime sur celle de l'image entière ; si les deux diffèrent, note
    `écart OCR zone/image : <champ>`. Format non 16:9 : zones non appliquées, note `format non standard`."""
    notes = ecran.setdefault("notes_extra", [])
    if zones.get("format_ok") is False:
        notes.append("format non standard")
        return
    z = interpreter_zones(zones, config)
    for champ in ("stage", "player_score", "final_score", "rage_count", "play_time"):
        if z[champ] is None:
            continue
        image = ecran.get(champ)
        if image is not None and image != z[champ] and (champ != "stage" or boss_connu(image, config)):
            notes.append(f"écart OCR zone/image : {champ}")
        ecran[champ] = z[champ]
    rangs = list(ecran.get("hunter_ranks") or [None] * 6)
    for k, v in enumerate(z["hunter_ranks"]):
        if v is None:
            continue
        if rangs[k] is not None and rangs[k] != v:
            notes.append(f"écart OCR zone/image : hunter_rank_{k + 1}")
        rangs[k] = v
    ecran["hunter_ranks"] = rangs


def lectures_depuis_texte(texte, meta, config, source, t=None, zones=None):
    """Texte OCR d'une image -> lectures de la vidéo (liste, éventuellement vide). `zones` : textes lus dans les
    zones ciblées de l'écran Results (pc.lire_zones_results)."""
    texte = normaliser(texte)
    type_ecran = detecter(texte)
    if type_ecran is None:
        return []
    ecran = {**LECTEURS[type_ecran](texte), "t": t}
    if type_ecran in ("gb_results", "gb_results_partiel"):
        ecran["stage"] = _boss_du_hud(texte, config) or ecran["stage"]     # v12 : nom normalisé si le boss est connu
        if zones is not None:
            _appliquer_zones(ecran, zones, config)
        type_ecran = "gb_results"
    if type_ecran == "gb_combat":
        ecran["stage"] = _boss_du_hud(texte, config)
        lectures = [ecrans.lecture_gb_combat(meta, ecran, config, source)]
    elif type_ecran == "bot":
        lectures = [ecrans.lecture_bot(meta, ecran, config, source)]
    elif type_ecran == "gb_results":
        lectures = [ecrans.lecture_gb_results(meta, ecran, config, source)]
    elif type_ecran == "gb_record":
        lectures = ecrans.lectures_gb_record(meta, ecran, config)
    elif type_ecran == "hotm":
        lectures = [ecrans.lecture_hotm(meta, ecran, config, source)]
    else:
        lectures = [ecrans.lecture_poc(meta, ecran, config, source)]
    lectures = [l for l in lectures if l]
    for l in lectures:
        l["regles"] = config.get("tri1_version")      # v13 : version des règles, aussi sur les lectures d'écran
    return lectures


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
            d = {**dernier["detail"], "hud_rage_count": max(x["detail"]["hud_rage_count"] for x in run),
                 "t_debut": min(x["detail"].get("t_debut", x["t"]) for x in run), "t_fin": max(x["detail"].get("t_fin", x["t"]) for x in run)}
            points = d.get("hud_points") if d["chrono_hud"] <= chrono_max else None
            if points is not None:
                d.update(damage_exact=False, damage_source="hud")
            sortie.append({**dernier, "damage": points, "detail": d,
                           "notes": [f"HUD : Boss Rage Count x{d['hud_rage_count']}, chrono {d['chrono_hud']}"]})
    return sortie


CHAMPS_RESULTS = ("stage", "player_score", "final_score", "rage_count", "play_time") + tuple(f"hunter_rank_{k}" for k in range(1, 7))


def _valeurs_results(l):
    d = l.get("detail") or {}
    rangs = list(d.get("hunter_ranks") or [None] * 6)
    v = {"stage": l.get("stage"), "player_score": d.get("player_score"), "final_score": l.get("damage"),
         "rage_count": l.get("score"), "play_time": d.get("play_time")}
    v.update({f"hunter_rank_{k + 1}": rangs[k] for k in range(6)})
    return v


def _votes_results(l):
    """Votes par champ : {champ: [[valeur, nombre d'images], …]}. Une lecture fusionnée garde ses votes (idempotence)."""
    deja = (l.get("detail") or {}).get("votes")
    if deja:
        return deja
    return {c: [[v, 1]] for c, v in _valeurs_results(l).items() if v is not None}


def fusionner_results(lectures, config=None):
    """v13 : lectures de l'écran Results d'une vidéo, fusionnées CHAMP PAR CHAMP sur les images consécutives d'un même
    écran : au plus `gb.fusion_max_s` (15 s) entre la première et la dernière image, sans HUD de combat entre elles.
    Par champ : valeur la plus fréquente ; égalité -> `a_verifier` + note `conflit de lecture : <champ>`. La lecture
    fusionnée porte `lecture fusionnée (n images)`, `t` = première image où le `Rage Count` retenu est lu. Sans
    `Rage Count` lu sur aucune image : l'écran n'est pas classé. Contrôles : somme des 6 `Hunter Rank` si tous lus,
    sinon contrôle sans Hunter Rank (ecrans.controle_results_sans_hunter_rank) avec le HUD qui précède.
    Idempotent (les votes sont conservés dans `detail.votes`)."""
    cfg = (config or {}).get("gb") or {}
    fusion_max, fenetre = cfg.get("fusion_max_s", 15), cfg.get("hud_results_fenetre_s", 60)
    est_res = lambda l: (l["mode"] == "gb" and l["score_source"] in ("debut-fin", "video-complete")
                         and (l.get("detail") or {}).get("ecran") != "combat")
    resultats = sorted((l for l in lectures if est_res(l)), key=lambda l: (l["video_id"], l["t"] or 0))
    autres = [l for l in lectures if not est_res(l)]
    huds = [l for l in autres if (l.get("detail") or {}).get("ecran") == "combat"]
    debut = lambda l: (l.get("detail") or {}).get("t_debut", l["t"] or 0)
    fin = lambda l: (l.get("detail") or {}).get("t_fin", l["t"] or 0)

    def hud_entre(vid, a, b):
        return any(h["video_id"] == vid and h["t"] is not None and a < fin(h) and debut(h) < b for h in huds)

    ecrans_res, courant = [], []
    for l in resultats:
        if courant and (l["video_id"] != courant[0]["video_id"] or fin(l) - debut(courant[0]) > fusion_max
                        or hud_entre(l["video_id"], max(fin(x) for x in courant), debut(l))):
            ecrans_res.append(courant)
            courant = []
        courant.append(l)
    if courant:
        ecrans_res.append(courant)
    sortie = list(autres)
    for groupe in ecrans_res:
        if not any(l.get("score") is not None for l in groupe):
            continue                                  # écran vu sans Rage Count lisible : rien à classer
        votes = {}
        for l in groupe:
            for champ, liste in _votes_results(l).items():
                for valeur, n in liste:
                    cumul = votes.setdefault(champ, {})
                    cumul[valeur] = cumul.get(valeur, 0) + n
        retenu, conflits = {}, []
        for champ, cumul in votes.items():
            classes = sorted(cumul.items(), key=lambda kv: -kv[1])
            retenu[champ] = classes[0][0]
            if champ == "rage_count":      # v14 : ≥ 2 fois plus d'images que toutes les lectures discordantes réunies
                if len(classes) > 1 and classes[0][1] < 2 * sum(n for _, n in classes[1:]):
                    conflits.append(champ)
            elif len(classes) > 1 and classes[0][1] == classes[1][1]:
                conflits.append(champ)
        rc, final = retenu.get("rage_count"), retenu.get("final_score")
        avec_rc = [l for l in groupe if l.get("score") == rc]
        base = min(avec_rc, key=lambda l: l["t"] or 0)
        rc_t = {}                                   # valeur de Rage Count -> première image où elle est lue

        def noter(valeur, t_v):
            if valeur is not None and t_v is not None:
                rc_t[str(valeur)] = min(t_v, rc_t.get(str(valeur), t_v))
        for l in groupe:
            noter(l.get("score"), l["t"])
            for k, t_k in ((l.get("detail") or {}).get("rc_t") or {}).items():
                noter(k, t_k)
        n_images = sum((l.get("detail") or {}).get("n_images", 1) for l in groupe)
        nombre = lambda champ, valeur: votes.get(champ, {}).get(valeur, 0)
        rangs = [retenu.get(f"hunter_rank_{k}") for k in range(1, 7)]
        hud = max((h for h in huds if h["video_id"] == base["video_id"] and h["t"] is not None and base["t"] is not None
                   and 0 <= base["t"] - h["t"] <= fenetre), key=lambda h: h["t"], default=None)
        d = {**base["detail"], "player_score": retenu.get("player_score"), "hunter_ranks": rangs,
             "hunter_ranks_lus": sum(r is not None for r in rangs), "play_time": retenu.get("play_time"),
             "new_record": any((l.get("detail") or {}).get("new_record") for l in groupe),
             "votes": {c: [[v, n] for v, n in cumul.items()] for c, cumul in votes.items()},
             "rc_images": nombre("rage_count", rc), "final_images": nombre("final_score", final), "n_images": n_images,
             "rc_t": rc_t,
             "t_debut": min(debut(l) for l in groupe), "t_fin": max(fin(l) for l in groupe)}
        d.pop("ecran", None)
        d.pop("completude", None)
        d.pop("lectures_identiques", None)
        if hud:
            d["hud_rage_count"] = hud["detail"]["hud_rage_count"]
        notes = []
        for l in groupe:
            for n in l["notes"]:
                if not n.startswith(("contrôle sans Hunter Rank", "lecture fusionnée", "conflit de lecture", "contrôle GB", "RC discordant écarté")) and n not in notes:
                    notes.append(n)
        if n_images >= 2:
            notes.append(f"lecture fusionnée ({n_images} images)")
        notes += [f"conflit de lecture : {c}" for c in conflits]
        if "rage_count" not in conflits:            # v14 : chaque valeur de Rage Count écartée est notée
            notes += [f"RC discordant écarté : {v} (t={rc_t.get(str(v))})" for v in votes.get("rage_count", {}) if v != rc]
        lec = {**base, "stage": retenu.get("stage"), "damage": final, "score": rc, "detail": d, "notes": notes,
               "exact": False, "confidence": "a_verifier"}
        if not conflits:
            if d["hunter_ranks_lus"] == 6:                     # somme Player's Score + 6 Hunter Rank = Final Score
                ok, pb = ecrans.controle_gb_results(d["player_score"], rangs, final)
                if ok:
                    lec.update(exact=True, confidence="sur")
                else:
                    lec["notes"] += [f"contrôle GB : {p}" for p in pb]
            else:                                              # contrôle de remplacement (v13, durci)
                ok, pb = ecrans.controle_results_sans_hunter_rank(lec, hud, config or {})
                if ok:
                    lec.update(exact=True, confidence="sur")
                    lec["notes"].append("contrôle sans Hunter Rank")
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
               l["t"] if (l.get("detail") or {}).get("ecran") == "combat" else None)
        if cle not in vues:
            vues.add(cle)
            sortie.append(l)
    return sortie
