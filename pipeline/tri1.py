"""Tri 1 : score provisoire dans le texte (titre, description, sous-titres).
Référence : docs/SPEC_ETAPE1.md §2. Tout score trouvé ici est provisoire :
exact false, confidence a_verifier ; la vidéo continue aux tris suivants."""
import re

from hotm_ecran import lire_porte
from scores import NON_GERE, degats_gb, extraire
from semaine import bornes, parse_iso, semaine_de

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
        "regles": None,         # v8 : version des règles du tri 1 qui a produit la lecture (config.tri1_version)
        "bot_variant": None,
        "player_ingame": None,  # v4 : pseudo en jeu (BOT, bandeau du bas), information seulement
        "damage": None,         # v5 : GB, `Final Score` (arrondi si lu sur le Personal Record)
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
    """SPEC §4.6 : variante BOT d'après le titre. `challenge` / `チャレンジ` / `챌린지` -> challenge ;
    `S\\d+-\\d`, `season \\d+`, `시즌 \\d+`, `シーズン\\d+` -> season. Les deux indices ou aucun -> None."""
    cfg = config.get("bot_variante", {})
    bas = (titre or "").lower()
    challenge = any(_mot_entier(m.lower(), bas) for m in cfg.get("challenge", []))
    season = any(re.search(rx, titre or "", re.IGNORECASE) for rx in cfg.get("season_regex", []))
    if challenge == season:
        return None
    return "challenge" if challenge else "season"


def _mot_entier(mot, texte):
    if mot.isascii():
        return re.search(rf"(?<![a-z0-9]){re.escape(mot)}(?![a-z0-9])", texte) is not None
    return mot in texte


def notes_alerte_reset(meta, config):
    """v8 §2.2 : vidéo publiée moins de `config.reset_alerte_heures` (3) après le reset de sa semaine : note
    d'alerte, sans effet sur le statut. Retourne [] ou la note."""
    heures = config.get("reset_alerte_heures")
    if not heures or not meta.get("published_at"):
        return []
    ecart = parse_iso(meta["published_at"]) - bornes(semaine_de(meta["published_at"]))[0]
    return ["publiée juste après le reset : semaine précédente ?"] if ecart.total_seconds() < heures * 3600 else []


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
                lec.update(score=r["valeur"], score_source=source, regles=config.get("tri1_version"))
                lec["notes"] += notes_alerte_reset(meta, config)
                if mode == "gb":  # v8 : dégâts lus dans le même texte (arrondis : exact false)
                    lec["damage"] = degats_gb(texte, config)
                    if lec["damage"] is not None:
                        lec["detail"]["damage_exact"] = False
                lec["notes"].append(f"score provisoire ({source}) : {r['brut']}")
                if r["autres"]:
                    lec["notes"].append("autres candidats : " + ", ".join(r["autres"]))
                if r.get("semaine_passee"):
                    lec["notes"].append("semaine précédente ?")
                if mode == "hotm":  # v3 : porte d'après le titre (l'écran prime dès qu'il est lu)
                    porte = lire_porte(meta.get("title") or "")
                    lec["gate"] = porte["number"] if porte else None
                if mode == "bot":  # v3 : variante d'après le titre
                    lec["bot_variant"] = variante_bot(meta.get("title"), config)
                    if lec["bot_variant"]:
                        lec["notes"].append("variante d'après le titre")
            elif r["valeur"] != lec["score"]:
                lec["notes"].append(f"{source} : {r['brut']}")
        if lec:
            lectures.append(lec)
    return lectures, sorted(set(non_geres))


def remplacer_lectures(toutes, video_id, nouvelles, sources):
    """Remplace les lectures de `video_id` issues de `sources` (idempotent)."""
    gardees = [l for l in toutes if not (l["video_id"] == video_id and l["score_source"] in sources)]
    return gardees + nouvelles
