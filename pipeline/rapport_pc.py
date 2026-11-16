"""Rapport du PC : `data/runs/<semaine>/_rapport_pc.md` (critère de gel n° 3, demande de la discussion 1).

Un bloc daté par passage PC, ajouté à la suite des précédents (jamais effacés). Seul le PC écrit ce fichier : le passage
GitHub (`etape1.ecrire_rapport`) n'y touche pas, il recopie seulement le dernier bloc en tête de `_rapport.md`.
Un même passage qui réécrit son bloc (ex. échec du push après le rapport) remplace son propre bloc, repéré par un
marqueur `<!-- passage-pc <passage> <instant ISO> -->`, jamais celui d'un autre passage."""
import re

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


def ecrire_bloc(d, week, passage, instant, lignes):
    """Ajoute (ou met à jour s'il existe déjà pour ce passage) le bloc du passage. `lignes` = lignes de l'en-tête d'état
    (`pc.entete_etat`), notes comprises. Retourne le texte du bloc."""
    p = d.data / chemin(week)
    existant = p.read_text(encoding="utf-8") if p.exists() else ENTETE.format(week=week)
    m = marqueur(passage, instant)
    bloc = "\n".join([m, titre(passage, instant), ""] + list(lignes)).rstrip() + "\n"
    if m in existant:
        debut = existant.index(m)
        suite = existant.find(DEBUT_MARQUEUR, debut + len(m))
        existant = existant[:debut] + bloc + ("\n" + existant[suite:] if suite != -1 else "")
    else:
        existant = existant.rstrip("\n") + "\n\n" + bloc
    d.ecrire(chemin(week), existant)
    return bloc


def blocs(texte):
    """Blocs d'un fichier `_rapport_pc.md`, du plus ancien au plus récent (marqueur retiré)."""
    morceaux = re.split(rf"(?m)^(?={re.escape(DEBUT_MARQUEUR)})", texte or "")
    return [m.split("\n", 1)[1].strip("\n") for m in morceaux if m.startswith(DEBUT_MARQUEUR)]


def dernier_bloc(d, week):
    """Lignes du dernier bloc PC de la semaine ([] s'il n'y en a pas)."""
    p = d.data / chemin(week)
    if not p.exists():
        return []
    b = blocs(p.read_text(encoding="utf-8"))
    return b[-1].split("\n") if b else []
