"""SPEC v32 : RC confirmé par le Personal Record (contrôle de somme sauté) ; zone du Player's Score (1080p, nh2D7xZ7dOQ)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
from classement import calculer
from test_classement import CONFIG, HORLOGE, T, W, lec, lire, preparer

IMAGE = Path(__file__).resolve().parents[2] / "docs/essais/ocr/nh2D7xZ7dOQ_recherche_275_gb_results.jpg"


def monde(results_detail=None, results_notes=None, results_conf="a_verifier", record_conf="sur", total=332, hud=133):
    det = {"damage_exact": True, "player_score": 141642312, "hunter_ranks_lus": 6, "rc_images": 7, "final_images": 6, "hud_rage_count": hud}
    det.update(results_detail or {})
    notes = ["lecture fusionnée (8 images)", "conflit de lecture : player_score"] if results_notes is None else results_notes
    rec = lambda team, rc, dmg: lec("nh2D", "UCS", "gb", rc, team=team, score_source="record", damage=dmg, exact=True, confidence=record_conf,
                                    detail={"total_rage_count": total, "time_left": "6d 9h", "damage_step": 1e10, "damage_exact": False}, t=2)
    res = lec("nh2D", "UCS", "gb", 165, damage=13763121797048, exact=False, confidence=results_conf, t=270, stage=None, detail=det, notes=notes)
    return preparer([rec(1, 167, 17.28 * T), rec(2, 165, 15.55 * T), res])


def run_nh2d(**kw):
    d = monde(**kw)
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    return l


def test_nh2d_rc_confirme_par_le_personal_record():
    l = run_nh2d()
    assert (l["score"]["total"], l["confidence"], l["rank"]) == (165, "sur", 1)
    (r,) = l["runs_detail"]
    assert (r["team"], r["damage"], r["damage_exact"]) == (2, 13763121797048, False)
    assert "groupe 2 d'après le Personal Record (RC égal)" in l["notes"] and "une seule run" in l["notes"]
    assert "RC confirmé par le Personal Record ; contrôle de somme impossible (Player's Score illisible)" in l["notes"]


def test_conditions_non_remplies_restent_a_verifier():
    assert run_nh2d(hud=170)["confidence"] == "a_verifier"                                        # (c) HUD : RC > RC du Results
    assert run_nh2d(results_detail={"rc_images": 1})["confidence"] == "a_verifier"               # (a) une seule image
    assert run_nh2d(results_notes=["conflit de lecture : player_score", "conflit de lecture : rage_count"])["confidence"] == "a_verifier"
    assert run_nh2d(results_notes=["conflit de lecture : player_score", "écart titre/écran : titre 159"])["confidence"] == "a_verifier"  # (c) titre
    assert run_nh2d(total=330)["confidence"] == "a_verifier"                                      # (b) Total ≠ somme des groupes
    assert run_nh2d(record_conf="a_verifier")["confidence"] == "a_verifier"                       # (b) record non sûr
    assert run_nh2d(results_notes=["contrôle GB : somme fausse"], results_detail={"player_score": 4141642312433})["confidence"] == "a_verifier"


def test_jamais_de_player_score_deduit():
    """Final − somme des Hunter Rank (2 125 582 312 433 avec les lectures du vote) n'est jamais écrit comme Player's Score."""
    l = run_nh2d()
    assert "2125582312433" not in str(l) and "2,125,582,312,433" not in str(l)


def test_zone_joueur_exclut_le_portrait_de_sjw():
    x, y, w, h = CONFIG["gb"]["zones"]["joueur"]
    assert x >= 0.15 and x + w <= 0.27 and 0.24 <= y and y + h <= 0.30


@pytest.mark.skipif(not shutil.which("tesseract") or not IMAGE.exists(), reason="tesseract ou capture absents")
def test_zone_joueur_lit_le_debut_du_nombre_sur_le_results_1080p():
    from PIL import Image, ImageOps
    im = Image.open(IMAGE).convert("L")
    W_, H_ = im.size
    x, y, w, h = CONFIG["gb"]["zones"]["joueur"]
    z = ImageOps.autocontrast(im.crop((int(x * W_), int(y * H_), int((x + w) * W_), int((y + h) * H_))))
    z.resize((z.width * 3, z.height * 3)).save(IMAGE.with_suffix(".zone.tmp.png"))
    try:
        txt = subprocess.run(["tesseract", str(IMAGE.with_suffix(".zone.tmp.png")), "-", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789,."],
                             capture_output=True, text=True).stdout.strip()
    finally:
        IMAGE.with_suffix(".zone.tmp.png").unlink(missing_ok=True)
    chiffres = re.sub(r"\D", "", txt)
    assert chiffres.startswith("4141") and chiffres.endswith("433"), txt     # début du nombre lu (l'ancienne zone le perdait)
    # repère de contrôle seulement (jamais une valeur écrite) : Final − 6 Hunter Rank lus sur la capture = Player's Score
    rangs = [9924529913136, 819761049651, 386652675192, 265010218097, 155539274175, 69986354364]
    assert 15763121797048 - sum(rangs) == 4141642312433


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
