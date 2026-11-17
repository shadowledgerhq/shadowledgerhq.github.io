"""Étape 2 : builds du top 10 (docs/SPEC_ETAPE2.md v1).
Un build = une run (`runs_detail[i]`) d'une ligne classée `rank` 1-10 de `data/runs/<semaine>/<mode>.json`.
Écrit `data/builds/<semaine>/<mode>/<run_id>-<n>.json` et `data/builds/<semaine>/_rapport.md`.

Deux couches : `observer` (images -> observations, par icône ; sans zones définies rien n'est cherché, SPEC §5 point 1)
et `construire_build` (observations + règles -> JSON, statut, confiance ; pur, testable sans image).

    python3 pipeline/builds.py [AAAA-MM-JJ] [--force]
"""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sjw as sjw_mod

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "pipeline" / "config" / "etape2.json"
SLOTS_ARTEFACT = ("helmet", "chestplate", "gloves", "boots", "necklace", "bracelet", "ring", "earrings")
SLOTS_NOYAU = ("mind", "body", "spirit")
SLOTS_GB = ("A1", "A2", "A3", "B1", "B2", "B3")
CLES = ("sjw", "sjw_weapons", "sjw_artifacts", "sjw_cores", "sjw_stats", "sjw_skills", "blessings", "hunters", "weapons",
        "artifacts", "cores", "stats", "shadows", "successor", "subjugation_support", "proof")
CLES_SJW = ("sjw", "sjw_weapons", "sjw_artifacts", "sjw_cores", "sjw_stats", "sjw_skills", "blessings")
CATEGORIE_DB = {"hunter": "hunters", "weapon": "weapons", "set": "artifact_sets", "core": "cores", "shadow": "shadows",
                "successor": "successors", "skill": "sjw_skills", "blessing": "blessings",
                "support": "subjugation_support", "modifier": "proof_modifiers"}


def charger_config(chemin=CONFIG):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def _json(f, defaut):
    f = Path(f)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else defaut


def charger_db(racine=RACINE):
    """{fichier: {id: objet}} pour les catégories utilisées ; `stats` aussi."""
    db = {}
    for nom in ("hunters", "weapons", "artifact_sets", "cores", "shadows", "successors", "remnant_powers", "sjw_skills", "blessings",
                "subjugation_support", "proof_modifiers", "stats"):
        db[nom] = {o["id"]: o for o in _json(Path(racine) / "data" / "db" / f"{nom}.json", []) if isinstance(o, dict) and "id" in o
                    and o.get("kind") != "rules"}      # entrées de règles (discussion 9) : pas des éléments reconnaissables
    return db


def stats_obligatoires(db):
    return [i for i, s in db.get("stats", {}).items() if s.get("required")]


# --- règles et éléments attendus (§1.1, §2.2) -------------------------------------------------------------------------

def regles_mode(regles, mode):
    """Bloc de règles du mode, ou None (inconnu). BOT : `bot`, sinon `bot_season` (SPEC §1.1)."""
    modes = (regles or {}).get("modes") or {}
    if mode == "bot":
        return modes.get("bot") or modes.get("bot_season") or None
    return modes.get(mode) or None


def deduire_hunter_mode(obs):
    """§1.1 : 4 onglets sans bénédictions -> True (sans SJW) ; 5 onglets, ou un personnage à gauche -> False. Sinon None."""
    ind = (obs or {}).get("hunter_mode_indices") or {}
    if ind.get("onglets") == 4 and not ind.get("benedictions"):
        return True
    if ind.get("onglets") == 5 or ind.get("perso_gauche"):
        return False
    return None


def elements_attendus(mode, regles, hunter_mode, cfg):
    """({cle: True | "fac" | None}, [plafonds]). True = attendu et compté ; "fac" = facultatif ; None = sans objet."""
    exp = {k: None for k in CLES}
    plafonds = []
    stats = True if cfg.get("stats_obligatoires", True) else "fac"
    for k in ("hunters", "weapons", "artifacts", "cores"):
        exp[k] = True
    exp["stats"] = stats
    r = regles
    if r is None:
        plafonds.append(f"règles {mode} inconnues")
    sjw_possible, sjw_regle = True, True
    if mode == "hotm":
        if hunter_mode is True:
            sjw_possible = False
        elif hunter_mode is None:
            plafonds.append("hunter_mode inconnu")
            sjw_regle = False
    def etat_regle(cle):
        """v5 : `true` -> attendu, `false` -> interdit (None), `null`/absent -> inconnu (facultatif, jamais d'alerte « interdit »)."""
        v = None if r is None else r.get(cle)
        return "fac" if v is None else (True if v else None)

    if sjw_possible:
        etat = "fac" if not sjw_regle else etat_regle("sjw")
        for k in CLES_SJW:
            exp[k] = etat
        if etat is True:
            exp["sjw_stats"] = stats
            exp["sjw_skills"] = etat_regle("sjw_skills")
            exp["blessings"] = etat_regle("blessings")
        elif etat == "fac":
            exp["sjw_stats"] = "fac"
    for k, cle_regle in (("shadows", "shadows"), ("successor", "successor")):
        exp[k] = etat_regle(cle_regle)
    if mode == "poc":
        exp["subjugation_support"] = "fac"
    if mode == "hotm":
        exp["proof"] = "fac"
    return exp, plafonds


# --- normalisation des observations ------------------------------------------------------------------------------------

def _pieces(liste, slots, cle_id):
    """Aligne une liste d'observations sur des emplacements fixes."""
    par_slot = {o.get("slot"): o for o in (liste or []) if isinstance(o, dict)}
    sortie = []
    for s in slots:
        o = par_slot.get(s) or {}
        e = {"slot": s, cle_id: o.get(cle_id), "level": o.get("level")}
        if o.get("empty"):
            e["empty"] = True
        sortie.append(e)
    return sortie


def _compter_pieces(liste, cle_id):
    return sum(1 for o in liste if o.get(cle_id) or o.get("empty"))


def _ratio(n, total):
    return f"{n}/{total}"


def _stats_lues(stats, db, obligatoires):
    return [k for k in obligatoires if k in (stats or {}) and (stats or {})[k] not in (None, {})]


def _bonus_sets(artefacts, db):
    """Nombre de pièces par set, paliers atteints d'après `artifact_sets.json` (jamais lu à l'écran)."""
    c = Counter(a["set_id"] for a in artefacts if a.get("set_id"))
    sortie = []
    for set_id, n in sorted(c.items()):
        paliers = sorted(int(p) for p in ((db.get("artifact_sets", {}).get(set_id) or {}).get("bonuses") or {}) if str(p).isdigit())
        sortie.append({"set_id": set_id, "pieces": n, "tiers": [p for p in paliers if p <= n]})
    return sortie


def _rang_hunters(n):
    return list(range(1, n + 1))


# --- construction d'un build (§1.2, §2) ------------------------------------------------------------------------------

def construire_build(ctx, obs, regles, cfg, db):
    """`ctx` : run_id, run_index, week, mode, gate, hunter_mode, rank, player, channel_id, video_id, t_result, team.
    `obs` : observations (voir `observer`), `regles` : bloc de règles du mode (ou None). Retourne le dict du build."""
    obs = obs or {}
    mode = ctx["mode"]
    notes = list(obs.get("notes") or [])
    n_hunters = 6 if mode == "gb" else 3
    hunter_mode = ctx.get("hunter_mode")
    if mode == "hotm" and hunter_mode is None:
        deduit = deduire_hunter_mode(obs)
        if deduit is not None:
            hunter_mode = deduit
            notes.append("hunter_mode déduit")
    exp, plafonds = elements_attendus(mode, regles, hunter_mode, cfg)
    if obs.get("analyse_terminee") is False:
        plafonds.append("analyse en cours")
    oblig = stats_obligatoires(db)
    sjw_vu = obs.get("sjw")
    interdits = []
    alertes = []

    # --- SJW
    sjw = None
    found = {k: None for k in CLES}
    counts = {}
    if mode == "hotm" and hunter_mode is True:
        if sjw_vu:
            alertes.append("SJW vu en mode sans SJW")
    elif sjw_vu:
        if exp["sjw"] is None:
            interdits.append("sjw")
        sjw = {"weapons": [{"id": (w or {}).get("id"), "level": (w or {}).get("level")} for w in list(sjw_vu.get("weapons") or [])[:2]],
               "artifacts": _pieces(sjw_vu.get("artifacts"), SLOTS_ARTEFACT, "set_id"),
               "cores": _pieces(sjw_vu.get("cores"), SLOTS_NOYAU, "id"),
               "stats": dict(sjw_vu.get("stats") or {}),
               "skills": _pieces(sjw_vu.get("skills"), sjw_mod.SKILL_SLOTS, "id"),
               "blessings": [{"id": (b or {}).get("id"), "level": (b or {}).get("level")} for b in list(sjw_vu.get("blessings") or [])[:sjw_mod.NB_BLESSINGS]]}
        while len(sjw["weapons"]) < 2:
            sjw["weapons"].append({"id": None, "level": None})
        while len(sjw["blessings"]) < sjw_mod.NB_BLESSINGS:
            sjw["blessings"].append({"id": None, "level": None})
        nb = {"sjw_weapons": (sum(1 for w in sjw["weapons"] if w["id"]), 2),
              "sjw_artifacts": (_compter_pieces(sjw["artifacts"], "set_id"), 8),
              "sjw_cores": (_compter_pieces(sjw["cores"], "id"), 3),
              "sjw_stats": (len(_stats_lues(sjw["stats"], db, oblig)), len(oblig)),
              "sjw_skills": (_compter_pieces(sjw["skills"], "id"), 6),
              "blessings": (sum(1 for b in sjw["blessings"] if b["id"]), sjw_mod.NB_BLESSINGS)}
        found["sjw"] = True
        for k, (n, t) in nb.items():
            counts[k] = _ratio(n, t)
            found[k] = n == t if t else None
        for k in nb:
            if exp[k] is None:
                found[k] = None
                if nb[k][0]:
                    interdits.append(k)
    elif exp["sjw"] is True:
        found["sjw"] = False
        for k in CLES_SJW[1:]:
            if exp[k] is True:
                found[k] = False
    elif exp["sjw"] == "fac":
        found["sjw"] = None

    # --- chasseurs
    positions = _rang_hunters(n_hunters)
    par_pos = {h.get("position"): h for h in (obs.get("hunters") or []) if isinstance(h, dict)}
    hunters = []
    for p in positions:
        o = par_pos.get(p) or {}
        w = o.get("weapon") or {}
        hunters.append({"position": p, "team_slot": SLOTS_GB[p - 1] if mode == "gb" else None, "id": o.get("id"),
                        "weapon": {"id": w.get("id"), "level": w.get("level")},
                        "artifacts": _pieces(o.get("artifacts"), SLOTS_ARTEFACT, "set_id"),
                        "cores": _pieces(o.get("cores"), SLOTS_NOYAU, "id"), "stats": dict(o.get("stats") or {})})
    for o in (h for h in (obs.get("hunters") or []) if isinstance(h, dict) and h.get("position") is None and h.get("id")):
        if o["id"] in [h["id"] for h in hunters]:
            continue
        libre = next((h for h in hunters if not h["id"]), None)      # place sur la composition inconnue : 1er emplacement libre
        if libre is not None:
            libre.update({"id": o["id"], "stats": dict(o.get("stats") or {}), "position_inconnue": True})
    nh = sum(1 for h in hunters if h["id"])
    na = sum(_compter_pieces(h["artifacts"], "set_id") for h in hunters)
    nc = sum(_compter_pieces(h["cores"], "id") for h in hunters)
    nw = sum(1 for h in hunters if h["weapon"]["id"])
    ns = sum(len(_stats_lues(h["stats"], db, oblig)) for h in hunters)
    for k, n, t in (("hunters", nh, n_hunters), ("weapons", nw, n_hunters), ("artifacts", na, 8 * n_hunters),
                    ("cores", nc, 3 * n_hunters), ("stats", ns, len(oblig) * n_hunters)):
        counts[k] = _ratio(n, t)
        found[k] = (n == t) if t else None
    # --- ombres, successeur, soutien, preuve
    ombres = [{"position": o.get("position", i + 1), "id": o.get("id")} for i, o in enumerate(list(obs.get("shadows") or [])[:3])]
    while len(ombres) < 3:
        ombres.append({"position": len(ombres) + 1, "id": None})
    succ_o = obs.get("successor") or {}
    successor = {"id": succ_o.get("id"), "level": succ_o.get("level"), "stats": dict(succ_o.get("stats") or {})}
    if mode == "bot" and successor["id"] in db.get("remnant_powers", {}):      # BOT : emplacement de droite = puissance rémanente (`remnant_powers.json`)
        successor["category"] = "remnant_powers"
    found["shadows"] = sum(1 for o in ombres if o["id"]) == 3
    counts["shadows"] = _ratio(sum(1 for o in ombres if o["id"]), 3)
    found["successor"] = bool(successor["id"])
    support = obs.get("subjugation_support")
    if support:
        support = list(support)[:3] + [None] * (3 - len(list(support)[:3]))
    proof = obs.get("proof")
    for k, trouve in (("subjugation_support", bool(support and any(support))), ("proof", bool(proof))):
        found[k] = True if trouve else None
    # --- v3 : statues, gemmes, stats du successeur (tous modes, facultatifs, jamais comptés dans le statut)
    statues = [dict(x) for x in (obs.get("statues") or [])][:5] or None
    gems = obs.get("gems") or None
    if gems:
        gems = {"colors": [dict(c) for c in (gems.get("colors") or [])][:5], "bonuses": [dict(b) for b in (gems.get("bonuses") or [])]}
        gems = gems if gems["colors"] or gems["bonuses"] else None
    facultatifs = {"successor_stats": bool(successor["stats"]), "statues": bool(statues), "gems": bool(gems)}
    if proof:
        cout = sum((db.get("proof_modifiers", {}).get((m or {}).get("id"), {}).get("cost_per_level") or 0) * ((m or {}).get("level") or 0)
                   for m in proof.get("modifiers") or [])
        if proof.get("level") is not None and proof.get("modifiers") and cout != proof["level"]:
            notes.append("contrôle preuve")
    for k in ("shadows", "successor"):
        if exp[k] is None and ((k == "shadows" and any(o["id"] for o in ombres)) or (k == "successor" and successor["id"])):
            interdits.append(k)
            found[k] = None
    for k in ("subjugation_support", "proof"):
        if exp[k] is None:
            found[k] = None
    # --- stats facultatives : jamais comptées dans le statut
    # --- doublons et armes exclusives (§2.3)
    ids_h = [h["id"] for h in hunters if h["id"]]
    for i in sorted({i for i in ids_h if ids_h.count(i) > 1}):
        alertes.append(f"doublon : {i}")
    for h in hunters:
        w = db.get("weapons", {}).get(h["weapon"]["id"]) if h["weapon"]["id"] else None
        if w and w.get("hunter_id") and h["id"] and w["hunter_id"] != h["id"]:
            alertes.append("arme d'un autre chasseur")
            break
    for k in sorted(set(interdits)):
        alertes.append(f"élément interdit détecté : {k}")
    element = ctx.get("element")             # v5 : repris de `runs_detail[i].element` (étape 1), jamais lu par l'étape 2
    if element and mode in ("poc", "gb"):
        vus = Counter(db.get("hunters", {}).get(h["id"], {}).get("element") for h in hunters if h["id"])
        vus.pop(None, None)
        premiers = vus.most_common(2)
        if premiers and (len(premiers) == 1 or premiers[0][1] > premiers[1][1]) and premiers[0][0] != element:
            alertes.append("élément de la run incohérent")
    # --- ids inconnus (erreur de contrôle)
    erreurs = []

    def verifier(categorie, identifiant, champ):
        if identifiant and identifiant not in db.get(categorie, {}):
            erreurs.append(f"id inconnu : {champ}/{identifiant}")

    for h in hunters:
        verifier("hunters", h["id"], "hunters")
        verifier("weapons", h["weapon"]["id"], "weapons")
        for a in h["artifacts"]:
            verifier("artifact_sets", a["set_id"], "artifact_sets")
        for c in h["cores"]:
            verifier("cores", c["id"], "cores")
    if sjw:
        for w in sjw["weapons"]:
            verifier("weapons", w["id"], "weapons")
        for a in sjw["artifacts"]:
            verifier("artifact_sets", a["set_id"], "artifact_sets")
        for c in sjw["cores"]:
            verifier("cores", c["id"], "cores")
        for s in sjw["skills"]:
            verifier("sjw_skills", s["id"], "sjw_skills")
        for b in sjw["blessings"]:
            verifier("blessings", b["id"], "blessings")
    for o in ombres:
        verifier("shadows", o["id"], "shadows")
    verifier(successor.get("category") or "successors", successor["id"], successor.get("category") or "successors")
    for s in support or []:
        verifier("subjugation_support", s, "subjugation_support")
    for m in (proof or {}).get("modifiers") or []:
        verifier("proof_modifiers", (m or {}).get("id"), "proof_modifiers")
    if any(a.get("empty") for h in hunters for a in h["artifacts"]) or (sjw and any(a.get("empty") for a in sjw["artifacts"])):
        notes.append("emplacement vide")
    notes += [e for e in erreurs if e not in notes]

    for k in CLES:                      # facultatif non trouvé : null (jamais `false`, jamais compté)
        if exp.get(k) == "fac" and not found.get(k):
            found[k] = None
    # --- statut (§2.2)
    attendus = [k for k, v in exp.items() if v is True]
    rien = not any(found.get(k) for k in CLES) and all(c.startswith("0/") for c in counts.values())
    if obs.get("illisible"):
        statut = "pas_de_build"
        notes.append(f"vidéo illisible : {obs['illisible']}")
    elif rien:
        statut = "pas_de_build"
    elif all(found[k] is True for k in attendus) and not erreurs and not obs.get("conflits"):
        statut = "build_complet"
    else:
        statut = "build_partiel"
    if statut == "build_complet" and plafonds:
        statut = "build_partiel"
        notes += [p for p in plafonds if p not in notes]
    elif statut != "build_complet":
        notes += [p for p in plafonds if p not in notes and statut == "build_partiel"]
    for k in obs.get("conflits") or []:
        n = f"conflit : {k}"
        if n not in notes:
            notes.append(n)
    alertes += [f"reconnaissance faible : {e}" for e in obs.get("faibles") or []]
    for a in alertes:
        if a not in notes:
            notes.append(a)
    confiance = "a_verifier" if alertes else "sur"
    if ctx.get("line_provisional"):          # v4 : ligne non classée, jamais « sûr »
        confiance = "a_verifier"
        if "ligne non classée (score provisoire)" not in notes:
            notes.insert(0, "ligne non classée (score provisoire)")

    return {
        "spec": 3, "run_id": ctx["run_id"], "run_index": ctx["run_index"], "week": ctx["week"], "mode": mode,
        "gate": ctx.get("gate"), "hunter_mode": hunter_mode, "rank": ctx.get("rank"),
        "line_provisional": bool(ctx.get("line_provisional")), "provisional_rank": ctx.get("provisional_rank"), "player": ctx.get("player"),
        "channel_id": ctx.get("channel_id"), "video_id": ctx.get("video_id"), "t_result": ctx.get("t_result"),
        "t_composition": obs.get("t_composition"), "team": ctx.get("team"), "element": ctx.get("element"),
        "rules": {"week": ctx["week"], **{k: (regles or {}).get(k) for k in ("sjw", "sjw_skills", "blessings", "shadows", "successor")}} if regles else None,
        "status": statut, "confidence": confiance, "sjw": sjw, "hunters": hunters,
        "set_bonuses": {**({"sjw": _bonus_sets(sjw["artifacts"], db)} if sjw else {}),
                        **{f"hunter_{h['position']}": _bonus_sets(h["artifacts"], db) for h in hunters}},
        "shadows": ombres, "successor": successor, "subjugation_support": support, "proof": proof,
        "statues": statues, "gems": gems,
        "found": {**found, **{k: (True if v else None) for k, v in facultatifs.items()}}, "counts": counts, "found_at": obs.get("found_at") or {}, "unmatched": list(obs.get("unmatched") or []),
        "attendus": {k: v for k, v in exp.items() if v is not None}, "plafonds": plafonds, "erreurs": erreurs,
        "notes": "; ".join(dict.fromkeys(notes)),
        "sources": [{"type": "video", "video_id": ctx.get("video_id"), "t": obs.get("t_composition")}],
    }


# --- observation des images (§0, §2.1) ------------------------------------------------------------------------------

def _voter(resultats):
    """Vote majoritaire entre plusieurs lectures (images d'un onglet, onglets) : (id | None, conflit, meilleur résultat)."""
    ok = [r["id"] for r in resultats if r["ok"]]
    meilleur = max(resultats, key=lambda r: r["score"]) if resultats else None
    if not ok:
        return None, False, meilleur
    c = Counter(ok).most_common()
    if len(c) > 1 and c[0][1] == c[1][1]:
        return None, True, meilleur
    return c[0][0], False, meilleur


def _par_categorie(cfg, cle, categorie, defaut):
    v = cfg.get(cle, defaut)
    return v.get(categorie, defaut) if isinstance(v, dict) else v


def _zones_cartes(zones_mode):
    pers = (zones_mode or {}).get("personnages") or {}
    return {int(k.split("_")[1]): v["hunter_face"] for k, v in pers.items() if k.startswith("hunter_") and v.get("hunter_face")}


def _retirer_non_reconnu(obs, owner, element, slot=None):
    obs["unmatched"] = [u for u in obs.get("unmatched") or []
                        if not (u.get("owner") == owner and u.get("element") == element and u.get("slot") == slot)]


def _hunters_par_bibliotheque(obs, images, zones_mode, banque, cfg):
    """Cartes de référence (`data/icons/hunters_cartes/`, `portraits.py`), prioritaires sur l'icône (SPEC v5 §2.1) : nom écrit
    (`via_portrait`, écran de stats) > carte > icône. Une carte reconnue l'emporte sur l'icône lue ; note `hunter_N reconnu par sa
    carte, icône lue : <id>`. Sans carte ni nom : l'icône (ou `unmatched`)."""
    import portraits as P
    candidats = [h for h in obs["hunters"] if h.get("position") and not h.get("via_portrait")]
    base = (images.get("personnages") or [])[:1]
    zones = _zones_cartes(zones_mode)
    if not base or not zones:
        return
    pos = sorted(zones)
    crops = dict(zip(pos, P.decouper_cartes(base[0], [zones[p] for p in pos], cfg)))
    obs["_cartes_pleines"] = crops          # carte entière de chaque chasseur : recadrage des `unmatched` en grand (jamais dans le JSON)
    cartes = P.charger_cartes(banque.dossier) if candidats else {}
    if not cartes:
        return
    trouves, m = P.apparier_cartes(crops, cartes, cfg)
    for h in candidats:
        ident = trouves.get(h.get("position"))
        if ident and h.get("id") != ident:
            avant = h.get("id")
            h["id"] = ident
            _retirer_non_reconnu(obs, f"hunter_{h['position']}", "hunters")
            obs["notes"].append(f"hunter_{h['position']} reconnu par sa carte, icône lue : {avant or 'aucune'} ({m[h['position']][ident]} correspondances)")


def _ombres_par_bibliotheque(obs, images, zones_mode, banque, cfg):
    """v33 : ombres reconnues par leur carte (`data/icons/shadows_cartes/<id>.png`, fournies par la discussion 9) : recadrage de chaque
    zone `shadows` de l'onglet personnages comparé aux cartes par points d'intérêt (SIFT + RANSAC, `portraits.apparier_cartes`,
    seuil `portraits.min_corr_ombres`, défaut 25 : le bruit mesuré est ≤ 6, bonnes cartes 47 à 458). Une carte reconnue l'emporte sur la
    lecture par icône (0,6 : peu fiable) ; note si elle la change. Jamais apprise automatiquement (l'identité vient de la base)."""
    import portraits as P
    zones = ((zones_mode or {}).get("personnages") or {}).get("shadows", {}).get("shadows") or []
    base = (images.get("personnages") or [])[:1]
    dossier = getattr(banque, "dossier", None)
    cartes = P.charger_cartes(dossier, P.DOSSIER_OMBRES) if dossier else {}
    if not zones or not base or not cartes:
        return
    w, h = base[0].size
    crops = {i + 1: base[0].crop((round(z[0] * w), round(z[1] * h), round(z[2] * w), round(z[3] * h))) for i, z in enumerate(zones)}
    trouves, m = P.apparier_cartes(crops, cartes, cfg, "min_corr_ombres", 25)
    if not trouves:
        return
    par_pos = {o.get("position"): o for o in obs.get("shadows") or []}
    for pos, ident in sorted(trouves.items()):
        o = par_pos.get(pos)
        if o is None:
            o = {"position": pos, "id": None}
            obs["shadows"] = (obs.get("shadows") or []) + [o]
            par_pos[pos] = o
        if o.get("id") != ident:
            avant = o.get("id")
            o["id"] = ident
            _retirer_non_reconnu(obs, "shadows", "shadows", pos - 1)
            obs["notes"].append(f"shadow_{pos} reconnu par sa carte, icône lue : {avant or 'aucune'} ({m[pos][ident]} correspondances)")
    obs["shadows"] = sorted(obs["shadows"], key=lambda o: o.get("position") or 0)


def _remanente_par_bibliotheque(obs, images, zones_mode, banque, cfg, db):
    """BOT : puissance rémanente (emplacement `successor`) reconnue par sa carte `data/icons/remnant_powers_cartes/<id>.png` (Slagate,
    fournies par la discussion 9), comme les ombres : SIFT + RANSAC, seuil `portraits.min_corr_remanentes` (défaut 12 : l'illustration du
    jeu est un recadrage de plus bas niveau que la carte, bruit mesuré ≤ 6 [À CONFIRMER] sur des images 1080p). Une carte reconnue l'emporte
    sur l'icône. Sans carte, l'id lu par l'icône n'est gardé que s'il existe dans `remnant_powers` (sinon `successors` : autre chose)."""
    import portraits as P
    succ = obs.get("successor") or {}
    if succ.get("id") and succ["id"] not in (db or {}).get("remnant_powers", {}):
        obs["successor"] = {**succ, "id": None}                      # id d'une autre catégorie (successeur de SJW) : pas une puissance rémanente
    zone = ((zones_mode or {}).get("personnages") or {}).get("successor", {}).get("successor")
    base = (images.get("personnages") or [])[:1]
    dossier = getattr(banque, "dossier", None)
    cartes = P.charger_cartes(dossier, "remnant_powers_cartes") if dossier else {}
    if not zone or not base or not cartes:
        return
    w, h = base[0].size
    crop = base[0].crop((round(zone[0] * w), round(zone[1] * h), round(zone[2] * w), round(zone[3] * h)))
    trouves, m = P.apparier_cartes({1: crop}, cartes, cfg, "min_corr_remanentes", 12)
    ident = trouves.get(1)
    if ident:
        avant = (obs.get("successor") or {}).get("id")
        obs["successor"] = {**(obs.get("successor") or {}), "id": ident}
        obs["unmatched"] = [u for u in obs.get("unmatched") or [] if u.get("element") != "successor"]
        obs["notes"].append(f"successor reconnu par sa carte, icône lue : {avant or 'aucune'} ({m[1][ident]} correspondances)")


def apprendre_cartes(obs, images, cfg, banque, mode_cle):
    """Enregistre la carte de chaque chasseur identifié par nom + portrait (jamais écrasée) : bibliothèque apprise."""
    import portraits as P
    zones = _zones_cartes(((cfg.get("zones") or {}).get(mode_cle)) or {})
    base = (images.get("personnages") or [])[:1]
    if not zones or not base:
        return
    pos = sorted(zones)
    crops = P.decouper_cartes(base[0], [zones[p] for p in pos], cfg)
    for h in obs.get("hunters") or []:
        if h.get("via_portrait") and h.get("id") and h.get("position") in zones:
            if P.apprendre(banque.dossier, h["id"], crops[pos.index(h["position"])]):
                obs["notes"].append(f"carte de {h['id']} apprise (data/icons/hunters_cartes)")


def observer(images, mode, cfg, banque, db=None, ctx_note=None):
    """`images` = {onglet: [PIL.Image]} (plusieurs images d'un même onglet : vote ; ombres et successeur : vote entre onglets).
    `mode` = clé de config (`poc`, `bot`, `hotm`, `hotm_sans_sjw`, `gb`). Zones : `cfg.zones.<mode>.<onglet>.<propriétaire>.<élément>`.
    Sans zones pour un onglet : rien n'est cherché, note `zones <mode>/<onglet> non définies`. Seuils, masques et candidats
    réduits : SPEC §2.1. Retourne les observations pour `construire_build`."""
    from icones import ECHELLES, recadrer, reconnaitre
    db = db or {}
    obs = {"sjw": None, "hunters": [], "shadows": [], "successor": None, "subjugation_support": None, "proof": None,
           "unmatched": [], "notes": [], "conflits": [], "faibles": [], "found_at": {}}
    ecart = cfg.get("ecart_icone", 0.05)
    ech_cfg = cfg.get("echelles_icone") or ECHELLES       # liste, ou {catégorie: liste, "defaut": liste}

    def echelles_de(cat):
        e = ech_cfg.get(cat, ech_cfg.get("defaut", ECHELLES)) if isinstance(ech_cfg, dict) else ech_cfg
        return tuple(e)
    onglets = (cfg.get("onglets") or {}).get(mode) or []
    if mode == "gb" and not onglets:
        obs["notes"].append("composition GB non décrite")
        return obs
    zones_mode = (cfg.get("zones") or {}).get(mode) or {}
    lectures = {}          # (propriétaire, élément, emplacement) -> {"cat", "res": [résultats]}

    def reco(img, zone, cat, restreint=None):
        rec = recadrer(img, zone)
        r = reconnaitre(rec, cat, banque, _par_categorie(cfg, "seuil_icone", cat, 0.55), ecart, restreint,
                        echelles_de(cat), (cfg.get("masques") or {}).get(cat))
        r["_img"] = rec                                          # gardé pour le recadrage des `unmatched` (écrit par `calculer`, jamais dans le JSON)
        return r

    def lire(imgs, zone, cat, element, owner, slot=None, restreint=None):
        L = lectures.setdefault((owner, element, slot), {"cat": cat, "res": []})
        L["res"] += [reco(im, zone, cat, restreint) for im in imgs]

    noyaux = lambda slot: {k for k, c in db.get("cores", {}).items() if c.get("slot") == slot} or None
    pieces = lambda slot: {k for k in banque.categorie("artifact_pieces") if k.endswith("--" + slot)}
    qte = {k for k, x in db.get("sjw_skills", {}).items() if x.get("type") == "qte"}
    comp = lambda slot: (qte or None) if slot.startswith("qte") else ({k for k in db.get("sjw_skills", {}) if k not in qte} or None)
    armes_sjw = {k for k, w in db.get("weapons", {}).items() if w.get("kind") == "sung_jinwoo"} or None

    def lire_proprietaire(imgs, nom, z):
        if nom == "sjw":
            for i, zz in enumerate(z.get("weapons") or []):
                lire(imgs, zz, "weapons", "sjw_weapons", "sjw", i, armes_sjw)
            for slot, zz in (z.get("artifacts") or {}).items():
                lire(imgs, zz, "artifact_pieces", "sjw_artifacts", "sjw", slot, pieces(slot))
            for slot, zz in (z.get("cores") or {}).items():
                lire(imgs, zz, "cores", "sjw_cores", "sjw", slot, noyaux(slot))
            for slot, zz in (z.get("skills") or {}).items():
                lire(imgs, zz, "sjw_skills", "sjw_skills", "sjw", slot, comp(slot))
            for i, zz in enumerate(z.get("blessings") or []):
                lire(imgs, zz, "blessings", "blessings", "sjw", i)
        elif nom.startswith("hunter_"):
            if z.get("hunter_face"):
                lire(imgs, z["hunter_face"], "hunters", "hunters", nom)
            if z.get("weapon"):         # armes du chasseur d'abord (`hunter_id`), puis toutes les armes de chasseurs
                hid, _, _ = _voter([reco(im, z["hunter_face"], "hunters") for im in imgs]) if z.get("hunter_face") else (None, 0, 0)
                propres = {k for k, w in db.get("weapons", {}).items() if w.get("hunter_id") == hid and k in banque.categorie("weapons")} if hid else set()
                autres = {k for k, w in db.get("weapons", {}).items() if w.get("kind") == "hunter"} or None
                res = [reco(im, z["weapon"], "weapons", propres) for im in imgs] if propres else []
                ident, _, _ = _voter(res) if res else (None, 0, 0)
                L = lectures.setdefault((nom, "weapons", None), {"cat": "weapons", "res": []})
                L["res"] += res if ident else [reco(im, z["weapon"], "weapons", autres) for im in imgs]
            for slot, zz in (z.get("artifacts") or {}).items():
                lire(imgs, zz, "artifact_pieces", "artifacts", nom, slot, pieces(slot))
            for slot, zz in (z.get("cores") or {}).items():
                lire(imgs, zz, "cores", "cores", nom, slot, noyaux(slot))
        elif nom == "shadows":
            for i, zz in enumerate(z.get("shadows") or []):
                lire(imgs, zz, "shadows", "shadows", "shadows", i)
        elif nom == "successor" and z.get("successor"):
            lire(imgs, z["successor"], "successors", "successor", "successor")
        elif nom == "poc":
            for i, zz in enumerate(z.get("subjugation") or []):
                lire(imgs, zz, "subjugation_support", "subjugation_support", "poc", i)

    vus = 0
    for onglet in onglets:
        zones, imgs = zones_mode.get(onglet), (images or {}).get(onglet) or []
        if not zones:
            obs["notes"].append(f"zones {mode}/{onglet} non définies")
            continue
        if not imgs:
            obs["notes"].append(f"images {mode}/{onglet} absentes")
            continue
        vus += 1
        for nom, z in zones.items():
            lire_proprietaire(imgs, nom, z)
    if not vus and any((zones_mode.get(o) for o in onglets)):
        obs["notes"].append("composition non filmée")
        obs["composition_non_filmee"] = True

    # --- vote et assemblage (SPEC §2.1)
    valeurs = {}
    for cle, L in lectures.items():
        owner, element, slot = cle
        ident, conflit, meilleur = _voter(L["res"])
        valeurs[cle] = ident
        if meilleur and meilleur.get("absente"):
            n = f"icône absente : {L['cat']}"
            if n not in obs["notes"]:
                obs["notes"].append(n)
        elif conflit:
            obs["conflits"].append(element)
        elif ident is None and meilleur:
            obs["unmatched"].append({"element": element, "owner": owner, "slot": slot, "best_id": meilleur["best_id"],
                                     "score": meilleur["score"], "crop": None})
            obs.setdefault("_crops", {})[(owner, element, slot)] = meilleur.get("_img")
        elif ident is not None:
            fort = max(r["score"] for r in L["res"] if r["id"] == ident)
            if fort < _par_categorie(cfg, "seuil_sur", L["cat"], _par_categorie(cfg, "seuil_icone", L["cat"], 0.55) + 0.10) and element not in obs["faibles"]:
                obs["faibles"].append(element)
    get = lambda owner, element: [(k[2], v) for k, v in valeurs.items() if k[0] == owner and k[1] == element]
    if any(k[0] == "sjw" for k in valeurs):
        obs["sjw"] = {"weapons": [{"id": v, "level": None} for _, v in sorted(get("sjw", "sjw_weapons"))],
                      "artifacts": [{"slot": sl, "set_id": v.split("--")[0] if v else None, "level": None} for sl, v in get("sjw", "sjw_artifacts")],
                      "cores": [{"slot": sl, "id": v, "level": None} for sl, v in get("sjw", "sjw_cores")],
                      "skills": [{"slot": sl, "id": v, "level": None} for sl, v in get("sjw", "sjw_skills")],
                      "blessings": [{"id": v, "level": None} for _, v in sorted(get("sjw", "blessings"))], "stats": {}}
    positions = sorted({int(k[0].split("_")[1]) for k in valeurs if k[0].startswith("hunter_")})
    for pos in positions:
        o = f"hunter_{pos}"
        obs["hunters"].append({"position": pos, "id": (get(o, "hunters") or [(None, None)])[0][1],
                               "weapon": {"id": (get(o, "weapons") or [(None, None)])[0][1], "level": None},
                               "artifacts": [{"slot": sl, "set_id": v.split("--")[0] if v else None, "level": None} for sl, v in get(o, "artifacts")],
                               "cores": [{"slot": sl, "id": v, "level": None} for sl, v in get(o, "cores")], "stats": {}})
    _hunters_par_bibliotheque(obs, images, zones_mode, banque, cfg)
    if any(k[0] == "shadows" for k in valeurs):
        obs["shadows"] = [{"position": i + 1, "id": v} for i, v in sorted(get("shadows", "shadows"))]
    _ombres_par_bibliotheque(obs, images, zones_mode, banque, cfg)
    if any(k[0] == "successor" for k in valeurs):
        obs["successor"] = {"id": get("successor", "successor")[0][1], "level": None}
    if mode == "bot":
        _remanente_par_bibliotheque(obs, images, zones_mode, banque, cfg, db)
    if any(k[0] == "poc" for k in valeurs):
        obs["subjugation_support"] = [v for _, v in sorted(get("poc", "subjugation_support"))]
    # pièce isolée : un set porté par une seule pièce parmi au moins 4 reconnues (SPEC §2.1 ; valeur gardée)
    for nom, arts in [("sjw", (obs["sjw"] or {}).get("artifacts") or [])] + [(f"hunter_{h['position']}", h["artifacts"]) for h in obs["hunters"]]:
        c = Counter(a["set_id"] for a in arts if a["set_id"])
        if sum(c.values()) >= 4:
            for a in arts:
                if a["set_id"] and c[a["set_id"]] == 1:
                    obs["notes"].append(f"pièce isolée : {a['slot']} ({nom})")
    return obs


# --- lecture des classements, calcul, rapport ------------------------------------------------------------------------------

def modes_du_top(week, racine=RACINE, cfg=None):
    """[(dossier_mode, ligne)] des lignes rank 1..top des fichiers poc, bot, gb et hotm-gate-<n> (jamais `inconnue`).
    v4 : un mode sans aucune ligne classée (et `config.builds_provisoires`) donne ses `top` premières lignes `a_verifier`
    par score provisoire (BOT du plus court au plus long, autres du plus haut au plus bas) : copies avec
    `line_provisional` true, `rank` null, `provisional_rank` 1..top."""
    cfg = cfg or charger_config()
    cfg_top = cfg["top"]
    dossier = Path(racine) / "data" / "runs" / week
    sortie = []
    for f in sorted(dossier.glob("*.json")):
        nom = f.stem
        if nom.startswith("_") or nom == "hotm-gate-inconnue" or not (nom in ("poc", "bot", "gb") or nom.startswith("hotm-gate-")):
            continue
        lignes = [r for r in _json(f, []) if isinstance(r, dict)]
        classees = [r for r in lignes if r.get("rank") is not None and r["rank"] <= cfg_top]
        if classees:
            sortie += [(nom, r) for r in classees]
        elif cfg.get("builds_provisoires"):
            cand = [r for r in lignes if r.get("confidence") == "a_verifier" and isinstance((r.get("score") or {}).get("total"), (int, float))]
            # v34 : l'ordre du fichier fait foi (`classement.ordonner`, rang prudent des chronos BOT incomplets) : pas de nouveau tri par score
            for i, r in enumerate(cand[:cfg_top], 1):
                sortie.append((nom, dict(r, rank=None, line_provisional=True, provisional_rank=i)))
    return sortie


def supprimer_provisoires(week, attendus, racine=RACINE):
    """v4 : supprime les builds `line_provisional` (et leurs recadrages) qui ne font plus partie de la sélection
    (mode devenu classé, ligne sortie du top). `attendus` : ensemble de chemins de builds provisoires courants."""
    base = Path(racine) / "data" / "builds" / week
    supprimes = []
    for f in sorted(base.glob("*/*.json")):
        b = _json(f, None)
        if b and b.get("line_provisional") and f.resolve() not in attendus:
            for u in b.get("unmatched") or []:
                if u.get("crop"):
                    (Path(racine) / u["crop"]).unlink(missing_ok=True)
            f.unlink()
            supprimes.append(f)
    return supprimes


def contextes(nom_mode, ligne, week):
    """Un contexte par run de la ligne (`runs_detail`) : un build par run."""
    details = ligne.get("runs_detail") or [{}]
    for i, d in enumerate(details, 1):
        vid = d.get("video_id") or ligne.get("video_id")
        # vidéo à plusieurs runs : les écrans de la run i sont ceux qui suivent le résultat de la run précédente de la même vidéo
        avant = [x.get("t") for x in details[:i - 1] if (x.get("video_id") or ligne.get("video_id")) == vid and isinstance(x.get("t"), (int, float))]
        yield {"t_debut": int(max(avant)) if avant and isinstance(d.get("t"), (int, float)) and max(avant) < d["t"] else 0,
               "run_id": ligne["run_id"], "run_index": i, "week": week, "mode": ligne.get("mode") or nom_mode.split("-")[0],
               "dossier": nom_mode, "gate": ligne.get("gate"), "hunter_mode": ligne.get("hunter_mode"), "rank": ligne.get("rank"),
               "line_provisional": bool(ligne.get("line_provisional")), "provisional_rank": ligne.get("provisional_rank"),
               "player": ligne.get("player"), "channel_id": ligne.get("channel_id"),
               "video_id": d.get("video_id") or ligne.get("video_id"), "t_result": d.get("t"), "team": d.get("team"),
               "element": d.get("element"),
               "published_at": d.get("published_at") or ligne.get("published_at"), "score": ligne.get("score"), "lang": ligne.get("lang")}


def analyse_terminee(processed, vid):
    p = (processed or {}).get(vid) or {}
    return (p.get("pc") or {}).get("tri4") == "fait" or (bool(p) and p.get("status") != "en_cours")


def calculer(week, racine=RACINE, cfg=None, banque=None, fournisseur=None, force=False):
    """Recalcule les builds du top 10 de `week`. `fournisseur(ctx)` -> {onglet: [images PIL]} (tris 3-4 du PC) ;
    sans lui, aucune image : `pas_de_build`. Un build `build_complet` existant n'est pas retraité (sauf `force`).
    Retourne la liste des builds (dicts) écrits ou conservés."""
    racine = Path(racine)
    cfg = cfg or charger_config()
    db = charger_db(racine)
    rules = _json(racine / "data" / "rules" / f"{week}.json", None)
    processed = _json(racine / "data" / "processed.json", {})
    if banque is None:
        from icones import Banque
        banque = Banque(racine)
    builds = []
    selection = modes_du_top(week, racine, cfg)
    supprimer_provisoires(week, {(racine / "data" / "builds" / week / n / f"{c['run_id']}-{c['run_index']}.json").resolve()
                                 for n, l in selection if l.get("line_provisional") for c in contextes(n, l, week)}, racine)
    for nom_mode, ligne in selection:
        for ctx in contextes(nom_mode, ligne, week):
            chemin = racine / "data" / "builds" / week / nom_mode / f"{ctx['run_id']}-{ctx['run_index']}.json"
            ancien = _json(chemin, None)
            if ancien and ancien.get("status") == "build_complet" and not force:
                builds.append(ancien)
                continue
            images, extra = {}, {}
            cle_cfg = "hotm_sans_sjw" if ctx["mode"] == "hotm" and ctx.get("hunter_mode") is True else ctx["mode"]
            if fournisseur and (cfg.get("zones") or {}).get(cle_cfg):       # sans zones définies : rien à chercher, pas de téléchargement
                res = fournisseur(ctx)
                images, extra = res if isinstance(res, tuple) else (res, {})
            obs = observer(images, cle_cfg, cfg, banque, db)
            if extra.get("ecrans"):
                import ecrans_hors_compo
                ecrans_hors_compo.integrer(obs, extra["ecrans"], db, cfg)
                apprendre_cartes(obs, images, cfg, banque, cle_cfg)
            if extra.get("t_composition"):
                obs["t_composition"] = extra["t_composition"]
            if extra.get("erreur"):
                obs["notes"].append(f"images de composition non disponibles : {extra['erreur']}")
            elif not images:
                obs["notes"].append("images de composition non disponibles")
            obs["analyse_terminee"] = analyse_terminee(processed, ctx["video_id"])
            b = construire_build(ctx, obs, regles_mode(rules, ctx["mode"]), cfg, db)
            b["dossier"] = nom_mode
            ecrire_crops(b, obs, racine, chemin, **(cfg.get("crops") or {}))
            if b["status"] == "pas_de_build" and not b["notes"]:
                b["notes"] = "aucun élément trouvé"
            chemin.parent.mkdir(parents=True, exist_ok=True)
            texte = json.dumps(b, ensure_ascii=False, indent=2) + "\n"
            if not chemin.exists() or chemin.read_text(encoding="utf-8") != texte:
                chemin.write_text(texte, encoding="utf-8")
            builds.append(b)
    for nom_mode, ligne in selection:        # v33 : build d'une run qui n'existe plus dans la ligne (ex. nh2D : 2 runs du Personal Record -> 1 run filmée)
        n = len(ligne.get("runs_detail") or [{}])
        for f in (racine / "data" / "builds" / week / nom_mode).glob(f"{ligne['run_id']}-*.json"):
            suffixe = f.stem[len(ligne["run_id"]) + 1:]
            if suffixe.isdigit() and int(suffixe) > n:
                f.unlink()
    for b in controler_chasseurs_communs(builds):            # v5 : contrôle entre les builds d'une même ligne
        f = racine / "data" / "builds" / week / (b.get("dossier") or b["mode"]) / f"{b['run_id']}-{b['run_index']}.json"
        f.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ecrire_rapport(week, builds, racine)
    return builds


NOTE_COMMUN = "chasseur commun aux 2 runs : "


def controler_chasseurs_communs(builds):
    """SPEC v5 §2.3 : POC et GB, deux builds de la même ligne (2 groupes / 2 équipes) avec un chasseur en commun : le jeu l'interdit
    (erreur de rattachement ou de lecture) -> `a_verifier` sur les deux builds, note `chasseur commun aux 2 runs : <id>`. Idempotent ;
    retourne les builds modifiés."""
    par_ligne = {}
    for b in builds:
        if b.get("mode") in ("poc", "gb"):
            par_ligne.setdefault((b.get("dossier"), b["run_id"]), []).append(b)
    modifies = []
    for liste in par_ligne.values():
        for i, a in enumerate(liste):
            for b in liste[i + 1:]:
                if a.get("run_index") == b.get("run_index"):
                    continue
                communs = sorted({h["id"] for h in a["hunters"] if h.get("id")} & {h["id"] for h in b["hunters"] if h.get("id")})
                for ident in communs:
                    for x in (a, b):
                        note = NOTE_COMMUN + ident
                        if note not in x["notes"].split("; "):
                            x["notes"] = "; ".join(n for n in (x["notes"], note) if n)
                            x["confidence"] = "a_verifier"
                            if x not in modifies:
                                modifies.append(x)
    return modifies


def ecrire_crops(b, obs, racine, chemin_build, taille=480, qualite=88):
    """SPEC §125 : recadrage de chaque icône non reconnue (`unmatched`) en JPEG ≤ `taille` px (480 ; 96 px avant, trop petit pour identifier
    une carte) dans `_crops/` à côté du build ; `crop` = chemin relatif à la racine du dépôt. Sert à montrer l'image vue dans la vidéo
    quand aucun nom n'est sûr (PPTX) et à la discussion 9 pour fournir les cartes. Un chasseur non reconnu : sa carte entière (`_cartes_pleines`)."""
    crops = obs.get("_crops") or {}
    cartes = obs.get("_cartes_pleines") or {}
    for u in b.get("unmatched") or []:
        img = crops.get((u.get("owner"), u.get("element"), u.get("slot")))
        if u.get("element") == "hunters" and str(u.get("owner") or "").startswith("hunter_"):
            try:
                img = cartes.get(int(u["owner"].split("_")[1]), img)
            except ValueError:
                pass
        if img is None:
            continue
        nom = "_".join(str(x) for x in (f"{b['run_id']}-{b['run_index']}", u.get("element"), u.get("owner"), u.get("slot")) if x is not None)
        dossier = Path(chemin_build).parent / "_crops"
        dossier.mkdir(parents=True, exist_ok=True)
        im = img.convert("RGB")
        im.thumbnail((taille, taille))
        f = dossier / f"{nom}.jpg"
        im.save(f, quality=qualite)
        u["crop"] = f.relative_to(racine).as_posix()


def regles_recentes(racine, mode):
    """Dernier fichier `data/rules/*.json` : (semaine, bloc du mode) ou (None, None). Sert au seul diagnostic `build_essai`."""
    for f in sorted((Path(racine) / "data" / "rules").glob("*.json"), reverse=True):
        r = regles_mode(_json(f, {}), mode)
        if r is not None:
            return f.stem, r
    return None, None


def build_essai(video_id, mode, racine=RACINE, cfg=None, banque=None, fournisseur=None, t_result=None, hunter_mode=None):
    """Diagnostic : build d'une seule vidéo hors classement (rang `None`), pour essayer les zones sur une vraie vidéo. Retourne
    le build ; `unmatched` et `found` montrent ce qui est reconnu. N'écrit rien dans `data/builds`."""
    racine = Path(racine)
    cfg = cfg or charger_config()
    db = charger_db(racine)
    if banque is None:
        from icones import Banque
        banque = Banque(racine)
    ctx = {"run_id": f"essai-{video_id}", "run_index": 1, "week": "essai", "mode": mode, "gate": None, "hunter_mode": hunter_mode, "rank": None,
           "player": None, "channel_id": None, "video_id": video_id, "t_result": t_result, "team": None}
    cle_cfg = "hotm_sans_sjw" if mode == "hotm" and hunter_mode is True else mode
    res = fournisseur(ctx) if fournisseur else ({}, {})
    images, extra = res if isinstance(res, tuple) else (res, {})
    obs = observer(images, cle_cfg, cfg, banque, db)
    if extra.get("ecrans"):
        import ecrans_hors_compo
        ecrans_hors_compo.integrer(obs, extra["ecrans"], db, cfg)
        apprendre_cartes(obs, images, cfg, banque, cle_cfg)
    obs["t_composition"] = extra.get("t_composition")
    obs["ocr_resume"] = extra.get("ocr_resume")
    if extra.get("erreur"):
        obs["notes"].append(f"images de composition non disponibles : {extra['erreur']}")
    elif not images:
        obs["notes"].append("composition non filmée")
    obs["analyse_terminee"] = True
    semaine, regles = regles_recentes(racine, mode)
    if regles is not None:
        obs["notes"].append(f"essai : règles de la semaine {semaine}")
    b = construire_build(ctx, obs, regles, cfg, db)
    if obs.get("ocr_resume"):
        b["ocr_resume"] = obs["ocr_resume"]                 # diagnostic de l'essai seulement : textes lus par l'OCR rapide
    return b


def rapport(week, builds, fichiers_pptx=()):
    """Texte du rapport (SPEC §6)."""
    L = [f"# Rapport des builds — semaine {week}", ""]
    if not builds:
        L += ["Aucune ligne classée (rank 1-10) : aucun build.", ""]
    for dossier in sorted({b.get("dossier") or b["mode"] for b in builds}):
        bm = [b for b in builds if (b.get("dossier") or b["mode"]) == dossier]
        c = Counter(b["status"] for b in bm)
        prov = any(b.get("line_provisional") for b in bm)
        L += [f"## {dossier}" + (" — CLASSEMENT PROVISOIRE (lignes non classées, score provisoire)" if prov else ""), "", f"- build_complet : {c['build_complet']} · build_partiel : {c['build_partiel']} · pas_de_build : {c['pas_de_build']}"]
        av = [b for b in bm if b["confidence"] == "a_verifier"]
        L.append("- À vérifier : " + (", ".join(f"{b['run_id']}-{b['run_index']} ({b['notes']})" for b in av) if av else "aucun"))
        um = Counter(u["element"] for b in bm for u in b["unmatched"])
        L.append("- Icônes non reconnues : " + (", ".join(f"{k} ×{v}" for k, v in sorted(um.items())) if um else "aucune"))
        chemins = {}
        for b in bm:        # v5 : recadrages non reconnus par catégorie (chemins), pour la discussion 9
            for u in b["unmatched"]:
                if u.get("crop"):
                    chemins.setdefault(u["element"], []).append(u["crop"])
        for k in sorted(chemins):
            L.append(f"  - {k} : " + ", ".join(dict.fromkeys(chemins[k])))
        inter = [f"{b['run_id']}-{b['run_index']} : {n}" for b in bm for n in b["notes"].split("; ") if n.startswith("élément interdit")]
        L.append("- Éléments interdits détectés : " + ("; ".join(inter) if inter else "aucun"))
        err = [f"{b['run_id']}-{b['run_index']} : {e}" for b in bm for e in b.get("erreurs", [])]
        L.append("- **Erreurs (id introuvables)** : " + ("; ".join(err) if err else "aucune"))
        L.append("")
    L += ["## PowerPoint", ""] + ([f"- {f}" for f in fichiers_pptx] if fichiers_pptx else ["Aucun fichier produit."]) + [""]
    return "\n".join(L)


def ecrire_rapport(week, builds, racine=RACINE, fichiers_pptx=()):
    chemin = Path(racine) / "data" / "builds" / week / "_rapport.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(rapport(week, builds, fichiers_pptx), encoding="utf-8")
    return chemin


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Étape 2 : calcul des builds du top 10 (SPEC_ETAPE2)")
    ap.add_argument("semaine", nargs="?")
    ap.add_argument("--force", action="store_true", help="retraite aussi les builds déjà complets")
    a = ap.parse_args(argv)
    from semaine import id_semaine, maintenant
    week = a.semaine or id_semaine(maintenant())
    builds = calculer(week, force=a.force)
    c = Counter(b["status"] for b in builds)
    print(f"Semaine {week} : {len(builds)} build(s) — {dict(c)}")


if __name__ == "__main__":
    main()
