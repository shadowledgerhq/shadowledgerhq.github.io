"""BOT : contrôle de la semaine par le titre `S<n>-<w>` (docs/SPEC_ETAPE1.md §4.6, v9).
Saison n, semaine w de 1 à `semaines_par_saison` (7), saisons enchaînées. Référence : `config.bot.saison_ref`."""
import re
from collections import defaultdict
from datetime import date

RX = re.compile(r"(?<![A-Za-z0-9])S(\d+)-(\d)(?![A-Za-z0-9])", re.IGNORECASE)


def lire_saison_semaine(titre):
    """'BOT S20-4 …' -> 'S20-4' ; sinon None (semaine hors 1-7 ignorée, w ≤ 7 vérifié par `attendue`)."""
    m = RX.search(titre or "")
    if not m or not 1 <= int(m.group(2)) <= 7:
        return None
    return f"S{int(m.group(1))}-{int(m.group(2))}"


def _parse(sw):
    n, w = re.fullmatch(r"S(\d+)-(\d)", sw).groups()
    return int(n), int(w)


def attendue(week, config, decalage=0):
    """(saison, semaine) attendue pour la semaine de jeu `week` (+ `decalage` semaines). None sans référence."""
    ref = (config.get("bot") or {}).get("saison_ref")
    if not ref:
        return None
    par = (config.get("bot") or {}).get("semaines_par_saison", 7)
    ecart = (date.fromisoformat(week) - date.fromisoformat(ref["week"])).days // 7 + decalage
    idx = (ref["saison"] - 1) * par + (ref["semaine_saison"] - 1) + ecart
    if idx < 0:
        return None
    return idx // par + 1, idx % par + 1


def verdict(sw, week, config):
    """'confirmee' | 'precedente' | 'incoherente' | None (pas de titre lisible ou pas de référence)."""
    att = attendue(week, config)
    if not sw or att is None:
        return None
    lu = _parse(sw)
    if lu[1] > (config.get("bot") or {}).get("semaines_par_saison", 7):
        return None
    if lu == att:
        return "confirmee"
    if lu == attendue(week, config, -1):
        return "precedente"
    return "incoherente"


def controler_semaine_bot(runs, week, config):
    """Modifie les runs BOT (notes, a_verifier). Retourne (runs gardées, runs de la semaine précédente,
    alertes). Jamais de rejet hors `precedente`."""
    gardees, precedentes, ecarts = [], [], defaultdict(set)
    for r in runs:
        sw = r.get("bot_season_week") if r["mode"] == "bot" else None
        v = verdict(sw, week, config)
        if v == "precedente":
            precedentes.append(r)
            continue
        if v == "confirmee":
            r["notes"][:] = [n for n in r["notes"] if not n.startswith("publiée juste après le reset")]
            r["notes"].append("semaine confirmée (titre)")
        elif v == "incoherente":
            r["confidence"] = "a_verifier"
            r["notes"].append(f"semaine du titre incohérente : {sw}")
            ecarts[sw].add(r["video_id"])
        gardees.append(r)
    alertes = [f"BOT : {len(vids)} vidéos donnent {sw} au lieu de S{attendue(week, config)[0]}-"
               f"{attendue(week, config)[1]} : référence saison_ref à corriger ?"
               for sw, vids in sorted(ecarts.items()) if len(vids) >= 2]
    return gardees, precedentes, alertes
