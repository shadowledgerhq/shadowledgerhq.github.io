import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pc
from donnees import Donnees, charger_config

VTT = """WEBVTT
Kind: captions
Language: ko

00:00:01.000 --> 00:00:03.000
<c>이번 기록 131조 4497억</c>

00:00:03.000 --> 00:00:05.000
이번 기록 131조 4497억
"""
SEM = "2026-11-12"
INSTANT = datetime(2026, 11, 13, 19, 30, tzinfo=timezone.utc)   # vendredi 20:30 Paris
JEUDI = datetime(2026, 11, 19, 0, 15, tzinfo=timezone.utc)      # jeudi 01:15 Paris : semaine du 12/11 écoulée


class FauxOutils:
    def __init__(self, textes, erreurs=()):
        self.textes, self.erreurs, self.appels = textes, set(erreurs), []

    def sous_titres(self, vid, dossier):
        self.appels.append(vid)
        if vid in self.erreurs:
            raise RuntimeError("HTTP 429")
        return self.textes.get(vid, "")

    def whisper(self, vid, dossier):
        return None


def monde(tmp):
    d = Donnees(tmp)
    meta = lambda v, modes: {"video_id": v, "channel_id": "UC" + v, "channel_title": "Ch " + v, "title": "t", "published_at": "2026-11-13T10:00:00Z",
                              "lang": "ko", "duration": "PT5M", "mode_guess": modes}
    d.ecrire(f"runs/{SEM}/_videos.json", {v: meta(v, ["poc"]) for v in ("a", "b", "c", "d")})
    d.ecrire("processed.json", {v: {"week": SEM, "channel_id": "UC" + v, "published_at": "2026-11-13T10:00:00Z", "first_seen": "2026-11-13",
                                    "updated_at": "2026-11-13", "last_tri": 1, "status": "en_cours", "modes": ["poc"], "pc_needed": True} for v in "abcd"})
    # `d` a déjà un score de titre (130T) : les sous-titres ne doivent pas doubler la lecture
    lec = {"video_id": "d", "channel_id": "UCd", "channel_title": "Ch d", "published_at": "2026-11-13T10:00:00Z", "lang": "ko", "mode": "poc",
           "bot_variant": None, "gate": None, "hunter_mode": None, "t": None, "stage": None, "team": None, "score": 130 * 10**12,
           "score_source": "titre", "exact": False, "confidence": "a_verifier", "detail": {}, "notes": ["score provisoire (titre) : 130T"]}
    d.ecrire(f"runs/{SEM}/_lectures.json", [lec])
    return d


def test_vtt():
    assert pc.vtt_vers_texte(VTT) == "이번 기록 131조 4497억"
    assert pc.duree_minutes("PT1H2M30S") == 62.5 and pc.duree_minutes("x") is None


def test_passage_daily_idempotent():
    config = charger_config()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        o = FauxOutils({"a": VTT, "d": "même run 150T", "c": ""}, erreurs=["b"])
        r = pc.lancer("daily", INSTANT, d, config, o)
        assert o.appels == ["a", "b", "c", "d"] and r["traitees"] == 4
        lec = {l["video_id"]: l for l in d.lectures(SEM)}
        assert lec["a"]["score"] == 131_449_700_000_000 and lec["a"]["score_source"] == "sous-titres"
        assert len([l for l in d.lectures(SEM) if l["video_id"] == "d"]) == 1          # pas de doublon
        assert "sous-titres : 150T" in lec["d"]["notes"]
        p = d.processed()
        assert [p[v]["pc"]["sous_titres"] for v in "abcd"] == ["fait", "erreur", "absent", "fait"]
        assert any("HTTP 429" in a for a in r["alertes"]) and any("non gérés [EN ATTENTE]" in a for a in r["alertes"])
        assert "pc-daily" in (Path(tmp) / f"data/runs/{SEM}/_rapport.md").read_text(encoding="utf-8")
        # 2e passage : seule la vidéo en erreur est retentée, rien n'est doublé
        avant = json.dumps(d.lectures(SEM))
        o2 = FauxOutils({"b": "98T"})
        pc.lancer("daily", INSTANT, d, config, o2)
        assert o2.appels == ["b"] and len(d.lectures(SEM)) == len(json.loads(avant)) + 1


def test_weekly_gel_et_ouverture():
    config = charger_config()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        r = pc.lancer("weekly", JEUDI, d, config, FauxOutils({}))
        assert r["week"] == SEM and d.meta(SEM)["frozen"] is False and d.meta("2026-11-19") is not None
        assert any("NON gelée" in a for a in r["alertes"])
        config["pc"]["geler"] = True
        r = pc.lancer("weekly", JEUDI, d, config, FauxOutils({}))
        assert d.meta(SEM)["frozen"] is True and d.meta(SEM)["frozen_at"] is not None
        o = FauxOutils({})
        r = pc.lancer("weekly", JEUDI, d, config, o)           # semaine gelée : rien n'est retraité
        assert o.appels == [] and any("déjà gelée" in a for a in r["alertes"])


def test_outil_absent():
    config = charger_config()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        class Absent(FauxOutils):
            def sous_titres(self, vid, dossier):
                raise pc.OutilAbsent("yt-dlp introuvable")
        r = pc.lancer("daily", INSTANT, d, config, Absent({}))
        assert r["traitees"] == 0 and any("yt-dlp introuvable" in a for a in r["alertes"])
        assert all("pc" not in p for p in d.processed().values())     # rien de marqué : retenté plus tard


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn(); print("ok", nom)
