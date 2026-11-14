"""Tests de l'étape 2 (SPEC_ETAPE2 §7) sur des données de test : sans zones d'onglets, les vrais builds sortent pas_de_build."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import builds as B
import export_pptx as P
import icones

RACINE = B.RACINE
DB = B.charger_db(RACINE)
CFG = B.charger_config()
HUNTERS = [h for h in DB["hunters"]][:6]
SETS = [s for s in DB["artifact_sets"]][:3]
OMBRES = list(DB["shadows"])[:3]
SUCC = next(iter(DB["successors"]))
CORES = {}
for cid, c in DB["cores"].items():
    CORES.setdefault(c["slot"], cid)
STATS_OBLIG = B.stats_obligatoires(DB)
STATS = {k: (1000 if DB["stats"][k]["display"] == "raw" else {"percent": 50.0, "rating": 19191}) for k in STATS_OBLIG}
REGLES_TOUT = {"sjw": True, "sjw_skills": True, "blessings": True, "shadows": True, "successor": True}
SKILLS = list(DB["sjw_skills"])[:6]
BLESS = list(DB["blessings"])[:8]
WEAPONS = [w for w, o in DB["weapons"].items() if not o.get("hunter_id")][:2]


def ctx(mode="hotm", hunter_mode=None, **kw):
    c = {"run_id": f"{mode}-2026-11-19-ABCDEFGHIJK", "run_index": 1, "week": "2026-11-19", "mode": mode, "gate": 3 if mode == "hotm" else None,
         "hunter_mode": hunter_mode, "rank": 1, "player": "Testeur", "channel_id": "UCtest", "video_id": "ABCDEFGHIJK", "t_result": 183, "team": 1}
    c.update(kw)
    return c


def hunter_complet(pos):
    return {"position": pos, "id": HUNTERS[pos - 1], "weapon": {"id": WEAPONS[0] if pos == 1 else None, "level": None},
            "artifacts": [{"slot": s, "set_id": SETS[0]} for s in B.SLOTS_ARTEFACT],
            "cores": [{"slot": s, "id": CORES[s]} for s in B.SLOTS_NOYAU], "stats": dict(STATS)}


def obs_hunters(n=3, **kw):
    hs = [hunter_complet(p) for p in range(1, n + 1)]
    # les armes: chacune une arme sans chasseur exclusif
    for h in hs:
        h["weapon"] = {"id": WEAPONS[0], "level": None}
    o = {"hunters": hs, "shadows": [{"position": i + 1, "id": s} for i, s in enumerate(OMBRES)], "successor": {"id": SUCC, "level": None},
         "unmatched": [], "notes": [], "conflits": [], "analyse_terminee": True, "t_composition": [4, 12]}
    o.update(kw)
    return o


def obs_sjw():
    return {"weapons": [{"id": w} for w in WEAPONS], "artifacts": [{"slot": s, "set_id": SETS[1]} for s in B.SLOTS_ARTEFACT],
            "cores": [{"slot": s, "id": CORES[s]} for s in B.SLOTS_NOYAU], "stats": dict(STATS),
            "skills": [{"slot": s, "id": SKILLS[i]} for i, s in enumerate(B.sjw_mod.SKILL_SLOTS)], "blessings": [{"id": b} for b in BLESS]}


def build(c, obs, regles, cfg=CFG):
    return B.construire_build(c, obs, regles, cfg, DB)


def row_pour(b):
    return {"run_id": b["run_id"], "channel": "Chaîne test", "published_at": "2026-11-19T10:00:00Z", "score": {"total": 90000, "unit": "points"},
            "runs_detail": [{"video_id": b["video_id"]}]}


def pptx(buildsf, lang="fr", row=None):
    tmp = Path(tempfile.mkdtemp()) / "t.pptx"
    n = P.generer_fichier(buildsf, row or row_pour(buildsf[0]), lang, tmp, RACINE, DB, CFG)
    from pptx import Presentation
    return Presentation(str(tmp)), n


def textes(prs):
    return [sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame]


# --- §7 ---------------------------------------------------------------------------------------------------------------

def test_1_hotm_sans_sjw_complet():
    b = build(ctx(hunter_mode=True), obs_hunters(), {**REGLES_TOUT})
    assert b["status"] == "build_complet" and b["sjw"] is None and b["confidence"] == "sur"
    assert all(b["found"][k] is None for k in B.CLES_SJW)
    prs, n = pptx([b])
    assert n == 7                                         # titre + 3 chasseurs + ombres + successeur + Sources


def test_2_hotm_avec_sjw_absent_partiel():
    b = build(ctx(hunter_mode=False), obs_hunters(), REGLES_TOUT)
    assert b["status"] == "build_partiel" and b["found"]["sjw"] is False


def test_2b_hotm_avec_sjw_complet():
    b = build(ctx(hunter_mode=False), obs_hunters(sjw=obs_sjw()), REGLES_TOUT)
    assert b["status"] == "build_complet", (b["status"], b["counts"], b["notes"])
    assert b["set_bonuses"]["sjw"][0]["pieces"] == 8
    prs, n = pptx([b])
    assert n == 10                                        # titre, SJW, 3 chasseurs, ombres, successeur, compétences, bénédictions, Sources


def test_3_hotm_sans_sjw_mais_sjw_vu():
    b = build(ctx(hunter_mode=True), obs_hunters(sjw=obs_sjw()), REGLES_TOUT)
    assert b["status"] == "build_complet" and b["confidence"] == "a_verifier" and "SJW vu en mode sans SJW" in b["notes"]


def test_4_hotm_hunter_mode_inconnu_plafond():
    b = build(ctx(hunter_mode=None), obs_hunters(), REGLES_TOUT)
    assert b["status"] == "build_partiel" and "hunter_mode inconnu" in b["notes"] and b["hunter_mode"] is None
    d = build(ctx(hunter_mode=None), obs_hunters(hunter_mode_indices={"onglets": 4, "benedictions": False}), REGLES_TOUT)
    assert d["hunter_mode"] is True and "hunter_mode déduit" in d["notes"] and d["status"] == "build_complet"
    e = build(ctx(hunter_mode=None), obs_hunters(sjw=obs_sjw(), hunter_mode_indices={"onglets": 5}), REGLES_TOUT)
    assert e["hunter_mode"] is False


def test_5_poc_regles_inconnues_partiel():
    b = build(ctx("poc"), obs_hunters(sjw=obs_sjw()), None)
    assert b["status"] == "build_partiel" and "règles poc inconnues" in b["notes"]
    assert B.regles_mode({"modes": {"poc": None}}, "poc") is None
    assert B.regles_mode({"modes": {"bot_season": REGLES_TOUT, "bot": None}}, "bot") == REGLES_TOUT


def test_6_aucun_element_pas_de_build():
    b = build(ctx("bot"), {"notes": ["zones bot/sjw non définies"], "analyse_terminee": True}, REGLES_TOUT)
    assert b["status"] == "pas_de_build" and "zones bot/sjw non définies" in b["notes"]
    g = build(ctx("gb"), B.observer({}, "gb", CFG, icones.Banque(RACINE), DB), None)
    assert g["status"] == "pas_de_build" and "composition GB non décrite" in g["notes"] and len(g["hunters"]) == 6
    i = build(ctx("bot"), {"illisible": "vidéo privée"}, REGLES_TOUT)
    assert i["status"] == "pas_de_build" and "vidéo privée" in i["notes"]


def test_7_video_a_deux_runs_un_fichier():
    b1 = build(ctx("gb", run_index=1, team=1), obs_hunters(6), REGLES_TOUT)
    b2 = build(ctx("gb", run_index=2, team=2), obs_hunters(6), REGLES_TOUT)
    prs, n = pptx([b1, b2])
    sources = [t for t in textes(prs) if t == "Sources"]
    assert len(sources) == 1 and prs.slides[-1].shapes.title is None
    assert n == 2 * 12 + 1                                # GB : titre, SJW, 6 chasseurs, ombres, successeur, compétences, bénédictions (x2) + Sources


def test_8_nom_fr_vide_en_italique():
    sans_fr = next((i for i, o in DB["successors"].items() if not o["name"].get("fr") and o["name"].get("en")), None)
    assert sans_fr, "aucun successeur sans nom FR dans la base de test"
    en = DB["successors"][sans_fr]["name"]["en"]
    assert P.nom_affiche(DB, "successors", sans_fr, "fr") == (en + " (EN)", True)
    assert P.nom_affiche(DB, "successors", sans_fr, "en") == (en, False)
    assert P.nom_affiche(DB, "stats", "hp", "fr") == ("hp", True)           # tout vide : l'id, en italique
    o = obs_hunters(successor={"id": sans_fr, "level": None})
    b = build(ctx(hunter_mode=True), o, REGLES_TOUT)
    prs, _ = pptx([b], "fr")
    assert en + " (EN)" in textes(prs)
    prs, _ = pptx([b], "en")
    assert en in textes(prs) and en + " (EN)" not in textes(prs)


def test_9_unmatched_case_icone_inconnue_non_comptee():
    o = obs_hunters()
    o["hunters"][1]["id"] = None
    o["unmatched"] = [{"element": "hunters", "owner": "hunter_2", "slot": None, "best_id": HUNTERS[1], "score": 0.61, "crop": None}]
    b = build(ctx(hunter_mode=True), o, REGLES_TOUT)
    assert b["status"] == "build_partiel" and b["counts"]["hunters"] == "2/3"
    prs, _ = pptx([b], "fr")
    assert "Icône inconnue" in textes(prs)
    prs, _ = pptx([b], "en")
    assert "Unknown icon" in textes(prs)


# --- autres règles du §1-2 -----------------------------------------------------------------------------------------------

def test_interdit_doublon_arme_et_id_inconnu():
    b = build(ctx("bot"), obs_hunters(sjw=obs_sjw()), {**REGLES_TOUT, "sjw": False})
    assert b["confidence"] == "a_verifier" and "élément interdit détecté : sjw" in b["notes"]
    o = obs_hunters()
    o["hunters"][1]["id"] = o["hunters"][0]["id"]
    assert "doublon : " + o["hunters"][0]["id"] in build(ctx(hunter_mode=True), o, REGLES_TOUT)["notes"]
    o = obs_hunters()
    o["hunters"][0]["id"] = "n-existe-pas"
    b = build(ctx(hunter_mode=True), o, REGLES_TOUT)
    assert b["status"] == "build_partiel" and b["erreurs"] == ["id inconnu : hunters/n-existe-pas"]
    autre = next((w for w, ob in DB["weapons"].items() if ob.get("hunter_id")), None)
    if autre:
        o = obs_hunters()
        o["hunters"][0]["weapon"]["id"] = autre
        o["hunters"][0]["id"] = next(h for h in HUNTERS if h != DB["weapons"][autre]["hunter_id"])
        assert "arme d'un autre chasseur" in build(ctx(hunter_mode=True), o, REGLES_TOUT)["notes"]


def test_stats_facultatives_et_plafond_analyse():
    o = obs_hunters()
    for h in o["hunters"]:
        h["stats"] = {}
    assert build(ctx(hunter_mode=True), o, REGLES_TOUT)["status"] == "build_partiel"          # stats_obligatoires = true
    assert build(ctx(hunter_mode=True), o, REGLES_TOUT, {**CFG, "stats_obligatoires": False})["status"] == "build_complet"
    o = obs_hunters(analyse_terminee=False)
    b = build(ctx(hunter_mode=True), o, REGLES_TOUT, {**CFG, "stats_obligatoires": False})
    assert b["status"] == "build_partiel" and "analyse en cours" in b["notes"]


def test_emplacement_vide_compte_comme_lu_et_preuve():
    o = obs_hunters()
    o["hunters"][0]["artifacts"][7] = {"slot": "earrings", "set_id": None, "empty": True}
    b = build(ctx(hunter_mode=True), o, REGLES_TOUT)
    assert "emplacement vide" in b["notes"] and b["counts"]["artifacts"] == "24/24"
    pm = next(k for k, v in DB["proof_modifiers"].items() if v.get("cost_per_level"))
    o = obs_hunters(proof={"level": 1, "modifiers": [{"id": pm, "level": 1}]})
    assert "contrôle preuve" in build(ctx(hunter_mode=True), o, REGLES_TOUT)["notes"] or DB["proof_modifiers"][pm]["cost_per_level"] == 1


def test_reconnaissance_par_icone_et_seuils():
    from PIL import Image, ImageDraw
    banque = icones.Banque(RACINE)

    def motif(forme, n=64):
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        (d.rectangle if forme == "carre" else d.ellipse)((4, 4, n - 4, n - 4), fill=(200, 60, 60, 255))
        d.line((4, 4, n - 4, n - 4) if forme == "carre" else (n // 2, 4, n // 2, n - 4), fill=(20, 220, 240, 255), width=n // 8)
        d.ellipse((n // 2 - 6, n // 2 + 8, n // 2 + 6, n // 2 + 20), fill=(250, 250, 40, 255))
        return im

    def ecran(forme):
        fond = Image.effect_noise((100, 100), 60).convert("RGBA")
        fond.alpha_composite(motif(forme, 56), (22, 18))
        return fond
    banque.ajouter("hunters", "a", motif("carre", 128))
    banque.ajouter("hunters", "b", motif("rond", 128))
    r = icones.reconnaitre(ecran("carre"), "hunters", banque, 0.55, 0.05, restreint={"a", "b"})
    assert r["ok"] and r["id"] == "a", r
    assert icones.reconnaitre(ecran("rond"), "hunters", banque, 0.55, 0.05, restreint={"a", "b"})["id"] == "b"
    bruit = Image.effect_noise((100, 100), 80).convert("RGBA")
    r2 = icones.reconnaitre(bruit, "hunters", banque, 0.55, 0.05, restreint={"a", "b"})
    assert not r2["ok"] and r2["id"] is None and r2["best_id"] in ("a", "b")
    # observer : sans zone -> rien cherché, note ; avec zone -> reconnu (structure zones.<mode>.<onglet>.<propriétaire>.<élément>)
    obs = B.observer({"personnages": [ecran("carre")]}, "bot", CFG, banque, DB)
    assert "zones bot/personnages non définies" in obs["notes"] and not obs["hunters"]
    cfg = {**CFG, "zones": {"bot": {"personnages": {"hunter_1": {"hunter": [0, 0, 1, 1]}}}}}
    obs = B.observer({"personnages": [ecran("carre"), ecran("carre")]}, "bot", cfg, banque, DB)
    assert len(obs["hunters"]) == 1 and obs["hunters"][0]["position"] == 1
    assert obs["hunters"][0]["id"] == "a" and not obs["unmatched"]
    obs = B.observer({"personnages": [Image.effect_noise((100, 100), 80).convert("RGBA")]}, "bot", cfg, banque, DB)
    assert obs["hunters"][0]["id"] is None and obs["unmatched"][0]["owner"] == "hunter_1"


def test_noyaux_reels_bot_japonais():
    """Capture réelle (docs/essais/composition/bot_noyaux_ja.png, 1158×651) : zones de `etape2.json`, vraie banque d'icônes."""
    from PIL import Image
    chemin = RACINE / "docs" / "essais" / "composition" / "bot_noyaux_ja.png"
    if not chemin.exists():
        return
    obs = B.observer({"noyaux": [Image.open(chemin)]}, "bot", CFG, icones.Banque(RACINE), DB)
    par = {h["position"]: {c["slot"]: c["id"] for c in h["cores"]} for h in obs["hunters"]}
    assert par[1]["mind"] == "ferocious-protectors-desire" and par[3]["mind"] == "ferocious-protectors-desire"
    assert par[2]["mind"] == "ancient-wraiths-obession" and par[2]["body"] == "nameless-demons-horn"
    assert par[1]["spirit"] == par[2]["spirit"] == "teeth-of-the-watcher"
    assert par[1]["body"] is None and par[3]["body"] is None and par[3]["spirit"] is None      # emplacements vides : jamais devinés
    assert {u["slot"] for u in obs["unmatched"] if u["owner"] == "hunter_1"} == {"body"}
    assert {c["slot"]: c["id"] for c in obs["sjw"]["cores"]}["mind"] == "ancient-wraiths-obession"


def test_calculer_sur_arbre_de_test():
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "data" / "runs" / "2026-11-19").mkdir(parents=True)
        (t / "data" / "db").mkdir(parents=True)
        for f in (RACINE / "data" / "db").glob("*.json"):
            (t / "data" / "db" / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        (t / "data" / "rules").mkdir()
        (t / "data" / "rules" / "2026-11-19.json").write_text(json.dumps({"week": "2026-11-19", "modes": {"hotm": REGLES_TOUT, "poc": None}}), encoding="utf-8")
        ligne = lambda rid, mode, rang, **kw: {"run_id": rid, "week": "2026-11-19", "mode": mode, "channel_id": "UC1", "player": "P", "video_id": "VID" + rid[-3:],
                                               "rank": rang, "score": {"total": 2, "runs": [1, 1], "unit": "damage"},
                                               "runs_detail": [{"video_id": "VID" + rid[-3:], "t": 100, "team": 1}, {"video_id": "VID" + rid[-3:], "t": 200, "team": 2}], **kw}
        (t / "data" / "runs" / "2026-11-19" / "poc.json").write_text(json.dumps([ligne("poc-x-001", "poc", 1), ligne("poc-x-002", "poc", None)]), encoding="utf-8")
        (t / "data" / "runs" / "2026-11-19" / "hotm-gate-3.json").write_text(json.dumps([ligne("hotm-x-003", "hotm", 2, gate=3, hunter_mode=True, runs_detail=[{"video_id": "VID003", "t": 50}])]), encoding="utf-8")
        (t / "data" / "runs" / "2026-11-19" / "hotm-gate-inconnue.json").write_text(json.dumps([ligne("hotm-x-004", "hotm", 1)]), encoding="utf-8")
        res = B.calculer("2026-11-19", t, CFG, banque=icones.Banque(t))
        assert sorted((b["run_id"], b["run_index"]) for b in res) == [("hotm-x-003", 1), ("poc-x-001", 1), ("poc-x-001", 2)]
        assert (t / "data" / "builds" / "2026-11-19" / "poc" / "poc-x-001-2.json").exists()
        assert all(b["status"] == "pas_de_build" for b in res)
        rap = (t / "data" / "builds" / "2026-11-19" / "_rapport.md").read_text(encoding="utf-8")
        assert "pas_de_build : 2" in rap and "Erreurs (id introuvables)" in rap
        # idempotent + un build complet n'est pas retraité
        f = t / "data" / "builds" / "2026-11-19" / "hotm-gate-3" / "hotm-x-003-1.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["status"] = "build_complet"
        d["notes"] = "gardé"
        f.write_text(json.dumps(d), encoding="utf-8")
        B.calculer("2026-11-19", t, CFG, banque=icones.Banque(t))
        assert json.loads(f.read_text(encoding="utf-8"))["notes"] == "gardé"
        fichiers = P.exporter("2026-11-19", t)
        assert len(fichiers) == 4 and (t / "exports" / "2026-11-19" / "builds" / "poc" / "01-VID001-fr.pptx").exists()
        assert (t / "exports" / "2026-11-19" / "builds" / "hotm-gate-3" / "02-VID003-en.pptx").exists()
        assert "01-VID001-fr.pptx" in (t / "data" / "builds" / "2026-11-19" / "_rapport.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
