"""Calcul des classements de la semaine (docs/SPEC_ETAPE1.md §4-5). Idempotent.

Entrée : data/runs/<semaine>/_lectures.json (une entrée par score lu par les tris).
Sorties : poc.json, bot.json, hotm-gate-<n>.json,
_boss.json ; mises à jour de rejected/<semaine>.json, processed.json, channels.json.

Usage : python3 pipeline/classement.py [AAAA-MM-JJ]   (défaut : semaine en cours)
"""
import re
import unicodedata
import sys
from collections import defaultdict
from datetime import timezone

import chrono_bot
import elements
import gb
import regles_deduites
from bot_saison import controler_semaine_bot
from donnees import Donnees, ajouter_rejet, charger_config
from semaine import bornes, id_semaine, iso_paris, maintenant, parse_iso, semaine_precedente

UNITES = {"poc": "damage", "bot": "seconds", "gb": "rage_count", "hotm": "points"}
CLES_DETAIL = {"poc": ("sjw", "successor", "hunters"), "hotm": ("clear", "proof_bonus", "proof_level"),
               "gb": ("total_score", "total_rage_count", "challenge_count", "time_left", "hud_rage_count", "damage_source")}


def cle_classement(lec, config):
    mode = lec["mode"]
    if mode == "bot":
        return "bot"  # v10 : un seul classement BOT
    if mode == "hotm":
        g = lec.get("gate")
        return f"hotm-gate-{g}" if isinstance(g, int) else config["fichier_hotm_porte_inconnue"]
    return mode


def _inconnue(cle, config):
    return cle == config["fichier_hotm_porte_inconnue"]


def _pub(r):
    return parse_iso(r["published_at"])


def _cle_score(r, mode):
    """Clé de comparaison d'une run : score ; au GB (v5) RC puis dégâts ; au BOT (v34) borne haute d'un chrono incomplet (`_tri`)."""
    return gb.cle_run(r) if mode == "gb" else r.get("_tri", r["score"])


def _meilleur(runs, mode):
    return (min if mode == "bot" else max)(runs, key=lambda r: _cle_score(r, mode))


def _tri_score(runs, mode):
    return sorted(runs, key=lambda r: _cle_score(r, mode), reverse=(mode != "bot"))


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
        if r["exact"] and r["mode"] in ("bot", "hotm") and r["mode"] not in modes:
            possibles[(r["_cle"], r["score"])].append(r)
    for groupe in possibles.values():
        if len({r["channel_id"] for r in groupe}) >= 2:
            groupe.sort(key=lambda r: (_pub(r), r["video_id"]))
            for r in groupe:  # § 4.4 : note `doublon possible : <video_id>` (la plus ancienne des autres vidéos)
                autre = next(x for x in groupe if x["video_id"] != r["video_id"] and x["channel_id"] != r["channel_id"])
                note = f"doublon possible : {autre['video_id']}"
                if note not in r["notes"]:
                    r["notes"].append(note)
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

def _norm_nom(t):
    return re.sub(r"\s+", "", "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")).lower()


def boss_id(stage, config):
    """v18 : identifiant commun d'un nom de boss (`config.gb.boss_alias`, comparaison sans accents, casse ni espaces) ;
    nom inconnu : le nom lui-même. `stage` garde le texte lu."""
    alias = {_norm_nom(n): i for n, i in {**((config.get("gb") or {}).get("boss_alias") or {}),
                                           **((config.get("bot") or {}).get("boss_alias") or {})}.items() if not n.startswith("_")}
    return alias.get(_norm_nom(stage), stage)


NOTE_RESET = "publiée juste après le reset"


def _juste_apres_reset(r, heures):
    """Vidéo publiée moins de `heures` h après le reset de sa semaine (v34 : boss BOT, `config.bot.reset_boss_heures`)."""
    if not r.get("published_at"):
        return False
    pub = _pub(r)
    return 0 <= (pub - bornes(id_semaine(pub))[0]).total_seconds() < heures * 3600


def controler_boss(runs, cles, config, boss_prec):
    """Modifie les runs (a_verifier + note). Retourne (boss_semaine, cles_non_controlees,
    runs_semaine_precedente)."""
    ref_prec = {b["classement"]: boss_id(b["stage"], config) for b in boss_prec}
    boss, non_controle, precedentes = [], set(), []
    for cle in cles:
        sures = [r for r in runs if r["_cle"] == cle and r["confidence"] == "sur" and r["stage"]]
        videos_par_stage, texte_stage = defaultdict(set), {}
        for r in sures:
            videos_par_stage[boss_id(r["stage"], config)].add(r["video_id"])
            texte_stage.setdefault(boss_id(r["stage"], config), r["stage"])
        nb_videos = len({r["video_id"] for r in sures})
        if nb_videos < config.get("boss_min_videos", 3):
            non_controle.add(cle)
            continue
        ref = sorted(videos_par_stage.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0][0]
        exemple = sures[0]
        boss.append({"classement": cle, "mode": exemple["mode"], "gate": exemple.get("gate"),
                     "stage": texte_stage[ref],
                     "videos": len(videos_par_stage[ref])})
        heures_boss = (config.get("bot") or {}).get("reset_boss_heures") if cle == "bot" else None
        for r in runs:
            if r["_cle"] != cle or not r["stage"]:
                continue
            proche = bool(heures_boss) and _juste_apres_reset(r, heures_boss)
            if boss_id(r["stage"], config) == ref:
                if proche:      # v34 : boss de la semaine confirmé : l'alerte « semaine précédente ? » tombe
                    r["notes"][:] = [n for n in r["notes"] if not n.startswith(NOTE_RESET)]
                continue
            if proche or boss_id(r["stage"], config) == ref_prec.get(cle):          # v34 : < 6 h après le reset, autre boss = semaine précédente
                precedentes.append(r)
            else:
                r["confidence"] = "a_verifier"
                r["notes"].append(f"boss différent : {r['stage']}")
    ids_prec = {id(r) for r in precedentes}
    return boss, non_controle, precedentes, [r for r in runs if id(r) not in ids_prec]


# --- §4.1 sélection des runs d'un joueur ---------------------------------------

def _somme_cle(a, b, mode):
    ka, kb = _cle_score(a, mode), _cle_score(b, mode)
    return tuple(x + y for x, y in zip(ka, kb)) if mode == "gb" else ka + kb


def _choisir_poc(runs, mode="poc"):
    """(runs choisies, ok). v30 : la meilleure PAIRE de runs de groupes / équipes distincts (équipe lue, sinon élément ; un chasseur commun
    vu à l'écran = même groupe). ok = paire distinguée sûrement. Paire « peut » (une équipe connue, l'autre non) : ok faux, ligne
    `a_verifier`. Aucune paire : la meilleure run seule (règle v17)."""
    for niveau, ok in (("oui", True), ("peut", False)):
        paires = [(a, b) for i, a in enumerate(runs) for b in runs[i + 1:] if elements.distinctes(a, b) == niveau]
        if paires:
            a, b = max(paires, key=lambda p: _somme_cle(p[0], p[1], mode))
            return sorted([a, b], key=lambda r: (r["team"] if r["team"] in (1, 2) else 9, tuple(-x if isinstance(x, (int, float)) else x for x in (_cle_score(r, mode) if mode == "gb" else (r["score"],))))), ok
    return ([_meilleur(runs, mode)] if runs else []), False


def choisir_runs(runs, mode):
    if mode in ("bot", "hotm"):
        return [_meilleur(runs, mode)], True
    return _choisir_poc(runs, mode)  # POC : une run par équipe ; GB (v5) : une run par groupe


def ligne_joueur(runs_j, cle, config):
    mode = runs_j[0]["mode"]
    exactes = [r for r in runs_j if r["exact"]]
    utiles = exactes or runs_j  # §4.3 : provisoire remplacé par toute run exacte
    sures = [r for r in utiles if r["confidence"] == "sur"]
    choix, ok = choisir_runs(sures, mode) if sures else ([], False)
    nb_requis = 2 if mode in ("poc", "gb") else 1
    une_seule = False
    if mode in ("poc", "gb") and len(choix) == 1:
        # v16 (décision d'Alexis du 14/11) : une seule run `sur` est classée, total = cette run ; une 2e run (autre équipe /
        # autre groupe) trouvée plus tard s'y ajoutera. Si une run provisoire d'une autre équipe existe déjà, le total est
        # incertain : ligne `a_verifier` comme avant.
        concurrentes = [r for r in utiles if r not in sures and (r["team"] is None or r["team"] != choix[0]["team"])]
        une_seule = not concurrentes
        ok = une_seule
    if not (ok and (len(choix) == nb_requis or une_seule)):
        choix, _ = choisir_runs(utiles, mode)
        ok = False
    notes = []
    if mode in ("poc", "gb") and choix and any(r["team"] not in (1, 2) for r in choix):   # v18 : runs de groupe inconnu laissées de côté
        notes += [f"groupes inconnus : 2e run non additionnée ({r['score']}, {r['video_id']})"
                  for r in _tri_score(sures, mode) if r not in choix and r["team"] not in (1, 2)]
    if une_seule:
        notes.append("une seule run")
    elif mode in ("poc", "gb") and len(choix) < 2:
        notes.append("une seule run trouvée")
    if (mode in ("poc", "gb") and len(choix) == 2 and not ok and any(r["team"] is None for r in choix)
            and elements.distinctes(*choix) != "oui"):
        notes.append("équipe illisible" if mode == "poc" else "groupe illisible")
    if mode in ("poc", "gb") and len(choix) == 2 and elements.distinctes(*choix) == "oui":
        n = elements.note_distinction(*choix)         # v30 : groupes distingués par l'élément (chasseurs et / ou titre)
        if n:
            notes.append(n)
    if _inconnue(cle, config):
        notes.append("porte HOTM illisible")
        ok = False
    sur = ok and all(r["confidence"] == "sur" for r in choix) and not any(r.get("_contradiction") for r in choix)
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
    if mode == "bot" and principale.get("_tri") is not None:
        ligne["_tri"] = principale["_tri"]         # v34 : chrono incomplet trié à sa borne haute (retiré avant l'écriture)
    if mode == "hotm":
        ligne["gate"] = principale.get("gate")
        ligne["hunter_mode"] = principale.get("hunter_mode")
    if mode == "bot":
        ligne["bot_season_week"] = principale.get("bot_season_week")  # v9
        ligne["player_ingame"] = principale.get("player_ingame")  # v4 : information seulement
    if mode == "gb":
        ligne["_degats"] = gb.somme_degats(choix)  # départage (retiré avant l'écriture)
        ligne["_degats_exacts"] = all(r.get("damage") is not None and (r.get("detail") or {}).get("damage_exact", r.get("score_source") != "record")
                                      for r in choix)        # v33 : dégâts contrôlés (somme Player's Score + Hunter Rank) ?
    detail = []
    for r in choix:
        d = {"video_id": r["video_id"], "published_at": iso_paris(r["published_at"]), "t": r["t"],
             "stage": r["stage"], "team": r["team"], "score_source": r["score_source"],
             "exact": r["exact"]}
        if mode == "gb":  # v5 : dégâts de la run (arrondis si lus sur le Personal Record)
            d["damage"] = r.get("damage")
            d["damage_exact"] = (None if r.get("damage") is None  # v7 : pas de dégâts lus -> pas d'exactitude
                                 else (r.get("detail") or {}).get("damage_exact", r.get("score_source") != "record"))
        if mode in ("poc", "gb"):        # v30 : élément de la run (`light|fire|water|wind|dark` | null) et sa source
            d["element"], d["element_source"] = r.get("element"), r.get("element_source")
        for k in CLES_DETAIL.get(mode, ()):
            if k in r.get("detail", {}):
                d[k] = r["detail"][k]
        detail.append(d)
    ligne["runs_detail"] = detail
    ligne["_fin"] = max(_pub(r) for r in choix)  # §4.2 : score complet le plus tôt
    return ligne


NOTE_EGALITE_DEGAT = "égalité départagée par un dégât non contrôlé"


def ordonner(lignes, mode):
    """Runs classées par rang, puis runs rank null (§4.2, §5.1). GB : à RC égal, somme des dégâts (§4.1)."""
    signe = 1 if mode == "bot" else -1

    def cle(l):
        degats = -l.get("_degats", 0) if mode == "gb" else 0
        return (signe * l.get("_tri", l["score"]["total"]), degats, l["_fin"], l["channel_id"])

    if mode == "gb":        # v33 : un dégât non contrôlé ne départage jamais une égalité de RC (vote 5/3 du 17/11)
        egaux = {}
        for l in lignes:
            if l["confidence"] == "sur":
                egaux.setdefault(l["score"]["total"], []).append(l)
        for groupe in egaux.values():
            if len(groupe) > 1:
                for l in groupe:
                    if not l.get("_degats_exacts"):
                        l["confidence"] = "a_verifier"
                        l["notes"] = "; ".join(n for n in (l["notes"], NOTE_EGALITE_DEGAT) if n)
    if mode == "bot":       # v35 : écart improbable (< 70 % de la médiane des scores provisoires, ≥ 5 lignes) : hors du top 10 provisoire
        prov = [l for l in lignes if l["confidence"] != "sur"]
        limite = chrono_bot.ecart_improbable([l["score"]["total"] for l in prov])
        for l in prov:
            if limite is not None and l["score_source"] in chrono_bot.SOURCES_TEXTE and l["score"]["total"] < limite:
                if chrono_bot.NOTE_ECART_IMPROBABLE not in l["notes"]:
                    l["notes"] = "; ".join(n for n in (l["notes"], chrono_bot.NOTE_ECART_IMPROBABLE) if n)
    classees = sorted((l for l in lignes if l["confidence"] == "sur"), key=cle)
    autres = sorted((l for l in lignes if l["confidence"] != "sur"),
                    key=lambda l: (chrono_bot.NOTE_ECART_IMPROBABLE in l["notes"],) + cle(l))
    for i, l in enumerate(classees, 1):
        l["rank"] = i
    for l in classees + autres:
        del l["_fin"]
        l.pop("_tri", None)
        l.pop("_degats", None)
        l.pop("_degats_exacts", None)
    return classees + autres


# --- §4.7 saison du Personal Record -------------------------------------------

def controler_saison_record(runs, week, config):
    """Time Left in Season : capture = prochain reset − temps restant. Après `published_at` -> record
    de la saison précédente (rejeté, `semaine_precedente`). Illisible -> a_verifier."""
    _, fin = bornes(week)
    marges = gb.tolerances(config.get("gb"))
    gardees, precedentes, levees = [], [], set()
    for r in runs:
        if r.get("score_source") == "record":
            verdict = gb.saison_precedente((r.get("detail") or {}).get("time_left"), r["published_at"], fin, marges)
            if verdict:
                precedentes.append(r)
                continue
            if verdict is None:
                r["confidence"] = "a_verifier"
                r["notes"].append("saison illisible (Time Left in Season)")
            else:       # v15 : capture de la bonne semaine confirmée par `Time Left in Season` : l'alerte « juste après le reset » est levée
                r["notes"][:] = [n for n in r["notes"] if not n.startswith("publiée juste après le reset")]
                levees.add(r["video_id"])
        gardees.append(r)
    for r in gardees:         # v18 : le Personal Record lève l'alerte pour toutes les runs de la même vidéo (awb-GlVIa7Q)
        if r["video_id"] in levees:
            r["notes"][:] = [n for n in r["notes"] if not n.startswith("publiée juste après le reset")]
    return gardees, precedentes


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
    lectures_semaine = d.lectures(week)
    chrono_bot.noter_virgule_miniature(lectures_semaine)    # v35.1 : note ajoutée aux miniatures déjà stockées (sans relire la miniature)
    chrono_bot.appliquer_echecs_ecran(lectures_semaine)     # v35 : un écran BOT en échec de contrôle ne donne jamais un score
    for lec in gb.appliquer_hud(lectures_semaine):  # v12 : dégâts provisoires du HUD attachés aux lectures GB
        if lec["video_id"] in rejetes or lec.get("score") is None or lec["mode"] not in modes_classes or (lec.get("detail") or {}).get("sans_score"):
            continue
        r = {**lec, "notes": list(lec.get("notes", []))}
        r["_cle"] = cle_classement(r, config)
        runs.append(r)
    videos_avant = {r["video_id"] for r in runs}

    runs = chrono_bot.reconcilier(runs)               # v34 : chronos BOT incomplets, lectures de plusieurs sources
    runs, saisons_prec = controler_saison_record(runs, week, config)
    runs, records_seuls = gb.attribuer_groupes(runs)      # v30 : le Personal Record ne classe plus aucune run
    runs, semaines_prec, alertes_semaine_bot = controler_semaine_bot(runs, week, config)
    runs, doublons = dedoublonner(runs, config)
    cles = sorted({r["_cle"] for r in runs})
    boss, non_controle, precedentes, runs = controler_boss(
        runs, cles, config, d.boss(semaine_precedente(week)))
    boss_prec = d.boss(semaine_precedente(week))
    for b in boss:                  # v24 : première semaine où ce libellé de boss est la référence (changement de saison)
        avant = next((p for p in boss_prec if p.get("classement") == b["classement"]
                      and boss_id(p["stage"], config) == boss_id(b["stage"], config)), None)
        b["premiere_semaine"] = (avant.get("premiere_semaine") or semaine_precedente(week)) if avant else week

    titres_v = {v: m.get("title", "") for v, m in d.videos(week).items()}      # v30 : éléments des runs (titre, chasseurs vus)
    db_hunters = {h["id"]: h.get("element") for h in d.lire("db/hunters.json", []) if isinstance(h, dict) and "id" in h}
    elements.annoter(runs, titres_v, config, db_hunters, elements.charger_builds(d.data, week))

    # Vidéos qui n'ont plus aucune run : rejetées (doublon / semaine précédente).
    rejected, processed = d.rejected(week), d.processed()
    restantes = {r["video_id"] for r in runs}
    motifs = {}
    for r, origine in doublons:
        motifs.setdefault(r["video_id"], ("doublon", origine, r))
    for r in precedentes:
        motifs.setdefault(r["video_id"], ("semaine_precedente", r["stage"], r))
    for r in semaines_prec:  # v9 : titre S<n>-<w> de la semaine précédente
        motifs.setdefault(r["video_id"], ("semaine_precedente", r["bot_season_week"], r))
    for r in saisons_prec:
        motifs.setdefault(r["video_id"], ("semaine_precedente",
                                          f"Time Left in Season : {r['detail'].get('time_left')}", r))
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
    regles_deduites.mettre_a_jour(d, week, d.lectures(week), date)     # v24 : éléments autorisés déduits des écrans
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
            "alertes_boss": alertes_boss, "alertes_semaine_bot": alertes_semaine_bot,
            "records_seuls": [f"{v} : Personal Record seul : aucune run filmée" for v in records_seuls]}


if __name__ == "__main__":
    semaine = sys.argv[1] if len(sys.argv) > 1 else id_semaine(maintenant())
    res = calculer(semaine)
    if res["gelee"]:
        print(f"Semaine {semaine} gelée : rien à faire.")
    else:
        print(f"Semaine {semaine} : " + ", ".join(f"{c} {n}" for c, n in sorted(res["fichiers"].items()))
              + f" ; {len(res['a_verifier'])} à vérifier ; {len(res['rejets'])} rejet(s).")
