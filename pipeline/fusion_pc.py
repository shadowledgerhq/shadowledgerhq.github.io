"""Résolution automatique d'un conflit git sur data/ entre le PC (tris 3-4) et le passage GitHub (demande de la discussion 1).

Règle : version DISTANTE pour les fichiers du passage GitHub (classements, `_videos.json`, `_meta.json`, `_rapport.md`,
sous-titres…), version du PC pour les fichiers des tris 3-4 (`PROPRES_PC`). Deux fichiers sont écrits par les deux côtés ;
ils sont fusionnés vidéo par vidéo : `processed.json` (distant + champs `pc` et statut final du PC) et `runs/<semaine>/_lectures.json`
(lectures distantes + lectures d'écran du PC, via `pc.fusionner_ecrans`). `rejected/<semaine>.json` : union des deux listes."""
import re

PROPRES_PC = (
    r"^data/runs/[^/]+/_rapport_pc\.md$",          # blocs du PC : jamais effacés
    r"^data/builds/",                               # builds (étape 2, PC)
    r"^data/icons/hunters_cartes/",                 # bibliothèque de cartes apprise (PC)
)


def est_propre_pc(chemin):
    return any(re.search(p, chemin) for p in PROPRES_PC)


def fusion_json(chemin):
    return chemin == "data/processed.json" or bool(re.match(r"^data/runs/[^/]+/_lectures\.json$", chemin)) \
        or bool(re.match(r"^data/rejected/[^/]+\.json$", chemin))


def fusionner_processed(distant, local):
    """Distant + ce que seul le PC écrit : `pc` (avancement des tris 3-4) et un statut final (termine/rejete) posé par le PC."""
    res = {k: dict(v) if isinstance(v, dict) else v for k, v in (distant or {}).items()}
    for vid, l in (local or {}).items():
        d = res.get(vid)
        if not isinstance(l, dict):
            continue
        if d is None:
            res[vid] = l
            continue
        if l.get("pc"):
            d["pc"] = l["pc"]
        if l.get("pc_needed") is not None and "pc_needed" not in d:
            d["pc_needed"] = l["pc_needed"]
        if d.get("status") == "en_cours" and l.get("status") in ("termine", "rejete"):
            d["status"] = l["status"]
            for k in ("week", "reason", "date", "rejected_on"):
                if k in l and k not in d:
                    d[k] = l[k]
    return res


def fusionner_lectures(distant, local, config=None):
    """Lectures distantes, plus les lectures d'écran (images) du PC : pour chaque vidéo, `pc.fusionner_ecrans` les range comme
    au passage normal (l'écran contrôlé prime sur le titre, doublons retirés)."""
    import pc
    res = list(distant or [])
    par_video = {}
    for l in local or []:
        if pc._est_ecran(l):
            par_video.setdefault(l["video_id"], []).append(l)
    for vid, nouvelles in par_video.items():
        res = pc.fusionner_ecrans(res, vid, nouvelles, config)
    return res


def fusionner_liste(distant, local):
    res = list(distant or [])
    return res + [x for x in (local or []) if x not in res]


def fusionner(chemin, distant, local, config=None):
    """Contenu fusionné du fichier `chemin`, ou None si on ne sait pas (le fichier reste distant)."""
    if chemin == "data/processed.json":
        return fusionner_processed(distant, local) if isinstance(local, dict) else None
    if chemin.endswith("_lectures.json"):
        return fusionner_lectures(distant, local, config) if isinstance(local, list) else None
    if chemin.startswith("data/rejected/"):
        return fusionner_liste(distant, local) if isinstance(local, list) and (distant is None or isinstance(distant, list)) else None
    return None
