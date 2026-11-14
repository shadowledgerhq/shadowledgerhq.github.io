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


def config_sans_images():
    config = charger_config()
    config["pc"]["images"]["actif"] = False   # tris 3-4 testés dans test_images
    return config


class FauxOutils:
    def __init__(self, textes, erreurs=(), erreurs_msg=None):
        self.textes, self.erreurs, self.appels, self.erreurs_msg = textes, set(erreurs), [], erreurs_msg or {}

    def sous_titres(self, vid, dossier):
        self.appels.append(vid)
        if vid in self.erreurs:
            raise RuntimeError(self.erreurs_msg.get(vid, "boom"))
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
           "gate": None, "hunter_mode": None, "t": None, "stage": None, "team": None, "score": 130 * 10**12,
           "score_source": "titre", "exact": False, "confidence": "a_verifier", "detail": {}, "notes": ["score provisoire (titre) : 130T"]}
    d.ecrire(f"runs/{SEM}/_lectures.json", [lec])
    return d


def test_vtt():
    assert pc.vtt_vers_texte(VTT) == "이번 기록 131조 4497억"
    assert pc.duree_minutes("PT1H2M30S") == 62.5 and pc.duree_minutes("x") is None


def test_passage_daily_idempotent():
    config = config_sans_images()
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
        assert any("boom" in a for a in r["alertes"]) and any("[EN ATTENTE]" in a for a in r["alertes"])
        assert "pc-daily" in (Path(tmp) / f"data/runs/{SEM}/_rapport.md").read_text(encoding="utf-8")
        # 2e passage : seule la vidéo en erreur est retentée, rien n'est doublé
        avant = json.dumps(d.lectures(SEM))
        o2 = FauxOutils({"b": "98T"})
        pc.lancer("daily", INSTANT, d, config, o2)
        assert o2.appels == ["b"] and len(d.lectures(SEM)) == len(json.loads(avant)) + 1


def test_anti_bot_youtube_arrete_le_lot():
    """Blocage anti-bot de yt-dlp (« -do-i-pass-cookies-to-yt-dlp ») traité comme un 429 : le lot s'arrête."""
    assert pc.est_429(Exception("yt-dlp code 1 : -do-i-pass-cookies-to-yt-dlp for how to manually pass cookies"))
    assert pc.est_429(Exception("Sign in to confirm you're not a bot")) and not pc.est_429(Exception("Video unavailable"))
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        o = FauxOutils({"a": VTT, "c": "x"}, erreurs=["b"], erreurs_msg={"b": "yt-dlp code 1 : -do-i-pass-cookies-to-yt-dlp"})
        r = pc.lancer("daily", INSTANT, d, config, o, journal=lambda x: None, dormir=lambda x: None)
        assert o.appels == ["a", "b"] and "pc" not in d.processed()["b"]
        assert any("anti-bot" in a for a in r["alertes"])


def test_429_reporte_et_arrete_les_sous_titres():
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        o = FauxOutils({"a": VTT, "c": "x"}, erreurs=["b"], erreurs_msg={"b": "HTTP Error 429: Too Many Requests"})
        lignes, pauses = [], []
        r = pc.lancer("daily", INSTANT, d, config, o, journal=lignes.append, dormir=pauses.append)
        assert o.appels == ["a", "b"]                                   # arrêt au 429 : c et d ne sont pas tentées
        p = d.processed()
        assert p["a"]["pc"]["sous_titres"] == "fait" and "pc" not in p["b"] and "pc" not in p["c"]   # b reportée, rien de marqué
        assert any("429" in a for a in r["alertes"]) and pauses == [config["pc"]["pause_s"]]          # pause entre a et b
        assert any(l.startswith("[1/4] a") for l in lignes) and any(l.startswith("[2/4] b") for l in lignes)
        # le passage suivant reprend à b
        o2 = FauxOutils({"b": "98T", "c": "", "d": ""})
        pc.lancer("daily", INSTANT, d, config, o2)
        assert o2.appels == ["b", "c", "d"]


def test_enregistrement_apres_chaque_video():
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)

        class Coupe(FauxOutils):
            def sous_titres(self, vid, dossier):
                if vid == "c":
                    # a et b sont déjà sur disque quand c démarre
                    assert [d.processed()[v].get("pc", {}).get("sous_titres") for v in "ab"] == ["fait", "fait"]
                    raise KeyboardInterrupt
                return super().sous_titres(vid, dossier)
        try:
            pc.lancer("daily", INSTANT, d, config, Coupe({"a": VTT, "b": VTT}))
        except KeyboardInterrupt:
            pass
        assert d.processed()["a"]["pc"]["sous_titres"] == "fait" and "pc" not in d.processed()["c"]
        assert any(l["video_id"] == "a" and l["score_source"] == "sous-titres" for l in d.lectures(SEM))


def test_budget_de_temps_du_passage():
    config = config_sans_images()
    config["pc"]["budget_minutes"] = 1
    horloge_t = iter(range(0, 10_000, 40))                              # +40 s à chaque lecture de l'horloge
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        o = FauxOutils({})
        r = pc.lancer("daily", INSTANT, d, config, o, horloge=lambda: next(horloge_t))
        assert 0 < len(o.appels) < 4 and any("budget de temps" in a for a in r["alertes"])


def test_weekly_gel_et_ouverture():
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        r = pc.lancer("weekly", JEUDI, d, config, FauxOutils({}))
        assert r["week"] == SEM and d.meta(SEM)["frozen"] is False and d.meta("2026-11-19") is not None
        assert any("NON gelée" in a for a in r["alertes"])
        config["pc"]["geler"] = True
        r = pc.lancer("weekly", JEUDI, d, config, FauxOutils({}))
        assert d.meta(SEM)["frozen"] is False and any("toutes les lignes sont provisoires" in a for a in r["alertes"])   # SPEC §6
        # une ligne « sûre » (écran RESULT lu) : le gel est permis
        lectures = d.lectures(SEM)
        lectures.append({**lectures[0], "video_id": "z", "channel_id": "UCz", "score": 90 * 10**12, "exact": True, "confidence": "sur",
                         "team": 1, "score_source": "video-complete"})
        lectures.append({**lectures[-1], "team": 2, "score": 80 * 10**12, "t": 9})
        d.ecrire(f"runs/{SEM}/_lectures.json", lectures)
        r = pc.lancer("weekly", JEUDI, d, config, FauxOutils({}))
        assert d.meta(SEM)["frozen"] is True and d.meta(SEM)["frozen_at"] is not None
        o = FauxOutils({})
        r = pc.lancer("weekly", JEUDI, d, config, o)           # semaine gelée : rien n'est retraité
        assert o.appels == [] and any("déjà gelée" in a for a in r["alertes"])


def test_outil_absent():
    config = config_sans_images()
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
