"""GB : Rage Count, groupes, écran Personal Record (SPEC_ETAPE1 §4.1 et §4.7, v5-v6).

Fonctions pures, utilisées par classement.py :
- attribuer_groupes(runs)  -> v30 : retire le Personal Record (jamais classé) ; il attribue un groupe aux runs `Results` de même RC
- cle_run(run)             -> (RC, dégâts) : « meilleure run » d'un groupe
- somme_degats(runs)       -> départage des égalités de RC total
- saison_precedente(...)   -> Personal Record d'une saison précédente (Time Left in Season)
"""
import re
from datetime import timedelta

from semaine import parse_iso


def degats(run):
    """Dégâts pour le départage : jamais ceux du HUD (provisoires, v12) ; seuls `Final Score`, `Total Score` et les
    dégâts lus dans un titre comptent."""
    if (run.get("detail") or {}).get("damage_source") == "hud":
        return 0
    return run.get("damage") or 0


def cle_run(run):
    """« Meilleure run » d'un groupe : RC le plus élevé, puis dégâts (`Final Score`)."""
    return (run["score"], degats(run))


def somme_degats(runs):
    """Départage au GB : somme des dégâts des 2 runs. Si les 2 runs viennent du même Personal Record,
    le `Total Score` (exact) est utilisé plutôt que la somme des dégâts arrondis par groupe."""
    totaux = {(r.get("detail") or {}).get("total_score") for r in runs if r.get("score_source") == "record"}
    if len(runs) == 2 and all(r.get("score_source") == "record" for r in runs) and len(totaux) == 1 and None not in totaux:
        return totaux.pop()
    return sum(degats(r) for r in runs)


def _memes_degats_arrondis(run, record):
    pas = (record.get("detail") or {}).get("damage_step")
    if not (pas and run.get("damage") and record.get("damage")):
        return False
    return abs(run["damage"] - record["damage"]) <= pas / 2 + 1e-6


def _est_results(r):
    return r.get("score_source") in ("debut-fin", "video-complete") and (r.get("detail") or {}).get("ecran") != "combat"


NOTE_RC_CONFIRME = "RC confirmé par le Personal Record ; contrôle de somme impossible (Player's Score illisible)"


def _rc_confirme_par_record(run, records):
    """SPEC v32 §3.2 : le RC d'une run filmée est `sûr` même si le contrôle de somme est sauté (Player's Score en conflit ou
    illisible), à 3 conditions : (a) RC lu sur ≥ 2 images, sans conflit de lecture (égalité de votes) ; (b) RC égal à celui d'UN
    groupe d'un Personal Record `sûr` de la même vidéo (Total Rage Count = somme des groupes ; `Time Left` déjà contrôlé par
    controler_saison_record) ; (c) aucun RC contradictoire dans le titre (note `écart titre/écran`) ni dans le HUD de fin (RC du
    HUD > RC du Results : un compteur ne décroît pas). Jamais de valeur déduite : les dégâts restent le Final Score voté,
    `damage_exact` passe à false. Une somme fausse (note `contrôle GB`) n'est jamais contournée."""
    if run.get("confidence") == "sur":
        return run
    notes, d = run.get("notes", []), dict(run.get("detail") or {})
    if not any(n == "conflit de lecture : player_score" for n in notes) and d.get("player_score") is not None:
        return run                                  # le contrôle de somme n'est pas « sauté » pour ce motif
    if any(n.startswith(("conflit de lecture : rage_count", "contrôle GB", "écart titre/écran")) for n in notes):
        return run
    if (d.get("rc_images") or 0) < 2:
        return run
    sains = [x for x in records if x.get("team") in (1, 2) and x.get("confidence") == "sur"]
    total = next(((x.get("detail") or {}).get("total_rage_count") for x in sains
                  if (x.get("detail") or {}).get("total_rage_count") is not None), None)
    if total is None or total != sum(x["score"] for x in sains) or len({x["team"] for x in sains}) != len(sains):
        return run
    hud = d.get("hud_rage_count")
    if hud is not None and hud > run["score"]:
        return run
    d["damage_exact"] = False
    return {**run, "confidence": "sur", "exact": False, "detail": d, "notes": notes + [NOTE_RC_CONFIRME]}


NOTE_RC_HUD = "RC du Results ({rc}) < RC du HUD ({hud}) : un compteur ne décroît pas, lecture à vérifier"


def rc_contredit_par_hud(run):
    """v37 : un Rage Count ne décroît pas. Un Results `sûr` dont le RC est inférieur au RC lu dans le HUD (`detail.hud_rage_count`,
    maximum des HUD de la vidéo) est rétrogradé `a_verifier` (cas XVzx3w07JPo : Results lu 7 sur 5 images, vrai 177, HUD 148).
    Le HUD ne corrige jamais la valeur : seul le doute est signalé."""
    d = run.get("detail") or {}
    hud = d.get("hud_rage_count")
    if run.get("confidence") != "sur" or not _est_results(run) or hud is None or run.get("score") is None or hud <= run["score"]:
        return run
    return {**run, "confidence": "a_verifier", "exact": False,
            "notes": list(run.get("notes", [])) + [NOTE_RC_HUD.format(rc=run["score"], hud=hud)]}


def attribuer_groupes(runs):
    """SPEC v30 §4.7 : le Personal Record ne classe plus aucune run. Il sert seulement à attribuer un groupe (`team`) à une run
    `Results` de la MÊME vidéo : si le RC du Results est égal au RC d'UN SEUL groupe du Personal Record contrôlé (`sûr`), ce groupe
    est attribué (note). Total Score, Total Rage Count et dégâts arrondis du record ne servent plus. Retourne
    (runs sans les lignes du Personal Record, vidéos dont le Personal Record est seul : aucun Results lu)."""
    records = [r for r in runs if r.get("score_source") == "record"]
    sortie = []
    for r in runs:
        if r.get("score_source") == "record":
            continue
        r = rc_contredit_par_hud(r)
        if _est_results(r) and r.get("team") is None:
            memes = [x for x in records if x["video_id"] == r["video_id"] and x.get("team") in (1, 2)
                     and x.get("confidence") == "sur" and x["score"] == r["score"]]
            if len(memes) == 1:
                g = memes[0]["team"]
                r = {**r, "team": g, "notes": list(r.get("notes", [])) + [f"groupe {g} d'après le Personal Record (RC égal)"]}
                r = _rc_confirme_par_record(r, [x for x in records if x["video_id"] == r["video_id"]])
        sortie.append(r)
    avec_results = {r["video_id"] for r in sortie if _est_results(r)}
    return sortie, sorted({x["video_id"] for x in records} - avec_results)


def temps_restant(texte):
    """`Time Left in Season` (`6d 9h`, `6d 9h 20m`) -> timedelta, ou None si illisible."""
    m = re.fullmatch(r"\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?\s*", texte or "", re.IGNORECASE)
    if not m or not any(m.groups()):
        return None
    j, h, mi = (int(x or 0) for x in m.groups())
    return timedelta(days=j, hours=h, minutes=mi)


def plus_petite_unite(texte):
    """Plus petite unité affichée dans `Time Left in Season` : `m` (minutes), `h` (heures), `d` (jours seulement),
    ou None si illisible. `6d 9h` -> h ; `6d` -> d ; `6d 9h 20m` -> m."""
    m = re.fullmatch(r"\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?\s*", texte or "", re.IGNORECASE)
    if not m or not any(m.groups()):
        return None
    return "m" if m.group(3) else "h" if m.group(2) else "d"


TOLERANCES_DEFAUT = {"d": 24 * 60, "h": 60, "m": 1}


def tolerances(config_gb):
    """Marges en minutes selon l'unité (SPEC §4.7, v7) : heures -> `record_tolerance_minutes` (60),
    jours seulement -> `record_tolerance_jours_minutes` (24 h), minutes -> `record_tolerance_min_minutes` (1 min)."""
    c = config_gb or {}
    return {"d": c.get("record_tolerance_jours_minutes", 24 * 60), "h": c.get("record_tolerance_minutes", 60),
            "m": c.get("record_tolerance_min_minutes", 1)}


def saison_precedente(time_left, publie, reset, marges=None):
    """§4.7 : moment de la capture = prochain reset − temps restant. S'il tombe APRÈS `published_at` plus la
    marge (qui dépend de la plus petite unité affichée : le temps restant est tronqué à cette unité), le record
    date de la saison précédente. Retourne True / False, ou None si `time_left` est illisible."""
    unite = plus_petite_unite(time_left) if not isinstance(time_left, timedelta) else "m"
    reste = time_left if isinstance(time_left, timedelta) else temps_restant(time_left)
    if reste is None or unite is None:
        return None
    marge = timedelta(minutes=(marges or TOLERANCES_DEFAUT)[unite])
    return parse_iso(reset) - reste > parse_iso(publie) + marge


def appliquer_hud(lectures):
    """v12 : les dégâts provisoires du HUD (lectures sans score, `detail.ecran == "combat"`, `damage` = dernier `Points`
    à chrono ≤ 5 s) sont attachés à la lecture de score de la même vidéo (titre, description, sous-titres) quand il n'y
    en a qu'une, sans dégâts, et qu'aucun écran Results ni Personal Record n'est lu pour cette vidéo. Le
    `Boss Rage Count` du HUD (`hud_rage_count`) est ajouté pour information. Retourne les lectures de score modifiées
    (copies) ; les lectures du HUD ne sont jamais classées."""
    huds = [l for l in lectures if l["mode"] == "gb" and (l.get("detail") or {}).get("ecran") == "combat"]
    scores = [l for l in lectures if l.get("score") is not None]
    sortie = []
    for l in scores:
        if l["mode"] != "gb":
            sortie.append(l)
            continue
        meme = [h for h in huds if h["video_id"] == l["video_id"]]
        ecran = [x for x in scores if x["video_id"] == l["video_id"] and x["mode"] == "gb"
                 and x["score_source"] in ("debut-fin", "video-complete", "record")]
        texte = [x for x in scores if x["video_id"] == l["video_id"] and x["mode"] == "gb" and x not in ecran]
        if l["score_source"] in ("debut-fin", "video-complete", "record") or len(meme) != 1 or ecran or len(texte) != 1:
            sortie.append(l)
            continue
        h, d = meme[0], dict(l.get("detail") or {})
        d["hud_rage_count"] = h["detail"]["hud_rage_count"]
        if l.get("damage") is None and h.get("damage") is not None:
            l = {**l, "damage": h["damage"]}
            d.update(damage_exact=False, damage_source="hud")
        sortie.append({**l, "detail": d})
    return sortie
