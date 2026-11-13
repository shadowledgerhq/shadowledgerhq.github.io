"""Tri 1 : score provisoire dans le texte (titre, description, sous-titres).
Référence : docs/SPEC_ETAPE1.md §2. Tout score trouvé ici est provisoire :
exact false, confidence a_verifier ; la vidéo continue aux tris suivants."""
import re

from hotm_ecran import lire_porte
from scores import NON_GERE, extraire

SOURCES_TEXTE = ("titre", "description", "sous-titres")


def lecture_vide(meta, mode):
    """Squelette d'une entrée de data/runs/<semaine>/_lectures.json."""
    return {
        "video_id": meta["video_id"],
        "channel_id": meta["channel_id"],
        "channel_title": meta.get("channel_title", ""),
        "published_at": meta["published_at"],
        "lang": meta.get("lang"),
        "mode": mode,
        "bot_variant": None,
        "gate": None,
        "hunter_mode": None,
        "t": None,
        "stage": None,
        "team": None,
        "score": None,
        "score_source": None,
        "exact": False,
        "confidence": "a_verifier",
        "detail": {},
        "notes": [],
    }


def variante_bot(titre, config):
    """v3 (SPEC §4.6) : variante BOT d'après le titre : `challenge`, `season` ou None (illisible).
    Mots dans config.bot_variante_mots [À CONFIRMER] ; les deux à la fois = ambigu = None ;
    challenge est cherché en premier (variante la plus spécifique) seulement s'il est seul."""
    bas = (titre or "").lower()
    trouve = {v for v, mots in config.get("bot_variante_mots", {}).items()
              if any(_mot_entier(m.lower(), bas) for m in mots)}
    return trouve.pop() if len(trouve) == 1 else None


def _mot_entier(mot, texte):
    if mot.isascii():
        return re.search(rf"(?<![a-z0-9]){re.escape(mot)}(?![a-z0-9])", texte) is not None
    return mot in texte


def lectures_texte(meta, textes, config):
    """`textes` : liste de (source, texte) dans l'ordre de priorité.
    Retourne (lectures, modes_non_geres). Une lecture au plus par mode : la première
    source qui donne un score ; les autres valeurs vont dans `notes`."""
    lectures, non_geres = [], []
    for mode in meta.get("mode_guess", []):
        lec = None
        for source, texte in textes:
            r = extraire(texte, mode, config, source)
            if r == NON_GERE:
                non_geres.append(mode)
                break
            if not r:
                continue
            if lec is None:
                lec = lecture_vide(meta, mode)
                lec.update(score=r["valeur"], score_source=source)
                lec["notes"].append(f"score provisoire ({source}) : {r['brut']}")
                if r["autres"]:
                    lec["notes"].append("autres candidats : " + ", ".join(r["autres"]))
                if r.get("semaine_passee"):
                    lec["notes"].append("semaine précédente ?")
                if mode == "hotm":  # v3 : porte d'après le titre d'abord
                    porte = lire_porte(meta.get("title") or "") or lire_porte(texte)
                    lec["gate"] = porte["number"] if porte else None
                if mode == "bot":  # v3 : variante d'après le titre
                    lec["bot_variant"] = variante_bot(meta.get("title"), config)
            elif r["valeur"] != lec["score"]:
                lec["notes"].append(f"{source} : {r['brut']}")
        if lec:
            lectures.append(lec)
    return lectures, sorted(set(non_geres))


def remplacer_lectures(toutes, video_id, nouvelles, sources):
    """Remplace les lectures de `video_id` issues de `sources` (idempotent)."""
    gardees = [l for l in toutes if not (l["video_id"] == video_id and l["score_source"] in sources)]
    return gardees + nouvelles
