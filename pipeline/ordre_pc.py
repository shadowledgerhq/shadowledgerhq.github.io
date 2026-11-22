"""SPEC v29 §6 : ordre de traitement du PC et « Top 10 couvert ».

Une vidéo est CANDIDATE au top 10 de son mode quand elle peut y entrer : score provisoire (`a_verifier`) meilleur que le
10e score `sûr` du fichier de classement (BOT : temps plus court), OU fichier de classement avec moins de 10 runs `sûr`, OU aucun
score provisoire du tout. Le PC traite d'abord les candidates (dans chaque groupe : rang du score provisoire dans son fichier,
0 = meilleur, donc score décroissant, BOT temps croissant ; sans score en dernier), puis les autres (même ordre). `top10_couvert`
= plus aucune candidate en attente du PC."""
import json
from pathlib import Path

TOP = 10


def _meilleur(a, b, unite):
    """a strictement meilleur que b ?"""
    return a < b if unite == "seconds" else a > b


def _fichiers(d, week):
    """[(nom de fichier, [lignes])] des classements de la semaine (fichiers sans `_`)."""
    sortie = []
    for f in sorted((Path(d.data) / "runs" / week).glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            lignes = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(lignes, list):
            sortie.append((f.stem, [x for x in lignes if isinstance(x, dict) and isinstance(x.get("score"), dict)
                                    and x["score"].get("total") is not None]))
    return sortie


def analyser(d, week):
    """{video_id: (candidate, rang du score provisoire | None)} pour toutes les vidéos qui ont une ligne de classement.
    Une vidéo à plusieurs lignes garde la meilleure situation (candidate si une ligne l'est ; plus petit rang)."""
    res = {}
    for _, lignes in _fichiers(d, week):
        if not lignes:
            continue
        unite = lignes[0]["score"].get("unit")
        tri = sorted(lignes, key=lambda x: x["score"]["total"], reverse=(unite != "seconds"))
        surs = [x["score"]["total"] for x in tri if x.get("confidence") == "sur"]
        dixieme = surs[TOP - 1] if len(surs) >= TOP else None
        for rang, x in enumerate(tri):
            if x.get("confidence") == "sur":
                continue
            cand = dixieme is None or _meilleur(x["score"]["total"], dixieme, unite) or "écart improbable" in (x.get("notes") or "")   # v35 : reste prioritaire
            for v in (x.get("video_ids") or [x.get("video_id")]):
                if v is None:
                    continue
                ancien = res.get(v)
                res[v] = (cand or (ancien[0] if ancien else False), rang if not ancien else min(rang, ancien[1]))
        for x in tri:                                # ligne `sûre` : la vidéo a un score (pas candidate à cause de cette ligne)
            if x.get("confidence") == "sur":
                for v in (x.get("video_ids") or [x.get("video_id")]):
                    if v is not None:
                        res.setdefault(v, (False, None))
    return res


def candidate(info, vid):
    """Vidéo sans aucune ligne = pas de score provisoire = candidate ; sinon selon `analyser`."""
    return True if vid not in info else info[vid][0]


def derniers(d, week, processed, ids, max_minutes=30):
    """v37 §6 : vidéos traitées APRÈS toutes les autres et jamais comptées dans « Top 10 couvert » : `processed.hors_sujet_probable`, ou
    durée > `max_minutes` (30) sans score dans le texte (titre, description, sous-titres). Vidéo dont le tri 3 a vu un écran de jeu : non."""
    import tri1
    from pc import duree_minutes
    videos, lectures = d.videos(week), d.lectures(week)
    sortie = set()
    for v in ids:
        p = processed.get(v) or {}
        if (p.get("pc") or {}).get("ecran_jeu"):
            continue
        minutes = duree_minutes((videos.get(v) or {}).get("duration"))
        if p.get("hors_sujet_probable") or (minutes is not None and minutes > max_minutes and not tri1.score_dans_le_texte(lectures, v)):
            sortie.add(v)
    return sortie


def ordonner(d, week, ids, processed=None, max_minutes=30):
    """`ids` (ordre d'origine conservé à égalité) -> (liste ordonnée, ensemble des candidates). v37 : avec `processed`, les vidéos
    `derniers` passent après toutes les autres et ne sont jamais candidates."""
    info = analyser(d, week)
    fin = derniers(d, week, processed, ids, max_minutes) if processed is not None else set()
    cand = {v for v in ids if candidate(info, v) and v not in fin}
    grand = 10 ** 9

    def cle(i_v):
        i, v = i_v
        rang = info.get(v, (False, None))[1]
        return (1 if v in fin else 0, 0 if v in cand else 1, grand if rang is None else rang, i)
    return [v for _, v in sorted(enumerate(ids), key=cle)], cand


def en_attente(processed, week, d=None):
    """Vidéos de la semaine encore à traiter par le PC (sous-titres ou images)."""
    return [v for v, p in processed.items() if p.get("week") == week and p.get("status") == "en_cours" and p.get("pc_needed")
            and (p.get("pc") or {}).get("tri4") not in ("fait", "inutile")]


def candidates_restantes(d, week, processed):
    """Nombre de vidéos candidates au top 10 encore en attente du PC."""
    ids = en_attente(processed, week)
    info = analyser(d, week)
    fin = derniers(d, week, processed, ids)         # v37 : hors sujet probable et vidéos longues sans score : jamais comptées
    return sum(1 for v in ids if candidate(info, v) and v not in fin)


def ligne_top10(n):
    return f"- Top 10 couvert : {'oui' if n == 0 else 'non'} ({n} vidéo{'s' if n > 1 else ''} candidate{'s' if n > 1 else ''} au top 10 restante{'s' if n > 1 else ''})"
