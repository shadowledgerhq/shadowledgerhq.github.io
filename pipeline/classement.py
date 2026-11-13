"""Calcul des classements de la semaine (docs/SPEC_ETAPE1.md §4-5). Idempotent.

Entrée : data/runs/<semaine>/_lectures.json (une entrée par score lu par les tris).
Sorties : poc.json, bot-season.json, bot-challenge.json, hotm-gate-<n>.json,
_boss.json ; mises à jour de rejected/<semaine>.json, processed.json, channels.json.

Usage : python3 pipeline/classement.py [AAAA-MM-JJ]   (défaut : semaine en cours)
"""
import sys
from collections import defaultdict
from datetime import timezone

from donnees import Donnees, ajouter_rejet, charger_config
from semaine import id_semaine, iso_paris, maintenant, parse_iso, semaine_precedente

UNITES = {"poc": "damage", "bot": "seconds", "gb": "rage_count", "hotm": "points"}
CLES_DETAIL = {"poc": ("sjw", "successor", "hunters"), "hotm": ("clear", "proof_bonus", "proof_level")}


def cle_classement(lec, config):
    mode = lec["mode"]
    if mode == "bot":
        v = lec.get("bot_variant")
        return f"bot-{v}" if v in ("season", "challenge") else config["fichier_bot_variante_inconnue"]
    if mode == "hotm":
        g = lec.get("gate")
        return f"hotm-gate-{g}" if isinstance(g, int) else config["fichier_hotm_porte_inconnue"]
    return mode


def _inconnue(cle, config):
    return cle in (config["fichier_bot_variante_inconnue"], config["fichier_hotm_porte_inconnue"])


def _pub(r):
    return parse_iso(r["published_at"])


def _meilleur(runs, mode):
    return (min if mode == "bot" else max)(runs, key=lambda r: r["score"])


def _tri_score(runs, mode):
    return sorted(runs, key=lambda r: r["score"], reverse=(mode != "bot"))


# --- §4.4 doublons -------------------------------------------------------------

def dedoublonner(runs, config):
    """Retourne (runs gardées, doublons [(run, video_id d'origine)])."""
    modes = config.get("doublon_modes", ["poc"])
    groupes = defaultdict(list)
    for r in runs:
        if r["exact"] and r["mode"] in modes:
            groupes[(r["_cle"], r["score"])].append(r)
    retires, doublons = set(), []
    # v3 : hors `doublon_modes` (BOT, HOTM), rien n'est retiré : simple note « doublon possible »
    possibles = defaultdict(list)
    for r in runs:
        if r["exact"] and r["mode"] not in modes:
            possibles[(r["_cle"], r["score"])].append(r)
    for groupe in possibles.values():
        if len({r["channel_id"] for r in groupe}) >= 2:
            for r in groupe:
                if "doublon possible" not in r["notes"]:
                    r["notes"].append("doublon possible")
    for groupe in groupes.values():
        if len(groupe) < 2:
            continue
        groupe.sort(key=lambda r: (_pub(r), r["video_id"], r["t"] or 0))
        origine = groupe[0]
        for r in groupe[1:]:
            retires.add(id(r))
            if r["channel_id"] != origine["channel_id"]:
                doublons.append((r, origine["video_id"]))
    return [r for r in runs if id(r) not in retires], doublons


# --- §4.5 boss -----------------------------------------------------------------

def controler_boss(runs, cles, config, boss_prec):
    """Modifie les runs (a_verifier + note). Retourne (boss_semaine, cles_non_controlees,
    runs_semaine_precedente)."""
    ref_prec = {b["classement"]: b["stage"] for b in boss_prec}
    boss, non_controle, precedentes = [], set(), []
    for cle in cles:
        sures = [r for r in runs if r["_cle"] == cle and r["confidence"] == "sur" and r["stage"]]
        videos_par_stage = defaultdict(set)
        for r in sures:
            videos_par_stage[r["stage"]].add(r["video_id"])
        nb_videos = len({r["video_id"] for r in sures})
        if nb_videos < config.get("boss_min_videos", 3):
            non_controle.add(cle)
            continue
        ref = sorted(videos_par_stage.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0][0]
        exemple = sures[0]
        boss.append({"classement": cle, "mode": exemple["mode"], "gate": exemple.get("gate"),
                     "bot_variant": exemple.get("bot_variant"), "stage": ref,
                     "videos": len(videos_par_stage[ref])})
        for r in runs:
            if r["_cle"] != cle or not r["stage"] or r["stage"] == ref:
                continue
            if r["stage"] == ref_prec.get(cle):
                precedentes.append(r)
            else:
                r["confidence"] = "a_verifier"
                r["notes"].append(f"boss différent : {r['stage']}")
    ids_prec = {id(r) for r in precedentes}
    return boss, non_controle, precedentes, [r for r in runs if id(r) not in ids_prec]


# --- §4.1 sélection des runs d'un joueur ---------------------------------------

def _choisir_poc(runs):
    """(runs choisies, ok). ok = une run de l'équipe 1 + une de l'équipe 2."""
    par_equipe = {e: _tri_score([r for r in runs if r["team"] == e], "poc") for e in (1, 2)}
    if par_equipe[1] and par_equipe[2]:
        return [par_equipe[1][0], par_equipe[2][0]], True
    choix, equipes = [], set()
    for r in _tri_score(runs, "poc"):
        if r["team"] in (1, 2):
            if r["team"] in equipes:
                continue  # deux runs de la même équipe ne s'additionnent jamais
            equipes.add(r["team"])
        choix.append(r)
        if len(choix) == 2:
            break
    return choix, False


def choisir_runs(runs, mode):
    if mode in ("bot", "hotm"):
        return [_meilleur(runs, mode)], True
    if mode == "poc":
        return _choisir_poc(runs)
    choix = _tri_score(runs, mode)[:2]  # GB : notion d'équipe [EN ATTENTE]
    return choix, len(choix) == 2


def ligne_joueur(runs_j, cle, config):
    mode = runs_j[0]["mode"]
    exactes = [r for r in runs_j if r["exact"]]
    utiles = exactes or runs_j  # §4.3 : provisoire remplacé par toute run exacte
    sures = [r for r in utiles if r["confidence"] == "sur"]
    choix, ok = choisir_runs(sures, mode) if sures else ([], False)
    nb_requis = 2 if mode in ("poc", "gb") else 1
    if not (ok and len(choix) == nb_requis):
        choix, _ = choisir_runs(utiles, mode)
        ok = False
    notes = []
    if mode in ("poc", "gb") and len(choix) < 2:
        notes.append("une seule run trouvée")
    if mode == "poc" and len(choix) == 2 and not ok and any(r["team"] is None for r in choix):
        notes.append("équipe illisible")
    if _inconnue(cle, config):
        notes.append("variante BOT illisible" if mode == "bot" else "porte HOTM illisible")
        ok = False
    sur = ok and all(r["confidence"] == "sur" for r in choix)
    return choix, sur, notes


# --- lignes JSON ---------------------------------------------------------------

def _total(choix, mode):
    if mode in ("bot", "hotm"):
        return choix[0]["score"]
    t = sum(r["score"] for r in choix)
    return round(t, 3) if isinstance(t, float) else t


def construire_ligne(choix, sur, notes_ligne, cle, week):
    mode = choix[0]["mode"]
    principale = _meilleur(choix, mode)
    notes = []
    for r in choix:
        for n in r["notes"]:
            if n not in notes:
                notes.append(n)
    notes += [n for n in notes_ligne if n not in notes]
    ligne = {
        "run_id": f"{cle}-{week}-{principale['video_id']}",
        "week": week,
        "mode": mode,
        "channel_id": principale["channel_id"],
        "player": principale["channel_title"],
        "channel": principale["channel_title"],
        "video_id": principale["video_id"],
        "video_ids": sorted({r["video_id"] for r in choix}, key=lambda v: v != principale["video_id"]),
        "published_at": iso_paris(principale["published_at"]),
        "lang": principale.get("lang"),
        "score": {"total": _total(choix, mode), "runs": [r["score"] for r in choix],
                  "unit": UNITES[mode]},
        "score_source": principale["score_source"],
        "exact": all(r["exact"] for r in choix),
        "confidence": "sur" if sur else "a_verifier",
        "rank": None,
        "notes": "; ".join(notes),
    }
    if mode == "hotm":
        ligne["gate"] = principale.get("gate")
        ligne["hunter_mode"] = principale.get("hunter_mode")
    if mode == "bot":
        ligne["bot_variant"] = principale.get("bot_variant")
    detail = []
    for r in choix:
        d = {"video_id": r["video_id"], "published_at": iso_paris(r["published_at"]), "t": r["t"],
             "stage": r["stage"], "team": r["team"], "score_source": r["score_source"],
             "exact": r["exact"]}
        for k in CLES_DETAIL.get(mode, ()):
            if k in r.get("detail", {}):
                d[k] = r["detail"][k]
        detail.append(d)
    ligne["runs_detail"] = detail
    ligne["_fin"] = max(_pub(r) for r in choix)  # §4.2 : score complet le plus tôt
    return ligne


def ordonner(lignes, mode):
    """Runs classées par rang, puis runs rank null (§4.2, §5.1)."""
    signe = 1 if mode == "bot" else -1

    def cle(l):
        return (signe * l["score"]["total"], l["_fin"], l["channel_id"])

    classees = sorted((l for l in lignes if l["confidence"] == "sur"), key=cle)
    autres = sorted((l for l in lignes if l["confidence"] != "sur"), key=cle)
    for i, l in enumerate(classees, 1):
        l["rank"] = i
    for l in classees + autres:
        del l["_fin"]
    return classees + autres


# --- passage complet -----------------------------------------------------------

def calculer(week, d=None, config=None, horloge=None):
    """Recalcule tout le classement de `week`. Retourne un résumé pour le rapport."""
    d = d or Donnees()
    config = config or charger_config()
    instant = horloge or maintenant()
    meta = d.meta(week)
    if meta and meta.get("frozen"):
        return {"gelee": True, "week": week}

    rejetes = d.tous_rejetes()
    runs = []
    modes_classes = config.get("modes_classement", ["poc", "bot", "hotm"])  # v3 : GB lu mais pas classé
    for lec in d.lectures(week):
        if lec["video_id"] in rejetes or lec.get("score") is None or lec["mode"] not in modes_classes:
            continue
        r = {**lec, "notes": list(lec.get("notes", []))}
        r["_cle"] = cle_classement(r, config)
        runs.append(r)
    videos_avant = {r["video_id"] for r in runs}

    runs, doublons = dedoublonner(runs, config)
    cles = sorted({r["_cle"] for r in runs})
    boss, non_controle, precedentes, runs = controler_boss(
        runs, cles, config, d.boss(semaine_precedente(week)))

    # Vidéos qui n'ont plus aucune run : rejetées (doublon / semaine précédente).
    rejected, processed = d.rejected(week), d.processed()
    restantes = {r["video_id"] for r in runs}
    motifs = {}
    for r, origine in doublons:
        motifs.setdefault(r["video_id"], ("doublon", origine, r))
    for r in precedentes:
        motifs.setdefault(r["video_id"], ("semaine_precedente", r["stage"], r))
    date = instant.astimezone(timezone.utc).date().isoformat()
    nouveaux_rejets, titres = [], d.videos(week)
    for vid, (raison, detail, r) in motifs.items():
        if vid in restantes or vid not in videos_avant:
            continue
        p = processed.get(vid, {})
        entree = {"video_id": vid, "channel_id": r["channel_id"], "title": titres.get(vid, {}).get("title", ""),
                  "published_at": r["published_at"], "mode_guess": r["mode"], "reason": raison,
                  "detail": detail, "last_tri": p.get("last_tri"), "date": date}
        if ajouter_rejet(rejected, entree):
            nouveaux_rejets.append(entree)
        if vid in processed:
            processed[vid].update(status="rejete", updated_at=date, pc_needed=False)

    # Lignes par classement.
    par_cle = defaultdict(lambda: defaultdict(list))
    for r in runs:
        par_cle[r["_cle"]][r["channel_id"]].append(r)
    fichiers = {}
    for cle, joueurs in par_cle.items():
        lignes = []
        for runs_j in joueurs.values():
            choix, sur, notes = ligne_joueur(runs_j, cle, config)
            if cle in non_controle:
                notes.append("boss non contrôlé")
            lignes.append(construire_ligne(choix, sur, notes, cle, week))
        fichiers[cle] = ordonner(lignes, lignes[0]["mode"])

    # Écriture : fichiers présents + anciens fichiers de classement devenus vides.
    dossier = d.data / "runs" / week
    anciens = set()
    if dossier.exists():
        anciens = {p.stem for p in dossier.glob("*.json") if not p.stem.startswith("_")}
    for cle in sorted(anciens | set(fichiers)):
        if cle in fichiers:
            d.ecrire(f"runs/{week}/{cle}.json", fichiers[cle])
        else:  # classement devenu vide (ou mode retiré du classement, ex. gb.json) : pas de fichier
            (dossier / f"{cle}.json").unlink()
    d.ecrire(f"runs/{week}/_boss.json", boss)
    d.ecrire(f"rejected/{week}.json", rejected)
    d.ecrire("processed.json", processed)

    # Chaînes avec au moins une run classée : suivies automatiquement (§1.4).
    channels = d.channels()
    connues = {c["channel_id"] for c in channels}
    for lignes in fichiers.values():
        for l in lignes:
            if l["rank"] is not None and l["channel_id"] not in connues:
                connues.add(l["channel_id"])
                channels.append({"channel_id": l["channel_id"], "name": l["channel"],
                                 "uploads_playlist": "UU" + l["channel_id"][2:],
                                 "added_at": date, "source": "auto"})
    d.ecrire("channels.json", channels)

    a_verifier = [(cle, l) for cle, ls in fichiers.items() for l in ls if l["confidence"] != "sur"]
    alertes_boss = [f"{cle} : boss non contrôlé (< {config.get('boss_min_videos', 3)} vidéos)"
                    for cle in sorted(non_controle)]
    alertes_boss += [f"{r['_cle']} : {r['video_id']} boss différent ({r['stage']})"
                     for r in runs if any(n.startswith("boss différent") for n in r["notes"])]
    return {"gelee": False, "week": week, "fichiers": {c: len(l) for c, l in fichiers.items()},
            "a_verifier": a_verifier, "rejets": nouveaux_rejets, "boss": boss,
            "alertes_boss": alertes_boss}


if __name__ == "__main__":
    semaine = sys.argv[1] if len(sys.argv) > 1 else id_semaine(maintenant())
    res = calculer(semaine)
    if res["gelee"]:
        print(f"Semaine {semaine} gelée : rien à faire.")
    else:
        print(f"Semaine {semaine} : " + ", ".join(f"{c} {n}" for c, n in sorted(res["fichiers"].items()))
              + f" ; {len(res['a_verifier'])} à vérifier ; {len(res['rejets'])} rejet(s).")
