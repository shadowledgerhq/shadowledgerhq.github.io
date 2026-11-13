"""GB : Rage Count, groupes, écran Personal Record (SPEC_ETAPE1 §4.1 et §4.7, v5-v6).

Fonctions pures, utilisées par classement.py :
- rattacher_groupes(runs)  -> rattache les runs `Results` (groupe inconnu) à un groupe du Personal Record
- cle_run(run)             -> (RC, dégâts) : « meilleure run » d'un groupe
- somme_degats(runs)       -> départage des égalités de RC total
- saison_precedente(...)   -> Personal Record d'une saison précédente (Time Left in Season)
"""
import re
from datetime import timedelta

from semaine import parse_iso


def degats(run):
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


def rattacher_groupes(runs):
    """§4.7 : une run `Results` (team None) est rattachée à un groupe du Personal Record si
    - son RC et ses dégâts arrondis correspondent à ceux du record (même run), ou
    - son RC est égal à celui d'un seul groupe et ses dégâts sont supérieurs (nouveau record du groupe,
      cas `New Record Achieved!` : à RC égal, plus de dégâts).
    Sinon elle reste `team: None`. Retourne une copie de `runs` ; les runs rattachées gardent une note."""
    records = {r["team"]: r for r in runs if r.get("score_source") == "record" and r.get("team") in (1, 2)}
    sortie = []
    for r in runs:
        if r.get("team") is not None or r.get("score_source") == "record" or not records:
            sortie.append(r)
            continue
        memes = [g for g, rec in records.items() if rec["score"] == r["score"] and _memes_degats_arrondis(r, rec)]
        meme_rc = [g for g, rec in records.items() if rec["score"] == r["score"]]
        groupe, raison = None, None
        if len(memes) == 1:
            groupe, raison = memes[0], "même run que le Personal Record"
        elif len(meme_rc) == 1 and degats(r) > degats(records[meme_rc[0]]):
            groupe, raison = meme_rc[0], "RC égal au groupe et dégâts supérieurs au Personal Record"
        if groupe is None:
            sortie.append(r)
            continue
        r = {**r, "team": groupe, "notes": list(r.get("notes", []))}
        r["notes"].append(f"groupe {groupe} d'après le Personal Record ({raison})")
        sortie.append(r)
    return sortie


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
