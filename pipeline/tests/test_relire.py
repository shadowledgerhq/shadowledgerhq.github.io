import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from donnees import Donnees, charger_config
from etape1 import a_relire, relire

W = "2026-11-12"


def lec(vid, mode, score, source, notes=()):
    return {"video_id": vid, "channel_id": "UC" + vid, "channel_title": vid, "published_at": "2026-11-13T10:00:00Z", "lang": "en",
            "mode": mode, "gate": None, "hunter_mode": None, "t": None, "stage": None, "team": None,
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
    assert r["descriptions_non_relues"] == 1 and all("regles" not in p for p in d.processed().values())   # pas marquées : à refaire avec la clé
    assert set(a_relire(d, config, W)) == {"a", "b", "c"}
    assert all("regles" in l for l in d.lectures(W)) and [l["regles"] for l in d.lectures(W) if l["video_id"] == "b"] == [None]   # lecture de description gardée


def test_relire_avec_api():
    d, config = monde(), charger_config()
    r = relire(d, config, W, FauxApi())
    l = {x["video_id"]: x for x in d.lectures(W)}
    assert "b" not in l                                   # chapitres : plus aucun score
    assert d.processed()["b"]["regles"] == config["tri1_version"] and r["descriptions_relues"] == 1
    assert d.videos(W)["b"]["title"] == "BOT clear" and a_relire(d, config, W) == ["a", "c"]   # b est à jour ; a et c : pas relues via l'API
    relire(d, config, W, FauxApi())                       # idempotent
    assert len(d.lectures(W)) == 1


# --- v8 -----------------------------------------------------------------------------------------

E4L = {"title": "BARUKA S20 BOT GUIDE WITHOUT S RANK FIGURES | BATTLEFIELD OF TIME SEASON 20 [SOLO LEVELING: ARISE]",
       "description": "Clear time 19.754s\n00:00 Intro\n00:32 Boss\n01:01 Phase 2\n01:45 Fin\n03:49 Merci"}


class ApiE4L:
    def appel(self, ressource, **p):
        return {"items": [{"id": "E4lHBPoZeKs", "snippet": E4L}]}


def test_v8_relecture_regles_et_cas_e4l():
    d, config = Donnees(tempfile.mkdtemp()), charger_config()
    m = {"video_id": "E4lHBPoZeKs", "channel_id": "UCe", "channel_title": "Black Thunder X", "title": "ancien titre", "published_at": "2026-11-12T07:58:32Z",
         "lang": "en", "mode_guess": ["bot"]}
    d.ecrire(f"runs/{W}/_videos.json", {"E4lHBPoZeKs": m})
    d.ecrire("processed.json", {"E4lHBPoZeKs": {"week": W, "status": "en_cours", "regles": 3}})    # lue avec les règles v3
    d.ecrire(f"runs/{W}/_lectures.json", [{**lec("E4lHBPoZeKs", "bot", 32.0, "description"), "regles": 3}])
    assert a_relire(d, config, W) == ["E4lHBPoZeKs"]
    r = relire(d, config, W, ApiE4L())
    (l,) = d.lectures(W)
    assert l["score"] == 19.754 and l["regles"] == config["tri1_version"]    # plus de 00:32 (chapitre)
    assert d.videos(W)["E4lHBPoZeKs"]["title"].startswith("BARUKA S20") and d.processed()["E4lHBPoZeKs"]["regles"] == config["tri1_version"]
    assert a_relire(d, config, W) == [] and r["changees"] == 1
    # une vidéo `termine` ou `rejete` n'est jamais relue
    d.ecrire("processed.json", {"E4lHBPoZeKs": {"week": W, "status": "termine", "regles": 1}})
    assert a_relire(d, config, W) == []


def test_v9_chapitres_dans_les_notes_sans_cle():
    d, config = monde(), charger_config()
    ls = d.lectures(W)
    for x in ls:
        if x["video_id"] == "b":
            x["notes"] = ["score provisoire (description) : 00:32", "autres candidats : 01:01, 01:45, 03:49"]
    d.ecrire(f"runs/{W}/_lectures.json", ls)
    r = relire(d, config, W)
    assert "b" not in {x["video_id"] for x in d.lectures(W)} and r["chapitres_retires"] == 1
    assert a_relire(d, config, W) == ["a", "b", "c"] or "b" in a_relire(d, config, W)  # reste à relire avec la clé


def test_v10_titre_rejoue_sans_cle():
    """Sans clé : la description n'est pas relue, mais la semaine BOT (titre) est rejouée sur la lecture gardée."""
    d, config = Donnees(tempfile.mkdtemp()), charger_config()
    m = {"video_id": "E4lHBPoZeKs", "channel_id": "UCe", "channel_title": "Black Thunder X", "title": E4L["title"], "published_at": "2026-11-12T07:58:32Z",
         "lang": "en", "mode_guess": ["bot"]}
    d.ecrire(f"runs/{W}/_videos.json", {"E4lHBPoZeKs": m})
    d.ecrire("processed.json", {"E4lHBPoZeKs": {"week": W, "status": "en_cours"}})
    d.ecrire(f"runs/{W}/_lectures.json", [lec("E4lHBPoZeKs", "bot", 32.0, "description")])
    relire(d, config, W)
    (l,) = d.lectures(W)
    assert "bot_variant" not in l and l["bot_season_week"] is None and "description non relue (règles v3)" in l["notes"] and a_relire(d, config, W) == ["E4lHBPoZeKs"]


if __name__ == "__main__":
    test_v10_titre_rejoue_sans_cle(); test_v9_chapitres_dans_les_notes_sans_cle(); test_relire_hors_ligne(); test_relire_avec_api(); test_v8_relecture_regles_et_cas_e4l(); print("OK")
