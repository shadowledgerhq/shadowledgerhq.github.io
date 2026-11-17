"""SPEC v33 : zones final / rang_5 / rang_6 recalées (nh2D7xZ7dOQ, 1080p) ; contrôle de somme normal ; (c) HUD ≤ RC ; garde-fou du vote
(un dégât non contrôlé ne départage jamais une égalité de RC)."""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pc
import pytest
import classement
import ocr_ecrans
import pc
from classement import calculer
from test_classement import CONFIG as CFG1, HORLOGE, T, W, lec, lire, preparer
from test_gb import meta as meta_gb
from test_tri34 import CONFIG
from test_v15 import VIDE
from test_v32 import run_nh2d

OCR = Path(__file__).resolve().parents[2] / "docs/essais/ocr"
IMAGE = OCR / "nh2D7xZ7dOQ_recherche_275_gb_results.jpg"
RANGS = [9924529913136, 819761049651, 386652675192, 265010218097, 155539274175, 69986354364]
Z_NH2D = {**VIDE, "_layout": "standard", "boss": "Giant Statue", "joueur": "4,141,642,312,433", "rang_1": "9,924,529,913,136",
          "rang_2": "819,761,049,651", "rang_3": "386,652,675,192", "rang_4": "265,010,218,097", "rang_5": "155,539,274,175",
          "rang_6": "69,986,354,364", "final": "15,763,121,797,048", "rage": "165", "temps": "03:00"}


def test_somme_exacte_de_la_capture_nh2d():
    """Repère de la capture : Player's Score + 6 Hunter Rank = Final Score exactement."""
    assert 4141642312433 + sum(RANGS) == 15763121797048


def test_nh2d_controle_normal_sur_exact_sans_note_v32():
    texte = (OCR / "nh2D7xZ7dOQ_recherche_275_gb_results.txt").read_text(encoding="utf-8", errors="replace")
    m = {**meta_gb("v"), "lang": "en", "mode_guess": ["gb"]}
    ls = [ocr_ecrans.lectures_depuis_texte(texte, m, CONFIG, "video-complete", t, Z_NH2D)[0] for t in (273, 274, 275)]
    (res,) = [l for l in pc.fusionner_ecrans([], "v", ls, CONFIG) if l["score"] is not None]
    assert (res["score"], res["damage"], res["confidence"], res["exact"]) == (165, 15763121797048, "sur", True)
    assert res["detail"]["damage_exact"] is True and not any("Personal Record" in n or "contrôle GB" in n for n in res["notes"])


def test_zones_recalees_hors_portrait():
    z = CFG1["gb"]["zones"]
    assert z["final"][0] >= 0.30 and z["rang_5"][0] >= 0.14 and z["rang_6"][0] >= 0.14       # numéros hors du portrait des chasseurs 5 et 6
    assert z["final"][3] <= 0.06 and z["rang_5"][3] <= 0.041 and z["rang_6"][3] <= 0.043


@pytest.mark.skipif(not (shutil.which("tesseract") and shutil.which("ffmpeg") and IMAGE.exists()), reason="tesseract, ffmpeg ou capture absents")
def test_zones_reelles_sur_le_results_1080p_de_nh2d():
    o = pc.Outils({**CFG1["pc"], "images": {**CFG1["pc"]["images"], "ffmpeg": "ffmpeg", "tesseract": "tesseract"}})
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(IMAGE, Path(t) / "i.jpg")
        z = pc.lire_zones_results(o, str(Path(t) / "i.jpg"), CFG1, "gb_results", "")
    n = lambda k: ocr_ecrans._nombre_zone(z[k])
    assert n("final") == 15763121797048 and n("rang_5") == 155539274175 and n("rang_6") == 69986354364


def test_c_hud_egal_ou_inferieur_ne_contredit_pas():
    for hud in (133, 164, 165):
        assert run_nh2d(hud=hud)["confidence"] == "sur", hud
    assert run_nh2d(hud=166)["confidence"] == "a_verifier"


def _gb(vid, ch, rc, dmg, exact, jour=13):
    return lec(vid, ch, "gb", rc, jour=jour, damage=dmg, exact=exact, detail={"damage_exact": exact})


def test_degat_non_controle_ne_departage_pas_une_egalite_de_rc():
    """Deux joueurs à 165 RC : le dégât lu sans contrôle (vote 5/3) ne fait pas le rang ; la ligne passe a_verifier."""
    d = preparer([_gb("v1", "UCA", 165, 15763121797048, False), _gb("v2", "UCB", 165, 13763121797048, True, jour=14)])
    calculer(W, d, CFG1, HORLOGE)
    a, b = lire(d, "gb")
    par = {x["channel_id"]: x for x in (a, b)}
    assert par["UCA"]["confidence"] == "a_verifier" and "égalité départagée par un dégât non contrôlé" in par["UCA"]["notes"]
    assert (par["UCB"]["confidence"], par["UCB"]["rank"]) == ("sur", 1)


def test_egalite_de_rc_avec_degats_controles_reste_departagee():
    d = preparer([_gb("v1", "UCA", 165, 15 * T, True), _gb("v2", "UCB", 165, 13 * T, True, jour=14)])
    calculer(W, d, CFG1, HORLOGE)
    r = {x["channel_id"]: x["rank"] for x in lire(d, "gb")}
    assert r == {"UCA": 1, "UCB": 2}


def test_pas_d_egalite_pas_de_changement():
    d = preparer([_gb("v1", "UCA", 165, 15 * T, False), _gb("v2", "UCB", 160, 13 * T, True, jour=14)])
    calculer(W, d, CFG1, HORLOGE)
    assert {x["channel_id"]: (x["rank"], x["confidence"]) for x in lire(d, "gb")} == {"UCA": (1, "sur"), "UCB": (2, "sur")}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


def test_resume_gb_en_tete_du_bloc():
    """v33 : une ligne par vidéo GB traitée ce jour (Results lu ?, RC, statut, groupe, élément)."""
    import donnees
    d = preparer([])
    d.ecrire("processed.json", {"v1": {"week": W, "modes": ["gb"], "status": "termine", "pc": {"date": "2026-11-17", "results_lus": [[270, 312]]}},
                                "v2": {"week": W, "modes": ["gb"], "status": "en_cours", "pc": {"date": "2026-11-17", "results_lus": []}},
                                "v3": {"week": W, "modes": ["gb"], "status": "termine", "pc": {"date": "2026-11-16", "results_lus": [[1, 2]]}}})
    d.ecrire(f"runs/{W}/gb.json", [{"video_id": "v1", "video_ids": ["v1"], "player": "SlayOnLow", "score": {"total": 165}, "confidence": "sur",
                                   "notes": "lecture fusionnée (8 images)", "runs_detail": [{"team": 2, "element": "light"}]}])
    lignes = pc.resume_gb(d, W, "2026-11-17")
    assert lignes == ["- Résumé GB : v1 · SlayOnLow · Results lu (270-312 s) · 165 RC sûr · groupe 2 · light",
                      "- Résumé GB : v2 · aucun Results lu · pas classée"]
