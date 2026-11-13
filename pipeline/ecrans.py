"""Écrans lus -> entrées de `_lectures.json`, avec les contrôles de la spec (§3.1, §3.2, §4.7).

La lecture des images (OCR, recadrages) est [EN ATTENTE] : ces fonctions reçoivent les valeurs déjà lues
(dict `ecran`) et produisent les lectures que `classement.py` consomme. Une valeur illisible vaut None :
la lecture reste `a_verifier`, jamais une valeur inventée.

- lecture_bot(meta, ecran, config)          écran `Results` du BOT (v4) ; variante d'après les armes de SJW (v5)
- lecture_gb_results(meta, ecran, config)   écran `Results` du GB (v5)
- lectures_gb_record(meta, ecran, config)   écran `Guild Boss` > `Personal Record` du GB (v6) : 2 lectures (groupes 1 et 2)
- lecture_hotm(meta, ecran, config)         écran RESULT du HOTM : clear + preuve = total = 이번 기록
- lecture_poc(meta, ecran, config)          écran RESULT du POC : 이번 기록 (`sur` seulement si les 5 composants sont lus et égaux)
"""
import re

from hotm_ecran import lire_porte
from tri1 import lecture_vide, notes_alerte_reset, variante_bot


def controle_bot(phases, chrono, play_time):
    """v4 : dernière phase = chrono du bandeau, `Play Time` = ce chrono tronqué à la seconde,
    phases croissantes. Retourne (ok, problèmes)."""
    if not phases or chrono is None or play_time is None:
        return False, ["écran BOT illisible (phases, chrono ou Play Time)"]
    pb = []
    if any(b <= a for a, b in zip(phases, phases[1:])):
        pb.append("phases non croissantes")
    if abs(phases[-1] - chrono) > 1e-3:
        pb.append(f"dernière phase {phases[-1]} ≠ chrono {chrono}")
    if int(chrono) != play_time:
        pb.append(f"Play Time {play_time} ≠ chrono tronqué {int(chrono)}")
    return not pb, pb


def lecture_bot(meta, ecran, config, source="video-complete"):
    phases, chrono = ecran.get("phases"), ecran.get("chrono")
    ok, pb = controle_bot(phases, chrono, ecran.get("play_time"))
    score = phases[-1] if phases else chrono
    if score is None:
        return None
    lec = lecture_vide(meta, "bot")
    lec["notes"] += notes_alerte_reset(meta, config)
    lec.update(score=round(score, 3), score_source=source, exact=ok, confidence="sur" if ok else "a_verifier",
               stage=ecran.get("stage"), t=ecran.get("t"), player_ingame=ecran.get("player_ingame"),
               detail={"phases": phases, "play_time": ecran.get("play_time")})
    lec["notes"] += [f"contrôle BOT : {p}" for p in pb]
    titre = variante_bot(meta.get("title"), config)
    armes = ecran.get("armes_sjw")  # True : armes de SJW dans le bandeau ; False : absentes ; None : illisible
    if armes is not None:  # l'écran prime sur le titre (v5, indice [À CONFIRMER] sur une capture de challenge)
        lec["bot_variant"] = "season" if armes else "challenge"
        lec["notes"].append("variante d'après les armes de SJW [À CONFIRMER]")
        if titre and titre != lec["bot_variant"]:
            lec["notes"].append(f"titre : {titre}")
    elif titre:
        lec["bot_variant"] = titre
        lec["notes"].append("variante d'après le titre")
    return lec


def controle_gb_results(player_score, hunter_ranks, final_score):
    """v5 : `Player's Score` + les 6 `Hunter Rank` = `Final Score`. Le RC n'a pas de contrôle arithmétique."""
    if player_score is None or final_score is None or not hunter_ranks or len(hunter_ranks) != 6 or None in hunter_ranks:
        return False, ["écran GB illisible (Player's Score, Hunter Rank ou Final Score)"]
    somme = player_score + sum(hunter_ranks)
    return somme == final_score, ([] if somme == final_score else [f"somme {somme} ≠ Final Score {final_score}"])


def lecture_gb_results(meta, ecran, config, source="video-complete"):
    if ecran.get("rage_count") is None:
        return None
    ok, pb = controle_gb_results(ecran.get("player_score"), ecran.get("hunter_ranks"), ecran.get("final_score"))
    lec = lecture_vide(meta, "gb")
    lec["notes"] += notes_alerte_reset(meta, config)
    lec.update(score=ecran["rage_count"], damage=ecran.get("final_score"), score_source=source, exact=ok,
               confidence="sur" if ok else "a_verifier", stage=ecran.get("stage"), t=ecran.get("t"), team=None,
               detail={"damage_exact": True, "play_time": ecran.get("play_time"),
                       "new_record": bool(ecran.get("new_record"))})  # groupe inconnu : voir gb.rattacher_groupes
    lec["notes"] += [f"contrôle GB : {p}" for p in pb]
    return lec


def degats_arrondis(texte):
    """`17.28T` -> (17_280_000_000_000, pas d'arrondi 1e10). Nombre déjà lu : (valeur, None)."""
    if isinstance(texte, (int, float)):
        return texte, None
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*([KMBT])\s*", texte or "", re.IGNORECASE)
    if not m:
        return None, None
    mult = {"k": 10**3, "m": 10**6, "b": 10**9, "t": 10**12}[m.group(2).lower()]
    chiffres = m.group(1).replace(",", ".")
    decimales = len(chiffres.split(".")[1]) if "." in chiffres else 0
    return round(float(chiffres) * mult), mult * 10 ** -decimales


def lectures_gb_record(meta, ecran, config, source="record"):
    """v6 §4.7 : un écran Personal Record = 2 runs (groupes 1 et 2), RC exact, dégâts arrondis.
    Contrôle : `Total Rage Count` = RC groupe 1 + RC groupe 2 -> `sur`, sinon `a_verifier`.
    La saison (`Time Left in Season`) est contrôlée par classement.py."""
    groupes = ecran.get("groups") or {}
    rcs = [(groupes.get(g) or {}).get("rage_count") for g in (1, 2)]
    total = ecran.get("total_rage_count")
    ok = None not in rcs and total is not None and sum(rcs) == total
    pb = [] if ok else ["Total Rage Count ≠ RC groupe 1 + RC groupe 2 (ou illisible)"]
    lectures = []
    for g in (1, 2):
        rc = (groupes.get(g) or {}).get("rage_count")
        if rc is None:
            continue
        deg, pas = degats_arrondis((groupes[g]).get("damage"))
        lec = lecture_vide(meta, "gb")
        lec["notes"] += notes_alerte_reset(meta, config)
        lec.update(score=rc, damage=deg, score_source=source, exact=ok, confidence="sur" if ok else "a_verifier",
                   stage=ecran.get("stage"), t=ecran.get("t"), team=g,
                   detail={"damage_exact": False, "damage_step": pas, "total_score": ecran.get("total_score"),
                           "total_rage_count": total, "challenge_count": ecran.get("challenge_count"),
                           "time_left": ecran.get("time_left")})
        lec["notes"] += [f"contrôle Personal Record : {p}" for p in pb]
        lectures.append(lec)
    return lectures


def lecture_hotm(meta, ecran, config, source="video-complete"):
    """SPEC §3.2 : `클리어` + `증명 보너스` = `합산 결과` = `이번 기록` -> sûr. `증명 보너스` = niveau × 100 :
    alerte seulement. Jamais `기존 기록`. La porte vient du titre (l'écran de composition n'est pas lu ici)."""
    clear, bonus, total, record = (ecran.get(k) for k in ("clear", "proof_bonus", "total", "record"))
    score = record if record is not None else total
    if score is None:
        return None
    ok = None not in (clear, bonus, total, record) and clear + bonus == total == record
    lec = lecture_vide(meta, "hotm")
    lec["notes"] += notes_alerte_reset(meta, config)
    porte = lire_porte(meta.get("title") or "")
    lec.update(score=score, score_source=source, exact=ok, confidence="sur" if ok else "a_verifier",
               stage=ecran.get("stage"), t=ecran.get("t"), gate=porte["number"] if porte else None,
               detail={"clear": clear, "proof_bonus": bonus, "proof_level": ecran.get("proof_level")})
    if not ok:
        lec["notes"].append("contrôle HOTM : clear + preuve ≠ total ≠ 이번 기록 (ou illisible)")
    niveau = ecran.get("proof_level")
    if ok and niveau is not None and bonus != niveau * 100:
        lec["notes"].append(f"alerte : bonus de preuve {bonus} ≠ niveau {niveau} × 100")
    return lec


def lecture_poc(meta, ecran, config, source="video-complete"):
    """SPEC §3.2 : `이번 기록` = SJW + successeur + chasseurs 1, 2 et 3. Sans les 5 composants lus : a_verifier."""
    record = ecran.get("record")
    if record is None:
        return None
    parts = [ecran.get("sjw"), ecran.get("successor"), *(ecran.get("hunters") or [])]
    ok = len(parts) == 5 and None not in parts and sum(parts) == record
    lec = lecture_vide(meta, "poc")
    lec["notes"] += notes_alerte_reset(meta, config)
    lec.update(score=record, score_source=source, exact=ok, confidence="sur" if ok else "a_verifier",
               stage=ecran.get("stage"), t=ecran.get("t"), team=ecran.get("team"),
               detail={"sjw": ecran.get("sjw"), "successor": ecran.get("successor"), "hunters": ecran.get("hunters")})
    if not ok:
        lec["notes"].append("contrôle POC non fait : composants (SJW, successeur, 3 chasseurs) non lus ou somme différente")
    return lec
