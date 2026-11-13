"""BOT : cycle de saison et contrôle de la semaine par le titre `S<n>-<w>` (docs/SPEC_ETAPE1.md §4.6, v10).
Une saison = `semaines_jeu` (4) semaines de jeu + `semaines_calcul` (1) semaine de calcul, sans classement.
Référence : `config.bot.saison_ref`. Un seul classement BOT par semaine (`bot.json`)."""
import re
from collections import defaultdict
from datetime import date

RX = re.compile(r"(?<![A-Za-z0-9])S(\d+)-(\d)(?![A-Za-z0-9])", re.IGNORECASE)
NOTE_CALCUL = "semaine de calcul : run de la semaine précédente ?"
NOTE_CHALLENGE = "challenge ? (mode supprimé)"


def _cfg(config):
    b = config.get("bot") or {}
    return b.get("saison_ref"), b.get("semaines_jeu", 4), b.get("semaines_calcul", 1)


def lire_saison_semaine(titre, config=None):
    """'BOT S20-4 …' -> 'S20-4' ; sinon None. Semaine hors 1..`semaines_jeu` ignorée."""
    m = RX.search(titre or "")
    jeu = _cfg(config or {})[1]
    if not m or not 1 <= int(m.group(2)) <= jeu:
        return None
    return f"S{int(m.group(1))}-{int(m.group(2))}"


def titre_challenge(titre, config):
    """v10 : ancien mode supprimé. Mots de `config.bot.challenge` (mot entier si ASCII)."""
    bas = (titre or "").lower()
    for mot in (config.get("bot") or {}).get("challenge", []):
        mot = mot.lower()
        if (re.search(rf"(?<![a-z0-9]){re.escape(mot)}(?![a-z0-9])", bas) if mot.isascii() else mot in bas):
            return True
    return False


def position(week, config, decalage=0):
    """('jeu', saison, semaine) ou ('calcul', saison, None) pour la semaine `week` (+ `decalage` semaines)."""
    ref, jeu, calcul = _cfg(config)
    if not ref:
        return None
    cycle = jeu + calcul
    ecart = (date.fromisoformat(week) - date.fromisoformat(ref["week"])).days // 7 + decalage
    decale = ref["semaine_saison"] - 1 + ecart
    saison, pos = ref["saison"] + decale // cycle, decale % cycle
    return ("jeu", saison, pos + 1) if pos < jeu else ("calcul", saison, None)


def attendue(week, config):
    """(saison, semaine) attendue, ou None (semaine de calcul, ou pas de référence)."""
    p = position(week, config)
    return (p[1], p[2]) if p and p[0] == "jeu" else None


def precedente(week, config):
    """Dernière semaine de jeu AVANT `week`, par-dessus une éventuelle semaine de calcul."""
    for d in range(1, 1 + _cfg(config)[2] + 1):
        p = position(week, config, -d)
        if p and p[0] == "jeu":
            return p[1], p[2]
    return None


def verdict(sw, week, config):
    """'confirmee' | 'precedente' | 'incoherente' | None (pas de titre lisible ou pas de référence)."""
    p = position(week, config)
    if not sw or p is None:
        return None
    lu = tuple(int(x) for x in re.fullmatch(r"S(\d+)-(\d)", sw).groups())
    if lu == precedente(week, config):
        return "precedente"
    if p[0] == "jeu" and lu == (p[1], p[2]):
        return "confirmee"
    return "incoherente"


def controler_semaine_bot(runs, week, config):
    """Modifie les runs BOT (notes, a_verifier). Retourne (runs gardées, runs de la semaine précédente,
    alertes). Jamais de rejet hors `precedente`."""
    p = position(week, config)
    calcul = p is not None and p[0] == "calcul"
    gardees, prec, ecarts, nb_calcul = [], [], defaultdict(set), set()
    for r in runs:
        if r["mode"] != "bot":
            gardees.append(r)
            continue
        v = verdict(r.get("bot_season_week"), week, config)
        if v == "precedente":
            prec.append(r)
            continue
        if any(n.startswith("challenge ?") for n in r["notes"]):
            r["confidence"] = "a_verifier"
        if calcul:
            r["confidence"] = "a_verifier"
            r["notes"].append(NOTE_CALCUL)
            nb_calcul.add(r["video_id"])
        if v == "confirmee":
            r["notes"][:] = [n for n in r["notes"] if not n.startswith("publiée juste après le reset")]
            r["notes"].append("semaine confirmée (titre)")
        elif v == "incoherente":
            r["confidence"] = "a_verifier"
            r["notes"].append(f"semaine du titre incohérente : {r['bot_season_week']}")
            ecarts[r["bot_season_week"]].add(r["video_id"])
        gardees.append(r)
    alertes = []
    if calcul:
        alertes.append(f"semaine de calcul (S{p[1]}) : {len(nb_calcul)} vidéo(s) BOT à vérifier "
                       "(run de la semaine précédente ?)")
    att = attendue(week, config)
    for sw, vids in sorted(ecarts.items()):
        if len(vids) >= 2:
            alertes.append(f"BOT : {len(vids)} vidéos donnent {sw}"
                           + (f" au lieu de S{att[0]}-{att[1]}" if att else "")
                           + " : référence saison_ref à corriger ?")
    return gardees, prec, alertes
