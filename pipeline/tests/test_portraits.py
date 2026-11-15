"""Liaison écran de stats -> carte de la composition (portraits.py), sur la vraie capture POC v0tuXJNxudk (15/11/2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import builds as B
import ecrans_hors_compo as H
import portraits as P

RACINE = B.RACINE
CFG = B.charger_config()
DOSSIER = RACINE / "docs" / "essais" / "builds" / "v0tuXJNxudk_ocr"


def test_portrait_stats_trouve_la_carte_2():
    from PIL import Image
    stats = Image.open(DOSSIER / "v0tuXJNxudk_hors-compo_16_stats.jpg").convert("RGB")
    compo = Image.open(DOSSIER / "v0tuXJNxudk_compo_personnages_0.jpg").convert("RGB")
    zones = [CFG["zones"]["poc"]["personnages"][f"hunter_{i}"]["hunter_face"] for i in (1, 2, 3)]
    notes = P.notes_cartes(P.decouper_portrait(stats, CFG), P.decouper_cartes(compo, zones, CFG))
    assert P.choisir(notes, CFG) == 1, notes


def test_choisir_refuse_les_cas_ambigus():
    assert P.choisir([30, 28, 2], CFG) is None        # 2e trop proche
    assert P.choisir([10, 1, 0], CFG) is None         # trop peu de correspondances
    assert P.choisir([], CFG) is None
    assert P.choisir([3, 80, 5], CFG) == 1


def test_integrer_place_le_chasseur_a_sa_position():
    db = B.charger_db(RACINE)
    texte = (DOSSIER / "v0tuXJNxudk_hors-compo_16_stats.txt").read_text(encoding="utf-8")
    obs = {"hunters": [{"position": p, "id": None, "weapon": {}, "artifacts": [], "cores": []} for p in (1, 2, 3)], "notes": []}
    H.integrer(obs, [("stats", texte), ("stats_position", "[2]")], db, CFG)
    par = {h["position"]: h for h in obs["hunters"]}
    assert par[2]["id"] == "christopher-reed" and par[2]["stats"] and not par[1]["id"], obs["hunters"]
    assert len(obs["hunters"]) == 3


if __name__ == "__main__":
    test_portrait_stats_trouve_la_carte_2()
    test_choisir_refuse_les_cas_ambigus()
    test_integrer_place_le_chasseur_a_sa_position()
    print("ok")
