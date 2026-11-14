"""Tris 3-4 : OCR d'écrans (textes SYNTHÉTIQUES tirés de la spec, pas de vraies captures) et passage PC."""
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_ecrans
import pc
from donnees import Donnees, charger_config
from test_pc import INSTANT, JEUDI, SEM, monde

CONFIG = charger_config()
T = 10**12

BOT = """Results
Baruka
Phase 1   00:09.281
Phase 2   00:14.986
Phase 3   00:19.926
Play Time 00:19
ThenaX    00:19.926"""
GB_RESULTS = """Results
Giant Statue
Player's Score 3,763,121,797,048
Hunter Rank 1 2,000,000,000,000
Hunter Rank 2 2,000,000,000,000
Hunter Rank 3 2,000,000,000,000
Hunter Rank 4 2,000,000,000,000
Hunter Rank 5 2,000,000,000,000
Hunter Rank 6 2,000,000,000,000
Final Score 15,763,121,797,048
Rage Count 165
Play Time 03:00
New Record Achieved!"""
GB_RECORD = """Guild Boss
Personal Record
Total Score 32,842,054,460,310
Challenge Count 12
Total Rage Count 332
Group 1   167   17.28T
Group 2   165   15.55T
Time Left in Season 6d 9h"""
HOTM = """RESULT — 기만자의 무대
전투 결과
클리어 1,500
증명 보너스 93,100
합산 결과 94,600
기존 기록 94,000
이번 기록 94,600"""
POC = """RESULT 재앙의 권좌
플레이어 스코어 4,000,000,000,000
계승자 스코어 2,000,000,000,000
이번 기록 131,449,789,393,717"""


def meta(vid="a", modes=("bot",), titre="t"):
    return {"video_id": vid, "channel_id": "UC" + vid, "channel_title": "Ch " + vid, "title": titre, "published_at": "2026-11-14T10:00:00Z",
            "lang": "en", "duration": "PT5M", "mode_guess": list(modes)}


def lire(texte, modes, titre="t"):
    return ocr_ecrans.lectures_depuis_texte(texte, meta("a", modes, titre), CONFIG, "debut-fin", 3)


def test_detection():
    assert [ocr_ecrans.detecter(t) for t in (BOT, GB_RESULTS, GB_RECORD, HOTM, POC, "bruit")] == ["bot", "gb_results", "gb_record", "hotm", "poc", None]


def test_bot():
    (l,) = lire(BOT, ["bot"])
    assert l["score"] == 19.926 and l["confidence"] == "sur" and l["exact"] and l["stage"] == "Baruka"
    assert l["detail"]["phases"] == [9.281, 14.986, 19.926] and l["detail"]["play_time"] == 19 and l["t"] == 3
    (l,) = lire(BOT.replace("Play Time 00:19", "Play Time 00:21"), ["bot"])
    assert l["confidence"] == "a_verifier"                          # Play Time ≠ chrono tronqué
    (l,) = lire(BOT.replace("ThenaX    00:19.926", ""), ["bot"])
    assert l["confidence"] == "a_verifier" and l["score"] == 19.926  # bandeau non lu : jamais « sûr »


def test_gb_results_et_record():
    (l,) = lire(GB_RESULTS, ["gb"])
    assert (l["score"], l["damage"], l["confidence"], l["exact"]) == (165, 15_763_121_797_048, "sur", True) and l["detail"]["new_record"]
    assert lire(GB_RESULTS.replace("Hunter Rank 6 2,000,000,000,000\n", ""), ["gb"])[0]["confidence"] == "a_verifier"   # 5 rangs lus
    g1, g2 = lire(GB_RECORD, ["gb"])
    assert [(g["team"], g["score"], g["damage"], g["confidence"], g["score_source"]) for g in (g1, g2)] == [
        (1, 167, 17_280_000_000_000, "sur", "record"), (2, 165, 15_550_000_000_000, "sur", "record")]
    assert g1["detail"]["total_score"] == 32_842_054_460_310 and g1["detail"]["time_left"] == "6d 9h"
    assert lire(GB_RECORD.replace("Total Rage Count 332", "Total Rage Count 330"), ["gb"])[0]["confidence"] == "a_verifier"


def test_hotm_et_poc():
    (l,) = lire(HOTM, ["hotm"], "HOTM 제 1관문")
    assert l["score"] == 94600 and l["confidence"] == "sur" and l["gate"] == 1 and l["stage"] == "기만자의 무대"   # jamais 기존 기록
    assert lire(HOTM.replace("93,100", "93,000"), ["hotm"])[0]["confidence"] == "a_verifier"
    (l,) = lire(POC, ["poc"])
    assert l["score"] == 131_449_789_393_717 and l["confidence"] == "a_verifier" and not l["exact"]   # 3 chasseurs non lus : pas de contrôle


def test_segments_et_dedoublonnage():
    cfg = CONFIG["pc"]["images"]
    assert pc.segments_tri(3, 300, cfg) == [(0, 10, 2), (270, 30, 2)]
    assert pc.segments_tri(3, 35, cfg) == [(0, 35, 2)] and pc.segments_tri(4, 300, cfg) == [(0, 300, 10)]
    memes = [ocr_ecrans.lectures_depuis_texte(GB_RESULTS, meta("a", ["gb"]), CONFIG, "debut-fin", t)[0] for t in (30, 4, 6)]
    assert [l["t"] for l in ocr_ecrans.dedoublonner_lectures(memes)] == [4]   # même écran lu 3 fois : la plus tôt


class OutilsImages:
    """Faux outils : chaque image `t` donne un texte OCR prédéfini par vidéo."""
    def __init__(self, textes):
        self.textes, self.appels = textes, []

    def sous_titres(self, vid, dossier):
        return ""

    def telecharger(self, vid, dossier):
        self.cur = vid
        self.appels.append(("dl", vid))
        return Path(dossier) / vid

    def images(self, chemin, segments, dossier):
        self.appels.append(("img", self.cur, tuple(segments)))
        return [(d + i * p, f"{self.cur}@{d + i * p}") for d, n, p in segments for i in range(0, n, p)]

    def reduire(self, png, largeur):
        return png

    def empreinte(self, png):
        return png

    def ocr(self, png, langues=None, psm=6, timeout=120):
        self.appels.append(("ocr", psm, langues))
        vid, t = png.split("@")
        return self.textes.get(vid, {}).get(int(t), "")


def test_passage_images_suffisant_puis_gel():
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"]["mode_guess"] = ["gb"]; videos["b"]["mode_guess"] = ["bot"]
        d.ecrire(f"runs/{SEM}/_videos.json", videos)
        o = OutilsImages({"a": {0: GB_RECORD, 2: GB_RECORD, 4: GB_RECORD}})
        r = pc.lancer("daily", INSTANT, d, config, o)
        p = d.processed()
        # a : le Personal Record (2 groupes sûrs) suffit -> pas de tri 4, vidéo terminée ; une seule lecture par groupe
        assert p["a"]["pc"]["tri3"] == "fait" and p["a"]["pc"]["tri4"] == "inutile" and p["a"]["status"] == "termine" and p["a"]["pc_needed"] is False
        lectures = [l for l in d.lectures(SEM) if l["video_id"] == "a"]
        assert sorted((l["team"], l["score"], l["score_source"]) for l in lectures) == [(1, 167, "record"), (2, 165, "record")]
        # b : rien de reconnu au tri 3 -> tri 4, puis fini sans score ; reste en_cours jusqu'au gel
        assert p["b"]["pc"]["tri3"] == "fait" and p["b"]["pc"]["tri4"] == "fait" and p["b"]["status"] == "en_cours" and p["b"]["last_tri"] == 4
        assert any(a[0] == "img" and a[1] == "b" and a[2] == ((0, 300, 10),) for a in o.appels)
        gb = (Path(tmp) / f"data/runs/{SEM}/gb.json")
        assert gb.exists()
        # 2e passage : rien n'est retraité (idempotent)
        o2 = OutilsImages({})
        pc.lancer("daily", INSTANT, d, config, o2)
        assert [a for a in o2.appels if a[0] == "dl"] == []   # aucune vidéo n'est retraitée (tri3/tri4 déjà faits)
        # gel : b (sans score) -> rejected pas_de_score ; lignes provisoires annotées « non vérifié »
        config["pc"]["geler"] = True
        r = pc.lancer("weekly", JEUDI, d, config, OutilsImages({}))
        assert d.meta(SEM)["frozen"] is True
        assert {x["video_id"]: x["reason"] for x in d.rejected(SEM)}.get("b") == "pas_de_score"
        lignes = d.lire(f"runs/{SEM}/poc.json", [])
        assert lignes and all("non vérifié" in l["notes"] for l in lignes if l["confidence"] != "sur")


def test_langues_et_marqueurs():
    cfg = CONFIG["pc"]["images"]
    assert pc.langues_ocr({"mode_guess": ["bot"]}, cfg) == "eng" and pc.langues_ocr({"mode_guess": ["hotm"]}, cfg) == "kor+eng"
    assert pc.langues_ocr({"mode_guess": ["gb", "poc"]}, cfg) == "eng+kor" and pc.langues_ocr({"mode_guess": []}, cfg) == cfg["ocr_langues"]
    assert pc.ressemble_ecran("Results\nBaruka") and pc.ressemble_ecran("합산 결과") and not pc.ressemble_ecran("blabla")


def test_ocr_rapide_filtre_et_max_images():
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        for v in "abcd":
            videos[v]["mode_guess"] = ["gb"]
        d.ecrire(f"runs/{SEM}/_videos.json", videos)

        o = OutilsImages({"a": {0: GB_RECORD}})
        lignes = []
        r = pc.lancer("daily", INSTANT, d, config, o, maximum=2, journal=lignes.append)
        assert [a[1] for a in o.appels if a[0] == "dl"] == ["a", "b"]                 # --max limite aussi les images
        psms = [a[1] for a in o.appels if a[0] == "ocr"]
        assert psms.count(11) >= 2 and psms.count(6) == 1                           # complet seulement sur l'écran candidat
        assert all(a[2] == "eng" for a in o.appels if a[0] == "ocr")                # GB : anglais seul
        assert any("candidate" in l and "[1/2]" not in l for l in lignes) and any(l.startswith("[2/2] b") for l in lignes)
        assert d.processed()["c"].get("pc") is None


def test_images_budget_video_partiel_puis_abandon():
    config = charger_config()
    config["pc"]["images"]["budget_video_min"] = 1
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        t = iter(range(0, 100_000, 30))
        o = OutilsImages({})
        for essai in (1, 2):
            r = pc.lancer("daily", INSTANT, d, config, o, maximum=1, horloge=lambda: next(t))
            etat = d.processed()["a"]["pc"]
            assert etat["essais"] == essai
            assert etat["tri3"] == ("partiel" if essai == 1 else "fait")
        assert any("abandonnées" in a for a in r["alertes"])


def test_publier_essai():
    import subprocess
    import tempfile
    cmds = []

    def faux(cmd, **kw):
        cmds.append(cmd)
        Path(cmd[-1]).write_bytes(b"jpg")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    class FauxGit:
        def __init__(self):
            self.appels = []

        def pousser_chemin(self, message, chemin):
            self.appels.append((message, chemin))

    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "logs", Path(tmp) / "docs"
        src.mkdir()
        for nom, texte in (("v_tri4_100", "long texte" * 9), ("v_tri3_4", "x"), ("v_tri4_50", "mid text")):
            (src / f"{nom}.txt").write_text(texte, encoding="utf-8")
            (src / f"{nom}.png").write_bytes(b"png")
        g = FauxGit()
        noms = pc.publier_essai(pc.Outils(CONFIG["pc"], executer=faux), src, dst, g, maximum=2)
        assert sorted(noms) == ["v_tri4_100.jpg", "v_tri4_100.txt", "v_tri4_50.jpg", "v_tri4_50.txt"]   # les 2 textes les plus longs
        assert (dst / "v_tri4_100.jpg").exists() and not (dst / "v_tri3_4.txt").exists() and len(g.appels) == 1


def test_commandes_des_outils():
    """Lignes de commande yt-dlp / ffmpeg / tesseract (outils absents ici : exécuteur simulé)."""
    import subprocess
    import tempfile
    cmds = []

    def faux(cmd, **kw):
        cmds.append(cmd)
        dossier = Path(next((c for c in cmd if "%(ext)s" in c or "%04d" in c), "/x/y")).parent
        if cmd[0] == "yt-dlp":
            (dossier / "vid1.mp4").write_bytes(b"")
        if cmd[0] == "ffmpeg" and any("fps=" in c for c in cmd):
            for i in (1, 2, 3):
                (dossier / f"f{len([c for c in cmds if c[0] == 'ffmpeg']) - 1}_{i:04d}.png").write_bytes(b"")
        return subprocess.CompletedProcess(cmd, 0, stdout="texte lu", stderr="")

    o = pc.Outils(CONFIG["pc"], executer=faux)
    with tempfile.TemporaryDirectory() as tmp:
        chemin = o.telecharger("vid1", tmp)
        assert chemin.name == "vid1.mp4" and cmds[0][:3] == ["yt-dlp", "-f", "bv*[height<=720]/b[height<=720]"]
        imgs = o.images(chemin, [(0, 10, 2), (270, 30, 2)], tmp)
        assert [t for t, _ in imgs] == [0, 2, 4, 270, 272, 274]
        ff = [c for c in cmds if c[0] == "ffmpeg"]
        assert ff[1][ff[1].index("-ss") + 1] == "270" and "fps=1/2" in ff[1] and ff[0][ff[0].index("-t") + 1] == "10"
        assert o.ocr(imgs[0][1]) == "texte lu" and cmds[-1][:2] == ["tesseract", str(imgs[0][1])] and "eng+kor+jpn" in cmds[-1]
        assert o.ocr(imgs[0][1], "eng", 11)  and cmds[-1][cmds[-1].index("-l") + 1] == "eng" and cmds[-1][-1] == "11"
        o.reduire(imgs[0][1], 960)
        assert cmds[-1][0] == "ffmpeg" and "scale=960:-2" in cmds[-1]
    try:
        pc.Outils(CONFIG["pc"]).ocr("x.png")   # tesseract absent de cet environnement
    except pc.OutilAbsent as e:
        assert "tesseract" in str(e)


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn(); print("ok", nom)
