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
    for nom in ("hunters", "weapons", "artifact_sets", "cores", "shadows", "successors", "sjw_skills", "blessings",
                "subjugation_support", "proof_modifiers", "stats"):
        db[nom] = {o["id"]: o for o in _json(Path(racine) / "data" / "db" / f"{nom}.json", []) if isinstance(o, dict) and "id" in o}
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
    if sjw_possible:
        sjw_on = bool(r and r.get("sjw")) if r is not None else None
        if r is None or not sjw_regle:
            etat = "fac"
        else:
            etat = True if sjw_on else None
        for k in CLES_SJW:
            exp[k] = etat
        if etat is True:
            exp["sjw_stats"] = stats
            exp["sjw_skills"] = True if r.get("sjw_skills") else None
            exp["blessings"] = True if r.get("blessings") else None
        elif etat == "fac":
            exp["sjw_stats"] = "fac"
    for k, cle_regle in (("shadows", "shadows"), ("successor", "successor")):
        exp[k] = "fac" if r is None else (True if r.get(cle_regle) else None)
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
    verifier("successors", successor["id"], "successors")
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

    return {
        "spec": 3, "run_id": ctx["run_id"], "run_index": ctx["run_index"], "week": ctx["week"], "mode": mode,
        "gate": ctx.get("gate"), "hunter_mode": hunter_mode, "rank": ctx.get("rank"), "player": ctx.get("player"),
        "channel_id": ctx.get("channel_id"), "video_id": ctx.get("video_id"), "t_result": ctx.get("t_result"),
        "t_composition": obs.get("t_composition"), "team": ctx.get("team"),
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
    echelles = tuple(cfg.get("echelles_icone") or ECHELLES)
    onglets = (cfg.get("onglets") or {}).get(mode) or []
    if mode == "gb" and not onglets:
        obs["notes"].append("composition GB non décrite")
        return obs
    zones_mode = (cfg.get("zones") or {}).get(mode) or {}
    lectures = {}          # (propriétaire, élément, emplacement) -> {"cat", "res": [résultats]}

    def reco(img, zone, cat, restreint=None):
        return reconnaitre(recadrer(img, zone), cat, banque, _par_categorie(cfg, "seuil_icone", cat, 0.55), ecart, restreint,
                           echelles, (cfg.get("masques") or {}).get(cat))

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
    if any(k[0] == "shadows" for k in valeurs):
        obs["shadows"] = [{"position": i + 1, "id": v} for i, v in sorted(get("shadows", "shadows"))]
    if any(k[0] == "successor" for k in valeurs):
        obs["successor"] = {"id": get("successor", "successor")[0][1], "level": None}
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

def modes_du_top(week, racine=RACINE):
    """[(dossier_mode, ligne)] des lignes rank 1..top des fichiers poc, bot, gb et hotm-gate-<n> (jamais `inconnue`)."""
    cfg_top = charger_config()["top"]
    dossier = Path(racine) / "data" / "runs" / week
    sortie = []
    for f in sorted(dossier.glob("*.json")):
        nom = f.stem
        if nom.startswith("_") or nom == "hotm-gate-inconnue" or not (nom in ("poc", "bot", "gb") or nom.startswith("hotm-gate-")):
            continue
        for r in _json(f, []):
            if r.get("rank") is not None and r["rank"] <= cfg_top:
                sortie.append((nom, r))
    return sortie


def contextes(nom_mode, ligne, week):
    """Un contexte par run de la ligne (`runs_detail`) : un build par run."""
    details = ligne.get("runs_detail") or [{}]
    for i, d in enumerate(details, 1):
        yield {"run_id": ligne["run_id"], "run_index": i, "week": week, "mode": ligne.get("mode") or nom_mode.split("-")[0],
               "dossier": nom_mode, "gate": ligne.get("gate"), "hunter_mode": ligne.get("hunter_mode"), "rank": ligne.get("rank"),
               "player": ligne.get("player"), "channel_id": ligne.get("channel_id"),
               "video_id": d.get("video_id") or ligne.get("video_id"), "t_result": d.get("t"), "team": d.get("team"),
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
    for nom_mode, ligne in modes_du_top(week, racine):
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
            if extra.get("t_composition"):
                obs["t_composition"] = extra["t_composition"]
            if extra.get("erreur"):
                obs["notes"].append(f"images de composition non disponibles : {extra['erreur']}")
            elif not images:
                obs["notes"].append("images de composition non disponibles")
            obs["analyse_terminee"] = analyse_terminee(processed, ctx["video_id"])
            b = construire_build(ctx, obs, regles_mode(rules, ctx["mode"]), cfg, db)
            b["dossier"] = nom_mode
            if b["status"] == "pas_de_build" and not b["notes"]:
                b["notes"] = "aucun élément trouvé"
            chemin.parent.mkdir(parents=True, exist_ok=True)
            texte = json.dumps(b, ensure_ascii=False, indent=2) + "\n"
            if not chemin.exists() or chemin.read_text(encoding="utf-8") != texte:
                chemin.write_text(texte, encoding="utf-8")
            builds.append(b)
    ecrire_rapport(week, builds, racine)
    return builds


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
    obs["t_composition"] = extra.get("t_composition")
    if extra.get("erreur"):
        obs["notes"].append(f"images de composition non disponibles : {extra['erreur']}")
    elif not images:
        obs["notes"].append("composition non filmée")
    obs["analyse_terminee"] = True
    semaine, regles = regles_recentes(racine, mode)
    if regles is not None:
        obs["notes"].append(f"essai : règles de la semaine {semaine}")
    return construire_build(ctx, obs, regles, cfg, db)


def rapport(week, builds, fichiers_pptx=()):
    """Texte du rapport (SPEC §6)."""
    L = [f"# Rapport des builds — semaine {week}", ""]
    if not builds:
        L += ["Aucune ligne classée (rank 1-10) : aucun build.", ""]
    for dossier in sorted({b.get("dossier") or b["mode"] for b in builds}):
        bm = [b for b in builds if (b.get("dossier") or b["mode"]) == dossier]
        c = Counter(b["status"] for b in bm)
        L += [f"## {dossier}", "", f"- build_complet : {c['build_complet']} · build_partiel : {c['build_partiel']} · pas_de_build : {c['pas_de_build']}"]
        av = [b for b in bm if b["confidence"] == "a_verifier"]
        L.append("- À vérifier : " + (", ".join(f"{b['run_id']}-{b['run_index']} ({b['notes']})" for b in av) if av else "aucun"))
        um = Counter(u["element"] for b in bm for u in b["unmatched"])
        L.append("- Icônes non reconnues : " + (", ".join(f"{k} ×{v}" for k, v in sorted(um.items())) if um else "aucune"))
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
