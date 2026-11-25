"""SPEC_ETAPE2 v5 (tests 19 à 22) : cartes prioritaires, règles `null`, chasseur commun, élément ; images de composition gardées ; rapport."""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest

import builds as B
import composition
from test_etape2 import CFG, DB, HUNTERS, RACINE, REGLES_TOUT, build, ctx, obs_hunters, obs_sjw, pptx

cv2 = pytest.importorskip("cv2")
from PIL import Image


# --- 19 : nom écrit > carte > icône ---------------------------------------------------------------------------------------

def _capture(mode):
    return Image.open(RACINE / f"docs/essais/composition/{mode}_personnages_ja.png").convert("RGB")


def _lancer_cartes(obs):
    B._hunters_par_bibliotheque(obs, {"personnages": [_capture("poc")]}, CFG["zones"]["poc"], SimpleNamespace(dossier=RACINE / "data/icons"), CFG)
    return obs


def test_19_carte_et_icone_en_desaccord_la_carte_l_emporte():
    o = _lancer_cartes({"hunters": [{"position": 1, "id": "autre-chasseur"}, {"position": 2, "id": None}, {"position": 3, "id": None}],
                        "unmatched": [{"owner": "hunter_2", "element": "hunters", "slot": None}, {"owner": "hunter_3", "element": "hunters", "slot": None}],
                        "notes": []})
    assert [h["id"] for h in o["hunters"]] == ["esil-radiru", "christopher-reed", None]
    assert any(n.startswith("hunter_1 reconnu par sa carte, icône lue : autre-chasseur") for n in o["notes"])
    assert any(n.startswith("hunter_2 reconnu par sa carte, icône lue : aucune") for n in o["notes"])
    # aucune carte ni nom : l'icône non reconnue reste `unmatched`
    assert o["unmatched"] == [{"owner": "hunter_3", "element": "hunters", "slot": None}]


def test_19_le_nom_ecrit_prime_sur_la_carte():
    o = _lancer_cartes({"hunters": [{"position": 1, "id": "id-par-le-nom", "via_portrait": True}], "unmatched": [], "notes": []})
    assert o["hunters"][0]["id"] == "id-par-le-nom" and o["notes"] == []


def test_19_ombres_meme_priorite():
    obs = {"shadows": [{"position": 2, "id": "brute"}], "unmatched": [{"owner": "shadows", "element": "shadows", "slot": 0}], "notes": []}
    B._ombres_par_bibliotheque(obs, {"personnages": [_capture("poc")]}, CFG["zones"]["poc"], SimpleNamespace(dossier=RACINE / "data/icons"), CFG)
    assert [(o["position"], o["id"]) for o in obs["shadows"]] == [(1, "beste"), (2, "greed")]
    assert any("shadow_2 reconnu par sa carte, icône lue : brute" in n for n in obs["notes"]) and obs["unmatched"] == []


# --- 20 : règle null = inconnu ; false = interdit ---------------------------------------------------------------------------

def _interdit(regles, obs=None):
    b = build(ctx("poc"), obs or {**obs_hunters(3), "sjw": obs_sjw()}, regles)
    return [n for n in b["notes"].split("; ") if n.startswith("élément interdit")]


def test_20_regle_null_pas_d_alerte_interdit():
    assert _interdit({"sjw": None, "sjw_skills": None, "blessings": None, "shadows": None, "successor": None}) == []
    assert _interdit({"sjw": True, "sjw_skills": None, "blessings": None, "shadows": None, "successor": None}) == []


def test_20_regle_false_et_element_vu_a_verifier():
    b = build(ctx("poc"), {**obs_hunters(3), "sjw": obs_sjw()}, {**REGLES_TOUT, "shadows": False, "successor": False})
    assert b["confidence"] == "a_verifier"
    assert "élément interdit détecté : shadows" in b["notes"] and "élément interdit détecté : successor" in b["notes"]
    assert "élément interdit détecté : sjw" in _interdit({**REGLES_TOUT, "sjw": False, "sjw_skills": False, "blessings": False})


# --- 21 : chasseur commun aux 2 runs --------------------------------------------------------------------------------------

def _deux_runs(mode, ids_a, ids_b):
    def b(i, ids):
        o = obs_hunters(3)
        for h, ident in zip(o["hunters"], ids):
            h["id"] = ident
        x = build(ctx(mode, run_index=i, run_id=f"{mode}-2026-11-12-AAAAAAAAAAA", team=i), o, REGLES_TOUT)
        x["dossier"] = mode
        return x
    return [b(1, ids_a), b(2, ids_b)]


def test_21_chasseur_commun_a_verifier_sur_les_deux_builds():
    a, b = _deux_runs("gb", HUNTERS[:3], [HUNTERS[2], HUNTERS[3], HUNTERS[4]])
    modifies = B.controler_chasseurs_communs([a, b])
    assert len(modifies) == 2
    for x in (a, b):
        assert x["confidence"] == "a_verifier" and f"chasseur commun aux 2 runs : {HUNTERS[2]}" in x["notes"]
    assert B.controler_chasseurs_communs([a, b]) == []                          # idempotent
    assert a["notes"].count("chasseur commun") == 1


def test_21_runs_distinctes_ou_autre_mode_sans_alerte():
    a, b = _deux_runs("poc", HUNTERS[:3], HUNTERS[3:6])
    assert B.controler_chasseurs_communs([a, b]) == [] and a["confidence"] == "sur"
    a, b = _deux_runs("bot", HUNTERS[:3], HUNTERS[:3])
    assert B.controler_chasseurs_communs([a, b]) == []


# --- 22 : élément de la run -----------------------------------------------------------------------------------------------

def _hunters_par_element():
    par = {}
    for i, h in DB["hunters"].items():
        par.setdefault(h.get("element"), []).append(i)
    return par


def test_22_element_repris_de_runs_detail():
    ligne = {"run_id": "gb-2026-11-12-X", "mode": "gb", "runs_detail": [{"video_id": "v", "t": 5, "team": None, "element": "fire"}, {"video_id": "v", "t": 9}]}
    c = list(B.contextes("gb", ligne, "2026-11-12"))
    assert [x["element"] for x in c] == ["fire", None]
    assert build(ctx("gb", element="fire"), obs_hunters(6), REGLES_TOUT)["element"] == "fire"
    assert build(ctx("gb"), obs_hunters(6), REGLES_TOUT)["element"] is None


def test_22_element_incoherent_avec_les_chasseurs_reconnus():
    par = _hunters_par_element()
    feu, eau = par["fire"][:3], par["water"][:3]
    o = obs_hunters(3)
    for h, ident in zip(o["hunters"], feu):
        h["id"] = ident
    assert "élément de la run incohérent" in build(ctx("poc", element="water"), o, REGLES_TOUT)["notes"]
    assert build(ctx("poc", element="water"), o, REGLES_TOUT)["confidence"] == "a_verifier"
    assert "incohérent" not in build(ctx("poc", element="fire"), o, REGLES_TOUT)["notes"]
    assert "incohérent" not in build(ctx("poc", element=None), o, REGLES_TOUT)["notes"]
    o2 = obs_hunters(3)                                                    # 1 feu + 1 eau + 1 inconnu : pas de majorité
    for h, ident in zip(o2["hunters"], [feu[0], eau[0], feu[1]]):
        h["id"] = ident
    o2["hunters"][2]["id"] = None
    assert "incohérent" not in build(ctx("poc", element="light"), o2, REGLES_TOUT)["notes"]


def test_22_slide_1_run_element_quand_le_groupe_est_inconnu():
    from pptx.util import Pt  # noqa: F401
    b = build(ctx("gb", element="fire", team=None, run_index=1), obs_hunters(6), REGLES_TOUT)
    prs, _ = pptx([b], "fr")
    textes = [sh.text_frame.text for sl in prs.slides for sh in sl.shapes if sh.has_text_frame]
    assert any("Run Feu (1/1)" in t for t in textes)
    b2 = build(ctx("gb", element="fire", team=2), obs_hunters(6), REGLES_TOUT)
    prs, _ = pptx([b2], "fr")
    assert any("Groupe 2" in sh.text_frame.text for sl in prs.slides for sh in sl.shapes if sh.has_text_frame)


# --- images de composition gardées pour les zones ; rapport des recadrages non reconnus ------------------------------------------

def test_images_de_composition_auto(tmp_path):
    petit, grand = Image.new("RGB", (640, 360), "red"), Image.new("RGB", (2400, 1350), "blue")
    ecrits = composition.sauver_images_auto(tmp_path, "poc", "VID00000001", {"personnages": [petit, grand], "noyaux": [petit]}, [4, 12], CFG)
    noms = sorted(f.name for f in ecrits)
    assert noms == ["VID00000001_noyaux_4.png", "VID00000001_personnages_4.png"]
    with Image.open(tmp_path / "docs/essais/composition/auto/poc/VID00000001_personnages_4.png") as im:
        assert im.size == (1920, 1080)                                          # la meilleure résolution, réduite à 1920 px
    assert composition.sauver_images_auto(tmp_path, "poc", "VID00000001", {"personnages": [grand]}, [9, 12], CFG) == []   # jamais écrasée
    assert composition.sauver_images_auto(tmp_path, "bot", "VID00000002", {"personnages": [grand]}, [4, 12], CFG) == []   # BOT : zones calibrées
    for k in range(4):                                                          # plafond par (mode, onglet)
        composition.sauver_images_auto(tmp_path, "gb", f"V{k:010d}", {"personnages": [petit]}, [1], CFG)
    assert len(list((tmp_path / "docs/essais/composition/auto/gb").glob("*_personnages_*.png"))) == CFG["extraction"].get("auto_max_par_onglet", 3)


def test_rapport_liste_les_recadrages_non_reconnus_par_categorie():
    b = build(ctx("poc"), obs_hunters(3, unmatched=[{"element": "weapons", "owner": "hunter_1", "slot": None, "best_id": None, "crop": "data/builds/s/poc/a-1_weapons.jpg"},
                                                  {"element": "shadows", "owner": "shadows", "slot": 2, "best_id": None, "crop": "data/builds/s/poc/a-1_shadows_2.jpg"}]), REGLES_TOUT)
    b["dossier"] = "poc"
    texte = B.rapport("2026-11-12", [b])
    assert "  - weapons : data/builds/s/poc/a-1_weapons.jpg" in texte and "  - shadows : data/builds/s/poc/a-1_shadows_2.jpg" in texte


def test_build_d_une_run_disparue_de_la_ligne_est_supprime(tmp_path):
    import shutil
    for rel in ("data/runs/2026-11-12", "data/rules", "data/db"):
        shutil.copytree(RACINE / rel, tmp_path / rel)
    ligne = next(l for l in json.loads((tmp_path / "data/runs/2026-11-12/gb.json").read_text(encoding="utf-8")) if l.get("player") == "SlayOnLow")
    dossier = tmp_path / "data/builds/2026-11-12/gb"
    dossier.mkdir(parents=True)
    ancien = dossier / f"{ligne['run_id']}-2.json"
    ancien.write_text("{}", encoding="utf-8")
    B.calculer("2026-11-12", racine=tmp_path, cfg=CFG, banque=object())
    assert len(ligne["runs_detail"]) == 1 and not ancien.exists() and (dossier / f"{ligne['run_id']}-1.json").exists()


def test_crops_orphelins_supprimes(tmp_path):
    import json
    import builds as B
    base = tmp_path / "data" / "builds" / "2026-11-12" / "bot"
    (base / "_crops").mkdir(parents=True)
    garde, orphelin = base / "_crops" / "a.jpg", base / "_crops" / "vieux.jpg"
    garde.write_bytes(b"x")
    orphelin.write_bytes(b"x")
    (base / "bot-1.json").write_text(json.dumps({"unmatched": [{"crop": "data/builds/2026-11-12/bot/_crops/a.jpg"}]}), encoding="utf-8")
    assert [p.name for p in B.supprimer_crops_orphelins("2026-11-12", tmp_path)] == ["vieux.jpg"]
    assert garde.exists() and not orphelin.exists()
