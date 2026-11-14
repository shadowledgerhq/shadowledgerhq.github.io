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

    def images(self, chemin, segments, dossier, prefixe="f"):
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
    config["pc"]["images"]["tri3_ocr_complet"] = False      # le tri 3 est complet par défaut (v11) ; ici on teste le filtre
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
        assert any("OCR complet" in l for l in lignes) and any(l.startswith("[2/2] b") for l in lignes)
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


# --- v11 : HUD du combat GB (textes OCR réels de docs/essais/ocr, vidéo lGDbzyIJcjY) -----------------------------------

HUD_228 = """\\ ~~
| LVBBaiciant statue | \\ =. Wi -
ee 08 시승 _ = 는 > "\\ (®) 10.45 ul
Points 1540,584,556 / RD Pda a. a oo ti ‘
__ Boss Rage Count x12 . / wi 1: j st
The boss monster refuses to die and becomes enra ged!)
"""
HUD_50 = "Ti Mam Of wre . 아만 1D x75 © 02:40 i\nPoints 99,530,637 | ian he ta 7\n__ Boss Rage Coun x6 )/ ) | . NK\n"
HUD_70 = "x164 © 02:27 |\n Points 770,387,441 Nees\n | Boss Rage Count x7 1」 \\ 4\n"
HUD_130 = "LV. 150 Temple Altar ㄴ a {\n09 . = 0296“ —_ / iy) 01:34 1\nPoints 1057342822 \\ |\nBoss Rage Count xd - wp 4 때\n"
HUD_170 = "Points - ㆍ 1201006080 ‘ % ' 630 34 나\n Boss RageCount/ 0 00 2000 7\n"
RESULTS_GB = "Results\nGiant Statue\nPlayer's Score 3,000\nHunter Rank 1 100\nHunter Rank 2 100\nHunter Rank 3 100\nHunter Rank 4 100\nHunter Rank 5 100\nHunter Rank 6 100\nFinal Score 3,600\nRage Gount 12\nPlay Time 03:00\n"


def test_v11_hud_gb():
    assert ocr_ecrans.detecter(HUD_228) == "gb_combat" and ocr_ecrans.detecter(RESULTS_GB) == "gb_results"
    m = {**meta("lGDbzyIJcjY", ["gb"]), "title": "BEST WIND BUILD"}
    (l,) = ocr_ecrans.lectures_depuis_texte(HUD_228, m, CONFIG, "debut-fin", 228)
    assert l["score"] == 12 and l["confidence"] == "a_verifier" and l["exact"] is False and l["t"] == 228
    assert l["detail"]["points_hud"] == 1540584556 and l["detail"]["chrono_hud"] == 10.45 and l["stage"] is None
    assert ocr_ecrans.lectures_depuis_texte(HUD_50, m, CONFIG, "video-complete", 50)[0]["score"] == 6     # « Rage Coun »
    assert ocr_ecrans.lectures_depuis_texte(HUD_130, m, CONFIG, "video-complete", 130) == []              # RC illisible (xd) : ignorée
    assert ocr_ecrans.detecter(HUD_170) is None                                                            # sans les 3 éléments
    (r,) = ocr_ecrans.lectures_depuis_texte(RESULTS_GB, m, CONFIG, "debut-fin", 245)
    assert r["score"] == 12 and r["stage"] == "Giant Statue"                                               # « Rage Gount » toléré
    assert ocr_ecrans.chrono_hud("Points 1,540,584,556 02:40") == 160 and ocr_ecrans.chrono_hud("Points 1,540,584,556") is None
    cible = ocr_ecrans.lectures_depuis_texte("LV. 150 Temple Altar\n01:34\nPoints 5\nBoss Rage Count x3", m, CONFIG, "x", 1)[0]
    assert cible["stage"] is None                                                                           # cible secondaire : jamais le stage


RESULTS_252 = """R a S Ul | tS @ Play Time 03:00
Player's Score
[ 0
| a.089.008 / - >,
Hunter Rank ¥ 7 rs " ( : Y ¢q 기
= : {ㅣ
0 < < 그 그룬 에 ES ~. Na
Your points have been registered.
Final Score Rage Count ®
1.601.097.999 19
"""


def test_v11_results_en_cours_d_affichage_texte_reel():
    """Écran Results vu à 252 s de lGDbzyIJcjY : valeurs sous les libellés, Hunter Rank pas encore affichés."""
    m = meta("lGDbzyIJcjY", ["gb"])
    assert ocr_ecrans.detecter(RESULTS_252) == "gb_results"
    (l,) = ocr_ecrans.lectures_depuis_texte(RESULTS_252, m, CONFIG, "debut-fin", 252)
    assert l["score"] == 19 and l["damage"] == 1601097999 and l["confidence"] == "a_verifier" and l["exact"] is False
    assert l["detail"]["damage_exact"] is True and any("contrôle GB" in n for n in l["notes"])
    out = pc.fusionner_ecrans([], "lGDbzyIJcjY", ocr_ecrans.lectures_depuis_texte(HUD_228, m, CONFIG, "debut-fin", 228) + [l], CONFIG)
    assert [(x["score"], x["score_source"]) for x in out] == [(19, "debut-fin")]    # le HUD (14-24 s avant) est remplacé


def test_v11_regroupement_par_run_et_remplacement_par_results():
    m = meta("v", ["gb"])
    brut = lambda rc, chrono, t: ocr_ecrans.lectures_depuis_texte(
        f"Points 5,000,000\nBoss Rage Count x{rc}\n{int(chrono // 60):02d}:{int(chrono % 60):02d}", m, CONFIG, "video-complete", t)[0]
    run1 = [brut(2, 150, 30), brut(5, 100, 80), brut(9, 20, 160)]
    run2 = [brut(1, 170, 300), brut(4, 60, 380)]                       # le chrono repart à la hausse : 2e run
    fin = ocr_ecrans.regrouper_hud(run1 + run2, CONFIG)
    assert sorted((l["t"], l["score"], l["score_source"]) for l in fin) == [(160, 9, "hud"), (380, 4, "hud")]
    assert ocr_ecrans.regrouper_hud(fin, CONFIG) and len(ocr_ecrans.regrouper_hud(fin + run2, CONFIG)) == 2     # idempotent
    # un écran Results dans les 60 s après la run 1 remplace sa lecture HUD ; la run 2 reste
    res = ocr_ecrans.lectures_depuis_texte(RESULTS_GB, m, CONFIG, "video-complete", 190)
    out = pc.fusionner_ecrans([], "v", run1 + run2 + res, CONFIG)
    assert sorted((l["t"], l["score"], l["score_source"]) for l in out) == [(190, 12, "video-complete"), (380, 4, "hud")]
    # un Personal Record retire tous les HUD
    rec = ocr_ecrans.lectures_depuis_texte(GB_RECORD, m, CONFIG, "debut-fin", 5)
    assert all(l["score_source"] != "hud" for l in pc.fusionner_ecrans([], "v", run1 + run2 + rec, CONFIG))


def test_v11_cas_lGDbzyIJcjY_recherche_results():
    """HUD à 228 s (chrono 10.45, RC 12) -> images de 228 à 254 s à 1 image/s jusqu'à l'écran Results (241 s)."""
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], duration="PT4M14S")           # 254 s
        d.ecrire(f"runs/{SEM}/_videos.json", videos)

        class Faux(OutilsImages):
            def images(self, chemin, segments, dossier, prefixe="f"):
                self.appels.append(("img", self.cur, tuple(segments), prefixe))
                return [(d_ + i * p, f"{self.cur}@{d_ + i * p}") for d_, n, p in segments for i in range(0, n, p)]
        o = Faux({"a": {228: HUD_228, 241: RESULTS_GB}})      # 241 : hors de la grille du tri 3 (1 image / 2 s)
        lignes = []
        r = pc.lancer("daily", INSTANT, d, config, o, maximum=1, journal=lignes.append)
        recherche = [a for a in o.appels if a[0] == "img" and a[3] != "f"]
        assert recherche and recherche[0][2] == ((228, 26, 1),)           # de 228 à la fin de la vidéo (254 s), 1 image/s
        lec = [l for l in d.lectures(SEM) if l["video_id"] == "a" and l["mode"] == "gb"]
        assert [(l["score"], l["score_source"], l["t"]) for l in lec] == [(12, "debut-fin", 241)]   # le HUD est remplacé par Results
        assert any("Results trouvé à 241" in l for l in lignes)
        assert d.processed()["a"]["pc"]["results_cherches"] == [228]
        # pas de nouvelle recherche au passage suivant
        o2 = Faux({})
        pc.lancer("daily", INSTANT, d, config, o2, maximum=1)
        assert not [a for a in o2.appels if a[0] == "img" and a[3] != "f"]


def test_refaire_une_video():
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], duration="PT4M14S")
        d.ecrire(f"runs/{SEM}/_videos.json", videos)
        pc.lancer("daily", INSTANT, d, config, OutilsImages({"a": {228: HUD_228}}), seulement={"a"})
        assert d.processed()["a"]["pc"]["tri4"] == "fait"
        o = OutilsImages({"a": {228: HUD_228}})
        pc.lancer("daily", INSTANT, d, config, o, seulement={"a"})
        assert not [x for x in o.appels if x[0] == "dl"]                                   # déjà fait : rien
        pc.lancer("daily", INSTANT, d, config, o, seulement={"a"}, refaire=True)
        assert [x for x in o.appels if x[0] == "dl"] == [("dl", "a")]                       # --refaire : retraitée


def test_v11_hud_sans_results_reste_provisoire():
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], duration="PT4M14S")
        d.ecrire(f"runs/{SEM}/_videos.json", videos)
        pc.lancer("daily", INSTANT, d, config, OutilsImages({"a": {228: HUD_228}}), maximum=1)
        (l,) = [l for l in d.lectures(SEM) if l["video_id"] == "a" and l["mode"] == "gb"]
        assert l["score_source"] == "hud" and l["score"] == 12 and l["confidence"] == "a_verifier" and l["detail"]["points_hud"] == 1540584556
        ligne = lire_gb(d)
        assert ligne["runs_detail"][0]["points_hud"] == 1540584556 and ligne["confidence"] == "a_verifier" and ligne["rank"] is None


def lire_gb(d):
    import json
    return json.loads((Path(d.data) / "runs" / SEM / "gb.json").read_text(encoding="utf-8"))[0]


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
