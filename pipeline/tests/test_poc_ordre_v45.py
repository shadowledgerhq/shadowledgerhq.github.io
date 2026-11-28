"""SPEC_ETAPE1 v45 : ordre POC = palier, Goal Progress, Rank Score ; ex aequo sinon."""
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import classement as C


def lg(cid, total, tier, goal, conf="sur"):
    return {"channel_id": cid, "confidence": conf, "score": {"total": total}, "_fin": datetime(2026, 11, 27),
            "runs_detail": [{"tier": tier, "goal_progress": goal}], "rank": None}


def test_palier_puis_but_puis_rank_score():
    # Rank Score incohérent avec la formule : le palier prime quand même
    a, b, c, d = lg("a", 5_000_000, 6, 10.0), lg("b", 9_000_000, 5, 99.0), lg("c", 5_100_000, 6, 10.0), lg("d", 5_100_000, 6, 10.0)
    r = C._ordonner_poc_refonte([a, b, c, d])
    assert [x["channel_id"] for x in r] == ["c", "d", "a", "b"]
    assert [x["rank"] for x in r] == [1, 1, 3, 4]


def test_texte_sans_pourcentage_et_clear():
    t = lg("t", 3_000_000, 4, None, "a_verifier")        # titre « Tier 4 » : 3 M → 0 %
    k = lg("k", 4_000_000, 4, None, "a_verifier")        # « Tier 4 clear » : 100 %
    assert C.cle_poc_v45(t)[:2] == (4, 0.0) and C.cle_poc_v45(k)[:2] == (4, 100.0)
    assert [x["channel_id"] for x in C._ordonner_poc_refonte([t, k])] == ["k", "t"]


def test_sur_devant_a_verifier():
    r = C._ordonner_poc_refonte([lg("x", 9_000_000, 10, 1.0, "a_verifier"), lg("y", 1_000_000, 2, 1.0)])
    assert r[0]["channel_id"] == "y"


if __name__ == "__main__":
    test_palier_puis_but_puis_rank_score(); test_texte_sans_pourcentage_et_clear(); test_sur_devant_a_verifier(); print("OK")
