"""SPEC_ETAPE1 v43 §9 point 4 : lecture du palier dans le texte POC (marque de mode, intervalle, palier + %, borne nulle)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import classement as C
import poc_palier as P

CONFIG = json.loads((Path(__file__).resolve().parents[2] / "pipeline/config/etape1.json").read_text(encoding="utf-8"))
META = {"video_id": "v1", "channel_id": "c1", "channel_title": "J", "published_at": "2026-11-21T10:00:00Z", "mode_guess": ["poc"]}


def vide(meta, mode):
    return {"video_id": meta["video_id"], "mode": mode, "notes": [], "detail": {}}


def lire(*textes):
    return P.lecture_texte(META, [("titre", t) for t in textes], CONFIG, vide)


def test_autre_mode_pas_de_lecture_poc():                        # 1CvG1JEPGwo
    assert lire("Solo Leveling Arise - Unstable Dungeon - Giant Arachnid - Tier 25") is None
    assert lire("Tier 25 sans aucun mode") is None                 # pas de marque POC
    assert lire("Power of Calamity Tier 25 pendant Hall of the Monarchs") is None


def test_intervalle():                                           # 3y8yRhcSq4Y
    assert lire("POWER OF CALAMITY TIER 1–5! BEST BUILD")["score"] == 4_000_000
    assert lire("POC T1-T5 guide")["score"] == 4_000_000
    assert lire("poc tier 1 to 5")["score"] == 4_000_000


def test_palier_et_pourcentage():                                # 9BrduWR4aSY, cNIuOYknYg8
    for t in ("ROUND 17 (100%) FIRE + WATER BUILD POC", "TIER 17 POC 100% WITH WATER TEAM RUN"):
        lec = lire(t)
        assert lec["score"] == 17_000_000 and "palier et % du titre" in lec["notes"] and lec["confidence"] == "a_verifier"
    assert lire("POC T16 96.2%")["score"] == 15_962_000


def test_palier_seul_inchange_et_clear():
    assert lire("POC Tier 17 run")["score"] == 16_000_000
    assert lire("Power of Calamity Tier 17 clear")["score"] == 17_000_000


def test_borne_nulle_jamais_une_ligne():
    lec = lire("POC Tier 1 tips")
    assert lec["score"] == 0                                       # gardée dans _lectures.json
    assert lire("POC Tier 1 tips", "POC Tier 9 100%")["score"] == 9_000_000     # une autre source mieux dite l'emporte


def test_correction_semaine_gelee_ne_touche_que_les_lignes_non_classees(tmp_path):
    import corriger_poc_v43 as K
    from donnees import Donnees
    d = Donnees(tmp_path)
    w = "2026-11-19"
    d.ecrire(f"runs/{w}/_meta.json", {"week": w, "frozen": True, "frozen_at": "2026-11-26T21:00:00Z"})
    d.ecrire(f"runs/{w}/_videos.json", {"a": {"video_id": "a", "title": "Unstable Dungeon Tier 25", "mode_guess": ["poc"], "channel_id": "c", "channel_title": "J", "published_at": "2026-11-21T10:00:00Z"},
                                          "b": {"video_id": "b", "title": "POC TIER 17 100% run", "mode_guess": ["poc"], "channel_id": "c", "channel_title": "J", "published_at": "2026-11-21T10:00:00Z"}})
    base = {"channel_id": "c", "channel_title": "J", "published_at": "2026-11-21T10:00:00Z", "lang": "en", "mode": "poc", "regles": 19,
            "score_source": "titre", "exact": False, "confidence": "a_verifier", "notes": ["palier du titre : rang prudent"]}
    d.ecrire(f"runs/{w}/_lectures.json", [{**base, "video_id": "a", "score": 24_000_000, "detail": {"poc_texte": "palier", "palier": 25}}])
    d.ecrire("processed.json", {"a": {"status": "en_cours", "week": w, "channel_id": "c", "published_at": "x"}})
    msg = K.corriger(w, d, CONFIG)
    assert "1 ajoutée(s) (b)" in msg and "1 vidéo(s) rejetée(s) hors_sujet (a)" in msg
    assert [r["reason"] for r in d.rejected(w)] == ["hors_sujet"] and d.processed()["a"]["status"] == "rejete"
    assert [l["video_id"] for l in d.lectures(w)] == ["b"] and d.lectures(w)[0]["score"] == 17_000_000
    assert d.meta(w)["frozen"] is True                                  # semaine toujours gelée
    assert "Correction POC v43 après gel" in (tmp_path / "data" / "runs" / w / "_rapport.md").read_text(encoding="utf-8")
