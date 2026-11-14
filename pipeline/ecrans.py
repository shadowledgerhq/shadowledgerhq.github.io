"""Écrans lus -> entrées de `_lectures.json`, avec les contrôles de la spec (§3.1, §3.2, §4.7).

La lecture des images (OCR, recadrages) est [EN ATTENTE] : ces fonctions reçoivent les valeurs déjà lues
(dict `ecran`) et produisent les lectures que `classement.py` consomme. Une valeur illisible vaut None :
la lecture reste `a_verifier`, jamais une valeur inventée.

- lecture_bot(meta, ecran, config)          écran `Results` du BOT (v4) 
- lecture_gb_results(meta, ecran, config)   écran `Results` du GB (v5)
- lectures_gb_record(meta, ecran, config)   écran `Guild Boss` > `Personal Record` du GB (v6) : 2 lectures (groupes 1 et 2)
- lecture_hotm(meta, ecran, config)         écran RESULT du HOTM : clear + preuve = total = 이번 기록
- lecture_poc(meta, ecran, config)          écran RESULT du POC : 이번 기록 (`sur` seulement si les 5 composants sont lus et égaux)
"""
import re

from hotm_ecran import lire_porte
from bot_saison import NOTE_CHALLENGE, lire_saison_semaine, titre_challenge
from tri1 import lecture_vide, notes_alerte_reset


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
    lec["bot_season_week"] = lire_saison_semaine(meta.get("title"), config)
    if titre_challenge(meta.get("title"), config):  # v10 : ancien mode supprimé
        lec["notes"].append(NOTE_CHALLENGE)
    return lec


def controle_gb_results(player_score, hunter_ranks, final_score, successor=0, successeur_present=False):
    """v5 : `Player's Score` + les 6 `Hunter Rank` = `Final Score`. Avec la ligne « Successor Score » (v15, vue en
    coréen) elle entre dans la somme. Le RC n'a pas de contrôle arithmétique."""
    if player_score is None or final_score is None or not hunter_ranks or len(hunter_ranks) != 6 or None in hunter_ranks:
        return False, ["écran GB illisible (Player's Score, Hunter Rank ou Final Score)"]
    if successeur_present and successor is None:
        return False, ["Successor Score illisible"]
    somme = player_score + (successor or 0) + sum(hunter_ranks)
    return somme == final_score, ([] if somme == final_score else [f"somme {somme} ≠ Final Score {final_score}"])


def lecture_gb_results(meta, ecran, config, source="video-complete"):
    """Écran Results GB (une image). Sans `Rage Count` lu : lecture PARTIELLE (`score: None`,
    `detail.ecran: results_partiel`), jamais classée par elle-même. Les lectures d'une même animation sont
    fusionnées champ par champ par `ocr_ecrans.fusionner_results` (qui contrôle aussi la run)."""
    partielle = ecran.get("rage_count") is None
    rangs = list(ecran.get("hunter_ranks") or [None] * 6)
    rangs = (rangs + [None] * 6)[:6]
    ok, pb = controle_gb_results(ecran.get("player_score"), rangs, ecran.get("final_score"),
                                 ecran.get("successor_score", 0), ecran.get("successeur_present", False))
    lec = lecture_vide(meta, "gb")
    lec["notes"] += notes_alerte_reset(meta, config)
    lec["notes"] += ecran.get("notes_extra", [])
    lec.update(score=ecran.get("rage_count"), damage=ecran.get("final_score"), score_source=source, exact=ok and not partielle,
               confidence="sur" if ok and not partielle else "a_verifier", stage=ecran.get("stage"), t=ecran.get("t"), team=None,
               detail={"damage_exact": True, "play_time": ecran.get("play_time"),
                       "new_record": bool(ecran.get("new_record")), "player_score": ecran.get("player_score"),
                       "hunter_ranks": rangs, "hunter_ranks_lus": sum(r is not None for r in rangs), "n_images": 1,
                       "successor_score": ecran.get("successor_score"), "successeur_present": bool(ecran.get("successeur_present"))})
    if partielle:
        lec["detail"]["ecran"] = "results_partiel"
    elif not ok:
        lec["notes"] += [f"contrôle GB : {p}" for p in pb]
    return lec


def controle_results_sans_hunter_rank(lec, hud, config, joueur_optionnel=False, infos=None):
    """v12, durci v13 §3.1 : contrôle de remplacement quand les 6 `Hunter Rank` ne sont pas tous lus. Retourne
    (ok, problèmes). Conditions : (1) boss, `Final Score`, `Rage Count` et `Play Time` lus ; (2) `Rage Count`
    identique sur ≥ 2 images ; (3) `Final Score` dans [Points HUD ; Points × (1 + `gb.hud_tolerance`)] (HUD à chrono
    ≤ 5 s) ou, sans HUD, identique sur ≥ 2 images ; (4) `Player's Score` + `Hunter Rank` lus < `Final Score`, et les
    `Hunter Rank` lus décroissent du rang 1 au rang 6 (v14 : sans HUD, 3 `Hunter Rank` lus au moins).
    v19 (SPEC v18, repli assoupli) : la condition 4 est NON bloquante si le HUD confirme le `Final Score` (condition 3
    par les Points) ET si le `Rage Count` est lu à l'identique sur ≥ 3 images sans aucune lecture discordante (étapes
    d'un compteur animé non comptées) ET si les conditions 1 et 2 sont remplies ; la note `Hunter Rank incohérents
    ignorés (HUD)` est ajoutée à `infos` si la condition 4 était en défaut. Sans HUD, la condition 4 reste obligatoire."""
    d, pb, pb4 = lec.get("detail") or {}, [], []
    final = lec.get("damage")
    for nom, valeur in (("boss", lec.get("stage")), ("Final Score", final), ("Rage Count", lec.get("score")),
                        ("Play Time", d.get("play_time"))):
        if valeur is None:
            pb.append(f"{nom} illisible")
    if d.get("rc_images", 1) < 2:
        pb.append("Rage Count lu sur une seule image")
    points = (hud or {}).get("damage")
    hud_confirme = False
    if points is not None and final is not None:
        tol = (config.get("gb") or {}).get("hud_tolerance", 0.02)
        if not points <= final <= points * (1 + tol):
            pb.append(f"Final Score {final} hors de [Points HUD {points} ; × {1 + tol:g}]")
        else:
            hud_confirme = True
    elif d.get("final_images", 1) < 2:
        pb.append("Final Score lu sur une seule image, sans HUD de fin de run")
    rangs = [r for r in (d.get("hunter_ranks") or []) if r is not None]
    if points is None and len(rangs) < 3:       # v14 : sans HUD, la condition 4 demande au moins 3 Hunter Rank lus
        pb4.append(f"{len(rangs)} Hunter Rank lu(s) (3 au moins sans HUD de fin de run)")
    joueur = d.get("player_score")
    if final is not None:
        if joueur is None:
            if not (joueur_optionnel and points is not None):   # v17 : repli à 6 rangs lus, Final Score confirmé par le HUD
                pb4.append("Player's Score illisible")
        elif joueur + (d.get("successor_score") or 0) + sum(rangs) >= final:
            pb4.append("Player's Score + Hunter Rank lus ≥ Final Score")
    if any(a < b for a, b in zip(rangs, rangs[1:])):
        pb4.append("Hunter Rank lus non décroissants")
    if pb4 and not pb and hud_confirme:
        discordantes = len((d.get("votes") or {}).get("rage_count") or []) > 1
        if d.get("rc_images", 1) >= 3 and not discordantes:
            if infos is not None:
                infos.append("Hunter Rank incohérents ignorés (HUD)")
            pb4 = []
    pb += pb4
    return not pb, pb


def lecture_gb_combat(meta, ecran, config, source="video-complete"):
    """v12 §3.1 : HUD du combat GB (`Points` + `Boss Rage Count xN` + chrono sur la même image). Le HUD n'est
    JAMAIS un score : lecture sans score (`score: None`, ignorée par le classement), qui garde le `Boss Rage Count`
    (information, `hud_rage_count`) et les `Points` (= `Final Score` en cours, hypothèse). Sans chrono lisible, ou sans compteur
    ni `Points` : ignorée (le compteur peut manquer dans une langue dont le libellé est mal lu). Les lectures d'une même run sont regroupées par `ocr_ecrans.regrouper_hud`."""
    rc, chrono = ecran.get("rage_count"), ecran.get("chrono")
    if chrono is None or (rc is not None and not 0 <= rc <= 500) or (rc is None and (not ecran.get("rage_optionnel") or ecran.get("points") is None)):
        return None             # chrono illisible, ou compteur illisible (sauf langue à libellé mal lu : `rage_optionnel`) : HUD ignoré
    lec = lecture_vide(meta, "gb")
    lec.update(score=None, score_source=None, exact=False, confidence="a_verifier", stage=ecran.get("stage"),
               t=ecran.get("t"), team=None,
               detail={"ecran": "combat", "hud_points": ecran.get("points"), "chrono_hud": chrono,
                       "hud_rage_count": rc})
    return lec


def lecture_gb_combat_sans_chrono(meta, ecran, config, source="video-complete"):
    """v20 (SPEC v19) : HUD du combat GB dont le chrono est illisible mais dont les `Points` sont plausibles. Lecture sans
    score (`detail.ecran == "combat_sans_chrono"`), conservée ; `ocr_ecrans.regrouper_hud` la rattache à la run dont un HUD au
    chrono lu ≤ 5 s la précède de 2 s au plus (chrono HUD déduit). Sans Points plausibles : ignorée (None)."""
    if ecran.get("points") is None:
        return None
    lec = lecture_vide(meta, "gb")
    lec.update(score=None, score_source=None, exact=False, confidence="a_verifier", stage=ecran.get("stage"),
               t=ecran.get("t"), team=None,
               detail={"ecran": "combat_sans_chrono", "hud_points": ecran.get("points"), "hud_rage_count": ecran.get("rage_count")})
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
    """v6 §4.7 : un écran Personal Record = 1 ou 2 runs (groupes 1 et 2), RC exact, dégâts arrondis.
    Contrôle : `Total Rage Count` = somme des RC des groupes joués -> `sur`, sinon `a_verifier`.
    v15-v16 : `Group N  No history` = groupe sans run cette semaine (pas une lecture manquante) ; avec un seul groupe
    joué, `Total Score` (exact) EST le `Final Score` de la run (`damage_source: record`).
    La saison (`Time Left in Season`) est contrôlée par classement.py."""
    groupes = ecran.get("groups") or {}
    joues = [g for g in (1, 2) if not (groupes.get(g) or {}).get("no_history")]
    rcs = [(groupes.get(g) or {}).get("rage_count") for g in joues]
    total = ecran.get("total_rage_count")
    total_score, incoherent = ecran.get("total_score"), None
    if total_score is not None:       # recoupement : Total Score ≈ somme des dégâts affichés des groupes joués (arrondi ou tronqué)
        lus = [degats_arrondis((groupes.get(g) or {}).get("damage")) for g in joues]
        if lus and all(v is not None for v, _ in lus):
            somme, pas = sum(v for v, _ in lus), sum(p_ or 0 for _, p_ in lus)
            if not -0.5 * pas - 1 <= total_score - somme <= 1.5 * pas + 1:
                incoherent, total_score = f"Total Score {total_score} incohérent avec les dégâts des groupes", None
    ok = bool(joues) and None not in rcs and total is not None and sum(rcs) == total
    pb = [] if ok else ["Total Rage Count ≠ somme des RC des groupes joués (ou illisible)"]
    note_total = [f"contrôle Personal Record : {incoherent}"] if incoherent else []   # Total Score écarté, les RC restent contrôlés
    seul = ok and len(joues) == 1 and total_score is not None    # sûr seulement : le Total Score lu à l'image entière peut être faux (« B4 » pour « 64 »)
    lectures = []
    for g in joues:
        rc = (groupes.get(g) or {}).get("rage_count")
        if rc is None:
            continue
        deg, pas = degats_arrondis((groupes[g]).get("damage"))
        lec = lecture_vide(meta, "gb")
        lec["notes"] += notes_alerte_reset(meta, config)
        lec["notes"] += ecran.get("notes_extra", [])
        detail = {"damage_exact": False, "damage_step": pas, "total_score": total_score,
                  "total_rage_count": total, "challenge_count": ecran.get("challenge_count"),
                  "time_left": ecran.get("time_left")}
        if seul:      # un seul groupe joué : le Total Score exact est le Final Score de la run
            deg, pas = total_score, None
            detail.update(damage_exact=True, damage_step=None, damage_source="record")
        lec.update(score=rc, damage=deg, score_source=source, exact=ok, confidence="sur" if ok else "a_verifier",
                   stage=ecran.get("stage"), t=ecran.get("t"), team=g, detail=detail)
        lec["notes"] += [f"contrôle Personal Record : {p}" for p in pb] + note_total
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
