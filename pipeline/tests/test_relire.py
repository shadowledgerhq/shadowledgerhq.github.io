import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from donnees import Donnees, charger_config
from etape1 import relire

W = "2026-11-12"


def lec(vid, mode, score, source, notes=()):
    return {"video_id": vid, "channel_id": "UC" + vid, "channel_title": vid, "published_at": "2026-11-13T10:00:00Z", "lang": "en",
            "mode": mode, "bot_variant": None, "gate": None, "hunter_mode": None, "t": None, "stage": None, "team": None,
            "score": score, "score_source": source, "exact": False, "confidence": "a_verifier", "detail": {}, "notes": list(notes)}


def monde():
    d = Donnees(tempfile.mkdtemp())
    meta = lambda v, titre, mode: {"video_id": v, "channel_id": "UC" + v, "channel_title": v, "title": titre, "published_at": "2026-11-13T10:00:00Z",
                                    "lang": "en", "mode_guess": [mode]}
    d.ecrire(f"runs/{W}/_videos.json", {"a": meta("a", "BOT challenge 223s", "bot"), "b": meta("b", "BOT clear", "bot"),
                                        "c": meta("c", "POC 133T (Can 150T)", "poc")})
    d.ecrire("processed.json", {v: {"week": W, "status": "en_cours"} for v in "abc"})
    d.ecrire(f"runs/{W}/_meta.json", {"week": W})
    d.ecrire(f"runs/{W}/_lectures.json", [lec("a", "bot", 223.0, "titre"), lec("b", "bot", 32.0, "description"),
                                          lec("c", "poc", 150 * 10**12, "titre")])
    return d


class FauxApi:
    def appel(self, ressource, **p):
        return {"items": [{"id": "b", "snippet": {"description": "BOT\n00:00 Intro\n00:32 Boss\n01:01 Fin"}}]}


def test_relire_hors_ligne():
    d, config = monde(), charger_config()
    r = relire(d, config, W)
    l = {x["video_id"]: x for x in d.lectures(W)}
    assert "a" not in l                                   # 223 s : hors plage BOT (5-180)
    assert l["c"]["score"] == 133 * 10**12                # « Can 150T » exclu
    assert l["b"]["score"] == 32.0 and "description non relue (règles v3)" in l["b"]["notes"]
    assert r["descriptions_non_relues"] == 1 and "tri1_version" not in d.meta(W)   # pas marquée : à refaire avec la clé


def test_relire_avec_api():
    d, config = monde(), charger_config()
    r = relire(d, config, W, FauxApi())
    l = {x["video_id"]: x for x in d.lectures(W)}
    assert "b" not in l                                   # chapitres : plus aucun score
    assert d.meta(W)["tri1_version"] == config["tri1_version"] and r["descriptions_relues"] == 1
    relire(d, config, W, FauxApi())                       # idempotent
    assert len(d.lectures(W)) == 1


if __name__ == "__main__":
    test_relire_hors_ligne(); test_relire_avec_api(); print("OK")
