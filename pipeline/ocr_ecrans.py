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
    t = texte or ""
    bas = t.lower()
    if "personal record" in bas and ("total rage count" in bas or "group 1" in bas):
        return "gb_record"
    if "final score" in bas and "hunter rank" in bas:
        return "gb_results"
    if "phase 1" in bas and "play time" in bas and _TEMPS.search(t):
        return "bot"
    if "합산" in t and ("증명" in t or "클리어" in t):
        return "hotm"
    if "이번" in t and ("플레이어 스코어" in t or "계승자 스코어" in t):
        return "poc"
    return None


def lire_bot(texte):
    temps = [int(m) * 60 + int(s) + int(ms) / 1000 for m, s, ms in _TEMPS.findall(texte)]
    phases, chrono = temps, None
    if len(temps) >= 2 and abs(temps[-1] - temps[-2]) < 1e-3:   # le bandeau du bas répète la dernière phase
        phases, chrono = temps[:-1], temps[-1]
    pt = re.search(r"play\s*time\D{0,5}(\d{1,2}):(\d{2})", texte, re.IGNORECASE)
    return {"stage": _ligne_apres(r"\bResults\b", texte), "phases": phases, "chrono": chrono,
            "play_time": int(pt.group(1)) * 60 + int(pt.group(2)) if pt else None,
            "player_ingame": None, "armes_sjw": None}   # pseudo et armes : [EN ATTENTE] (icônes, recadrage)


def lire_gb_results(texte):
    return {"stage": _ligne_apres(r"\bResults\b", texte),
            "player_score": _nombre_apres(r"player'?s\s*score", texte),
            "hunter_ranks": [_entier(x) for x in re.findall(r"hunter\s*rank\s*[1-6]" + _SEP + _ENT, texte, re.IGNORECASE)],
            "final_score": _nombre_apres(r"final\s*score", texte),
            "rage_count": _nombre_apres(r"rage\s*count", texte, r"(\d{1,3})(?!\d)"),
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


LECTEURS = {"bot": lire_bot, "gb_results": lire_gb_results, "gb_record": lire_gb_record, "hotm": lire_hotm, "poc": lire_poc}


def lectures_depuis_texte(texte, meta, config, source, t=None):
    """Texte OCR d'une image -> lectures de la vidéo (liste, éventuellement vide)."""
    type_ecran = detecter(texte)
    if type_ecran is None:
        return []
    ecran = {**LECTEURS[type_ecran](texte), "t": t}
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


def dedoublonner_lectures(lectures):
    """Une même image d'écran est lue à plusieurs instants (1 image / 2 s) : une seule lecture par
    (vidéo, mode, groupe/équipe, score, dégâts) ; la plus tôt dans la vidéo est gardée."""
    vues, sortie = set(), []
    for l in sorted(lectures, key=lambda l: (l.get("t") is None, l.get("t") or 0)):
        cle = (l["video_id"], l["mode"], l.get("team"), l["score"], l.get("damage"), l["score_source"] == "record")
        if cle not in vues:
            vues.add(cle)
            sortie.append(l)
    return sortie
