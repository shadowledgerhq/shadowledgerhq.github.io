"""v37.2 : Results GB reconnu sans « Final Score » (bandeau « New Record Achieved! »)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ocr_ecrans

TEXTE = open(Path(__file__).resolve().parents[2] / "docs/essais/ocr/libelles_inconnus/CnFBmHEzZww_502.txt", encoding="utf-8").read()


def test_results_sans_final_score_reconnu():
    assert ocr_ecrans.detecter(TEXTE) == "gb_results_partiel"


def test_hud_et_texte_quelconque_inchanges():
    assert ocr_ecrans.detecter("Hunter Rank seul") is None
    assert ocr_ecrans.detecter("Player's Score 5 681 614 211 887") is None
