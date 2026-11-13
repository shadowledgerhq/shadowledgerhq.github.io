import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sjw import SKILL_SLOTS, sjw_complet, verifier_sjw


def _sjw():
    return {"skills": [{"slot": s, "id": "x", "level": None if s == "qte_1" else 5}
                       for s in SKILL_SLOTS], "blessings": list(range(8))}


def test_complet():
    assert sjw_complet(_sjw())  # QTE 01 sans niveau reste complet


def test_incomplet():
    s = _sjw(); s["skills"].pop(); s["blessings"].pop()
    assert verifier_sjw(s) == ["emplacement manquant : qte_3", "bénédictions : 7/8"]


if __name__ == "__main__":
    test_complet(); test_incomplet(); print("ok")
