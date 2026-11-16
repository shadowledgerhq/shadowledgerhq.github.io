"""Rapport du PC : `data/runs/<semaine>/_rapport_pc.md` (critère de gel n° 3, demande de la discussion 1).

Un bloc daté par passage PC, ajouté à la suite des précédents (jamais effacés). Seul le PC écrit ce fichier : le passage
GitHub (`etape1.ecrire_rapport`) n'y touche pas, il recopie seulement le dernier bloc en tête de `_rapport.md`.
Un même passage qui réécrit son bloc (ex. échec du push après le rapport) remplace son propre bloc, repéré par un
marqueur `<!-- passage-pc <passage> <instant ISO> -->`, jamais celui d'un autre passage."""
import re
from datetime import datetime, timezone

from semaine import PARIS

DEBUT_MARQUEUR = "<!-- passage-pc "
ENTETE = ("# Rapport du PC — semaine {week}\n\nUn bloc par passage PC, le plus récent en bas, jamais effacé. Le passage GitHub "
          "ne modifie pas ce fichier : il recopie le dernier bloc en tête de `_rapport.md`.\n")


def chemin(week):
    return f"runs/{week}/_rapport_pc.md"


def marqueur(passage, instant):
    return f"{DEBUT_MARQUEUR}{passage} {instant.isoformat()} -->"


def titre(passage, instant):
    return f"## Passage {passage} — {instant.astimezone(PARIS).strftime('%Y-%m-%d %H:%M')} (Paris)"


_MARQ = re.compile(rf"(?m)^{re.escape(DEBUT_MARQUEUR)}(\S+) (\S+) -->$")


def _instant(texte_iso):
    try:
        t = datetime.fromisoformat(texte_iso)
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _morceaux(texte):
    """[(passage, instant, texte du bloc marqueur compris)] dans l'ordre du fichier."""
    sortie = []
    for m in re.split(rf"(?m)^(?={re.escape(DEBUT_MARQUEUR)})", texte or ""):
        mq = _MARQ.match(m)
        if mq:
            sortie.append((mq.group(1), _instant(mq.group(2)), m.rstrip("\n") + "\n"))
    return sortie


def _trier(morceaux):
    """v29 : blocs triés par horodatage (stable) : un passage qui finit après un autre ne passe plus avant lui."""
    return sorted(morceaux, key=lambda x: x[1])


def ecrire_bloc(d, week, passage, instant, lignes):
    """Ajoute (ou met à jour s'il existe déjà pour ce passage) le bloc du passage ; tous les blocs sont triés par horodatage
    (v29). `lignes` = lignes de l'en-tête d'état (`pc.entete_etat`), notes comprises. Retourne le texte du bloc."""
    p = d.data / chemin(week)
    existant = p.read_text(encoding="utf-8") if p.exists() else ENTETE.format(week=week)
    m = marqueur(passage, instant)
    bloc = "\n".join([m, titre(passage, instant), ""] + list(lignes)).rstrip() + "\n"
    morceaux = [x for x in _morceaux(existant) if marqueur(x[0], x[1]) != m and not x[2].startswith(m)]
    morceaux.append((passage, instant, bloc))
    entete = existant.split(DEBUT_MARQUEUR, 1)[0].rstrip("\n") if DEBUT_MARQUEUR in existant else existant.rstrip("\n")
    d.ecrire(chemin(week), entete + "\n\n" + "\n".join(x[2] for x in _trier(morceaux)))
    return bloc


def blocs(texte):
    """Blocs d'un fichier `_rapport_pc.md`, du plus ancien au plus récent par horodatage (marqueur retiré)."""
    return [x[2].split("\n", 1)[1].strip("\n") for x in _trier(_morceaux(texte))]


def dernier_bloc(d, week):
    """Lignes du dernier bloc PC de la semaine ([] s'il n'y en a pas)."""
    p = d.data / chemin(week)
    if not p.exists():
        return []
    b = blocs(p.read_text(encoding="utf-8"))
    return b[-1].split("\n") if b else []


def _bloc_couvert(lignes):
    """Le bloc indique « Top 10 couvert : oui » et ses erreurs bloquantes sont seulement l'anti-bot."""
    texte = "\n".join(lignes)
    if "Top 10 couvert : oui" not in texte:
        return False
    m = re.search(r"(?m)^- Erreurs bloquantes : (.*)$", texte)
    erreurs = [] if not m or m.group(1).strip() == "aucune" else m.group(1).split(" ; ")
    return all(e.startswith("anti-bot YouTube") for e in erreurs)


def critere_gel3(d, week, passage, instant, top10_n, bloquantes):
    """Critère de gel n° 3 (SPEC v29) : 2 passages planifiés de suite (les plus récents) dont le bloc indique « Top 10 couvert :
    oui », sans autre erreur bloquante que l'anti-bot. Retourne le texte de la ligne du bloc (le bloc courant compte)."""
    p = d.data / chemin(week)
    autres = [x for x in _trier(_morceaux(p.read_text(encoding="utf-8") if p.exists() else ""))
              if not (x[0] == passage and x[1] == instant)]
    ok_courant = top10_n == 0 and all(b.startswith("anti-bot YouTube") for b in bloquantes)
    suite = [ok_courant]
    for pas, _, texte in reversed([x for x in autres if x[0] in ("pc-daily", "pc-weekly") and x[1] < instant]):
        suite.append(_bloc_couvert(texte.split("\n")))
    n = 0
    for ok in suite:
        if not ok:
            break
        n += 1
    return f"{min(n, 2)}/2 passage(s) planifié(s) de suite avec top 10 couvert" + (" — atteint (reste à décider `pc.geler`)" if n >= 2 else "")
