import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classement import calculer
from donnees import Donnees, charger_config

W = "2026-11-12"
T = 10**12
CONFIG = charger_config()
HORLOGE = datetime(2026, 11, 14, 19, 0, tzinfo=timezone.utc)


def lec(vid, ch, mode, score, jour=13, **kw):
    base = {"video_id": vid, "channel_id": ch, "channel_title": ch.lower(),
            "published_at": f"2026-11-{jour:02d}T12:00:00Z", "lang": "ko", "mode": mode,
            "gate": None, "hunter_mode": None, "t": 10, "stage": None,
            "team": None, "score": score, "score_source": "video-complete", "exact": True,
            "confidence": "sur", "detail": {}, "notes": []}
    base.update(kw)
    return base


def preparer(lectures, boss_prec=None, meta=None):
    tmp = Path(tempfile.mkdtemp())
    d = Donnees(tmp)
    d.ecrire(f"runs/{W}/_lectures.json", lectures)
    if boss_prec:
        d.ecrire("runs/2026-11-05/_boss.json", boss_prec)
    if meta:
        d.ecrire(f"runs/{W}/_meta.json", meta)
    return d


def lire(d, nom):
    return json.loads((d.data / "runs" / W / f"{nom}.json").read_text(encoding="utf-8"))


def test_poc_equipes_egalite_doublon_provisoire():
    d = preparer([
        lec("a1", "UCA", "poc", 100 * T, team=1, jour=13),
        lec("a2", "UCA", "poc", 50 * T, team=2, jour=13),
        lec("a3", "UCA", "poc", 90 * T, team=1, jour=13),       # même équipe : jamais additionnée
        lec("b1", "UCB", "poc", 120 * T, team=1),
        lec("b2", "UCB", "poc", 110 * T, team=1),               # seulement l'équipe 1
        lec("c0", "UCC", "poc", 200 * T, exact=False, confidence="a_verifier", score_source="titre"),
        lec("c1", "UCC", "poc", 80 * T, team=1, jour=14),
        lec("c2", "UCC", "poc", 70 * T, team=2, jour=14),
        lec("d1", "UCD", "poc", 100 * T, team=1, jour=15),      # ré-upload de a1
    ])
    res = calculer(W, d, CONFIG, HORLOGE)
    poc = lire(d, "poc")
    assert [(l["channel_id"], l["rank"], l["score"]["total"]) for l in poc] == [
        ("UCA", 1, 150 * T), ("UCC", 2, 150 * T), ("UCB", 3, 120 * T)]            # v16 : une seule run sûre = classée
    assert poc[0]["video_ids"] == ["a1", "a2"] and poc[0]["score"]["runs"] == [100 * T, 50 * T]
    assert poc[1]["exact"] is True and "c0" not in poc[1]["video_ids"]
    assert "une seule run" in poc[2]["notes"] and "trouvée" not in poc[2]["notes"] and poc[2]["confidence"] == "sur"
    rej = d.rejected(W)
    assert [(r["video_id"], r["reason"], r["detail"]) for r in rej] == [("d1", "doublon", "a1")]
    assert res["rejets"] and json.loads((d.data / "channels.json").read_text())[0]["source"] == "auto"
    # Idempotent : deuxième passage sans changement.
    avant = (d.data / "runs" / W / "poc.json").read_text()
    calculer(W, d, CONFIG, HORLOGE)
    assert (d.data / "runs" / W / "poc.json").read_text() == avant
    assert len(d.rejected(W)) == 1


def test_poc_equipe_illisible():
    d = preparer([lec("e1", "UCE", "poc", 10 * T), lec("e2", "UCE", "poc", 9 * T)])
    calculer(W, d, CONFIG, HORLOGE)
    l = lire(d, "poc")[0]
    assert l["rank"] is None and l["score"]["total"] == 19 * T and "équipe illisible" in l["notes"]


def test_bot_unique_et_hotm_portes():
    d = preparer([
        lec("s1", "UC1", "bot", 19.558),
        lec("s2", "UC2", "bot", 18.0),
        lec("s3", "UC2", "bot", 25.0),
        lec("h1", "UC1", "hotm", 94600, gate=3, hunter_mode=False,
            detail={"clear": 90000, "proof_bonus": 4600, "proof_level": 46}),
        lec("h2", "UC2", "hotm", 95000, gate=None),
    ])
    calculer(W, d, CONFIG, HORLOGE)
    season = lire(d, "bot")
    assert [(l["channel_id"], l["rank"], l["score"]["total"]) for l in season] == [
        ("UC2", 1, 18.0), ("UC1", 2, 19.558)]
    assert season[0]["score"]["unit"] == "seconds" and "bot_variant" not in season[0]
    h = lire(d, "hotm-gate-3")[0]
    assert h["gate"] == 3 and h["hunter_mode"] is False and h["runs_detail"][0]["proof_bonus"] == 4600
    assert "submode" not in h["runs_detail"][0]
    assert lire(d, "hotm-gate-inconnue")[0]["rank"] is None


def test_boss():
    lectures = [lec(f"v{i}", f"UC{i}", "hotm", 90000 + i, gate=1, stage="기만자의 무대") for i in range(3)]
    lectures.append(lec("x", "UCX", "hotm", 99000, gate=1, stage="autre stage"))
    lectures.append(lec("y", "UCY", "hotm", 98000, gate=1, stage="ancien stage"))
    d = preparer(lectures, boss_prec=[{"classement": "hotm-gate-1", "stage": "ancien stage"}])
    res = calculer(W, d, CONFIG, HORLOGE)
    assert d.boss(W)[0]["stage"] == "기만자의 무대" and d.boss(W)[0]["videos"] == 3
    gate1 = lire(d, "hotm-gate-1")
    x = next(l for l in gate1 if l["channel_id"] == "UCX")
    assert x["rank"] is None and "boss différent : autre stage" in x["notes"]
    assert all(l["channel_id"] != "UCY" for l in gate1)
    assert d.rejected(W)[0]["reason"] == "semaine_precedente"
    assert res["alertes_boss"]


def test_boss_non_controle_et_gel():
    d = preparer([lec("v", "UCV", "hotm", 90000, gate=1, stage="s")])
    calculer(W, d, CONFIG, HORLOGE)
    assert "boss non contrôlé" in lire(d, "hotm-gate-1")[0]["notes"]
    d2 = preparer([lec("v", "UCV", "hotm", 90000, gate=1)], meta={"week": W, "frozen": True})
    assert calculer(W, d2, CONFIG, HORLOGE)["gelee"] is True
    assert not (d2.data / "runs" / W / "hotm-gate-1.json").exists()


def test_v5_gb_classe_au_rage_count():
    # GB (v5) : groupe 1 + groupe 2 ; deux runs d'un même groupe ne s'additionnent jamais
    d = preparer([lec("g1", "UCG", "gb", 167, team=1, damage=17 * T), lec("g2", "UCG", "gb", 165, team=2, damage=15 * T),
                  lec("g3", "UCG", "gb", 166, team=1, damage=16 * T), lec("p1", "UCP", "poc", 100 * T, team=1)])
    res = calculer(W, d, CONFIG, HORLOGE)
    l = lire(d, "gb")[0]
    assert "gb" in res["fichiers"] and l["score"] == {"total": 332, "runs": [167, 165], "unit": "rage_count"}
    assert l["rank"] == 1 and l["runs_detail"][0]["damage"] == 17 * T and [x["team"] for x in l["runs_detail"]] == [1, 2]


def test_v3_doublon_bot_hotm_note_sans_retrait():
    assert CONFIG["doublon_modes"] == ["poc"]
    lectures = [lec("h1", "UC1", "hotm", 94600, gate=1, jour=13), lec("h2", "UC2", "hotm", 94600, gate=1, jour=14),
                lec("b1", "UC1", "bot", 19.558), lec("b2", "UC2", "bot", 19.558, jour=14)]
    d = preparer(lectures)
    res = calculer(W, d, CONFIG, HORLOGE)
    h = lire(d, "hotm-gate-1")
    assert len(h) == 2 and sorted(l["notes"].split("doublon possible : ")[1][:2] for l in h) == ["h1", "h2"]  # note avec le video_id de l'autre
    assert len(lire(d, "bot")) == 2 and d.rejected(W) == []
    # POC : la run en trop est retirée ; la vidéo n'est rejetée que si elle n'a plus aucune run
    d = preparer([lec("a1", "UCA", "poc", 100 * T, team=1), lec("a2", "UCA", "poc", 50 * T, team=2),
                  lec("d1", "UCD", "poc", 100 * T, team=1, jour=14), lec("d1", "UCD", "poc", 40 * T, team=2, jour=14, t=60)])
    calculer(W, d, CONFIG, HORLOGE)
    assert d.rejected(W) == [] and lire(d, "poc")[1]["score"]["runs"] == [40 * T]  # run en trop retirée, vidéo gardée (il lui reste une run)
    d = preparer([lec("a1", "UCA", "poc", 100 * T, team=1), lec("d1", "UCD", "poc", 100 * T, team=1, jour=14)])
    calculer(W, d, CONFIG, HORLOGE)
    assert [(r["video_id"], r["reason"]) for r in d.rejected(W)] == [("d1", "doublon")]  # plus aucune run : rejetée


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
    print("OK")
