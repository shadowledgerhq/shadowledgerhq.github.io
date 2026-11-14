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
        return [(d + i, f"{self.cur}@{d + i}") for d, n, p in segments for i in range(0, n, p)]

    def reduire(self, png, largeur):
        return png

    zones = {}      # {(vidéo, t): {"boss": texte, "joueur": texte}} : texte lu dans les recadrages

    def recadrer(self, png, zone, echelle=3):
        nom = next(n for n, z in CONFIG["gb"]["zones"].items() if list(z) == list(zone))
        return f"{png}#{nom}"

    def dimensions(self, png):
        return (1280, 720)

    def hauteurs(self, vid):
        return [360, 720, 1080]

    def empreinte(self, png):
        return png

    def ocr(self, png, langues=None, psm=6, timeout=120, extra=None):
        self.appels.append(("ocr", psm, langues))
        if "#" in png:
            base, zone = png.split("#")
            vid, t = base.split("@")
            return self.zones.get((vid, int(t)), {}).get(zone, "")
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
        noms = pc.publier_essai(pc.Outils(CONFIG["pc"], executer=faux), src, dst, g, maximum=2, resume={"semaine": "x", "lectures": []})
        assert sorted(noms) == ["_resume.json", "v_tri3_4.jpg", "v_tri3_4.txt", "v_tri4_50.jpg", "v_tri4_50.txt"]     # fin de vidéo (tri 3) puis images réparties (tri 4)
        assert "v_tri4_100.txt" in (dst / "_resume.json").read_text(encoding="utf-8")   # les 2 textes les plus longs
        assert (dst / "v_tri4_50.jpg").exists() and not (dst / "v_tri4_100.txt").exists() and len(g.appels) == 1


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


HUD_238 = """, LV.150GiantStalual 호 =.
Ld ol > a 해 뜨 0 a0 = 097 @) 1.00 |
| points 1593,669,209 , 8 SY ©) fal ae, VES
Boss Rage Count x12 | | WARNING } | = ‘ r
시 00:1.00
"""
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
# image plus nette de la même animation (titre, boss, Player's Score lisibles ; Hunter Rank pas encore affichés)
RESULTS_253 = RESULTS_252.replace("R a S Ul | tS @ Play Time 03:00", "Results @ Play Time 03:00\nGiant Statue").replace(
    "Player's Score\n[ 0\n| a.089.008 / - >,", "Player's Score\n313,099,049")


def _m(vid="lGDbzyIJcjY"):
    return {**meta(vid, ["gb"]), "title": "BEST WIND BUILD"}


def test_v12_hud_information_seulement():
    assert ocr_ecrans.detecter(HUD_228) == "gb_combat" and ocr_ecrans.detecter(RESULTS_GB) == "gb_results"
    assert ocr_ecrans.detecter(RESULTS_252) == "gb_results"          # sans le mot « Results » : Final Score + bandeau suffisent
    (l,) = ocr_ecrans.lectures_depuis_texte(HUD_228, _m(), CONFIG, "debut-fin", 228)
    assert l["score"] is None and l["score_source"] is None and l["confidence"] == "a_verifier" and l["t"] == 228 and l["regles"] == CONFIG["tri1_version"]   # jamais un RC
    assert l["detail"]["hud_points"] == 1540584556 and l["detail"]["chrono_hud"] == 10.45 and l["detail"]["hud_rage_count"] == 12
    assert ocr_ecrans.lectures_depuis_texte(HUD_50, _m(), CONFIG, "video-complete", 50)[0]["detail"]["hud_rage_count"] == 6   # « Rage Coun »
    assert ocr_ecrans.lectures_depuis_texte(HUD_130, _m(), CONFIG, "video-complete", 130) == []    # Boss Rage Count illisible (xd)
    assert ocr_ecrans.detecter(HUD_170) is None
    assert ocr_ecrans.chrono_hud("Points 1,540,584,556 02:40") == 160 and ocr_ecrans.chrono_hud("Points 1,540,584,556") is None
    (g,) = ocr_ecrans.lectures_depuis_texte(HUD_238, _m(), CONFIG, "debut-fin", 238)
    assert g["detail"]["chrono_hud"] == 1.0 and g["detail"]["hud_points"] == 1593669209            # « WARNING » ignoré
    assert pc.ressemble_ecran("WARNING 00:1.00") and pc.ressemble_ecran("Your points have been registered.")


def test_v12_regroupement_et_degats_provisoires():
    brut = lambda rc, chrono, pts, t: ocr_ecrans.lectures_depuis_texte(
        f"Points {pts:,}\nBoss Rage Count x{rc}\n{int(chrono // 60):02d}:{int(chrono % 60):02d}", _m("v"), CONFIG, "video-complete", t)[0]
    run1 = [brut(2, 150, 10_000, 30), brut(5, 100, 50_000, 80), brut(9, 20, 90_000, 160)]       # chrono min 20 s > 5 s : pas de dégâts
    run2 = [brut(1, 170, 5_000, 300), brut(4, 60, 70_000, 380), brut(6, 4, 99_000, 436)]
    fin = ocr_ecrans.regrouper_hud(run1 + run2, CONFIG)
    assert sorted((l["t"], l["detail"]["hud_rage_count"], l["damage"], l["score"]) for l in fin) == [
        (160, 9, None, None), (436, 6, 99_000, None)]
    r2 = [l for l in fin if l["t"] == 436][0]
    assert r2["detail"]["damage_exact"] is False and r2["detail"]["damage_source"] == "hud"
    assert len(ocr_ecrans.regrouper_hud(fin + run2, CONFIG)) == 2                                  # idempotent
    # le HUD ne remplace jamais une lecture de texte
    texte = {**fin[0], "mode": "gb", "score": 165, "score_source": "titre", "detail": {}}
    assert [l["score"] for l in pc.fusionner_ecrans([texte], "v", fin, CONFIG) if l["score_source"] == "titre"] == [165]


def _hud(t, texte=HUD_238):
    return ocr_ecrans.lectures_depuis_texte(texte, _m(), CONFIG, "debut-fin", t)


RESULTS_252_EXT = "| OT Na. a 7 Z\nYour points have been registered.\na 6 2 ~\n\nX\n"
RESULTS_253_REEL = "2\nWw\nRage Rewards\nx ¢.\n\\ ：\n; 58,465,656\nTap the screen to continue.\nNew Record Achic\n"
VIDE = {"format_ok": True}
Z_252 = {**VIDE, "boss": "Giant Statue", "joueur": "313,099,049", "final": "1,601,097,999", "rage": "19", "temps": "03:00"}
Z_253 = {**VIDE, "boss": "Giant Statue", "joueur": "313,099,049", "rang_4": "62,925,780", "rang_5": "58,465,656",
         "rang_6": "22,280,102", "final": "1,601,097,999", "rage": "19", "temps": "03:00"}


def _res(texte, t, zones=None):
    return ocr_ecrans.lectures_depuis_texte(texte, _m(), CONFIG, "debut-fin", t, zones)[0]


def _un_ecran(lectures):
    out = [l for l in pc.fusionner_ecrans([], "lGDbzyIJcjY", lectures, CONFIG) if l["mode"] == "gb" and l["score"] is not None]
    assert len(out) == 1
    return out[0]


def test_v13_cas_lGDbzyIJcjY_fusion_et_controle():
    """Cas de la spec : RC 19 lu à 252 s et 253 s ; HUD 1 596 246 179 ≤ 1 601 097 999 ≤ 1 628 171 102 ; Hunter Rank 4-6 lus."""
    hud = _hud(238, HUD_238.replace("1593,669,209", "1596,246,179"))
    r252, r253 = _res(RESULTS_252, 252, Z_252), _res(RESULTS_253_REEL, 253, Z_253)
    assert r253["score"] == 19 and r253["detail"]["new_record"] is True                       # bandeau « New Record Achieved! » à 253 s
    res = _un_ecran([r252, r253] + hud)
    d = res["detail"]
    assert (res["score"], res["damage"], res["exact"], res["confidence"], res["stage"], res["t"]) == (19, 1601097999, True, "sur", "Giant Statue", 252)
    assert d["new_record"] is True and d["hunter_ranks"] == [None, None, None, 62925780, 58465656, 22280102] and d["player_score"] == 313099049
    assert d["rc_images"] == 2 and d["final_images"] == 2 and d["n_images"] == 2 and d["hud_rage_count"] == 12
    assert "lecture fusionnée (2 images)" in res["notes"] and "contrôle sans Hunter Rank" in res["notes"]
    assert 1596246179 <= 1601097999 <= 1628171102
    # idempotent : refusionner la lecture fusionnée avec les images ne double pas les votes
    again = _un_ecran([res, _res(RESULTS_253_REEL, 253, Z_253)] + hud)
    assert again["detail"]["rc_images"] == 3 and again["confidence"] == "sur"


def test_v13_controle_sans_hunter_rank_durci():
    hud = _hud(238, HUD_238.replace("1593,669,209", "1596,246,179"))
    r252, r253 = _res(RESULTS_252, 252, Z_252), _res(RESULTS_253_REEL, 253, Z_253)
    # (2) Rage Count sur une seule image -> a_verifier
    une = _un_ecran([r253] + hud)
    assert une["confidence"] == "a_verifier" and "contrôle sans Hunter Rank : Rage Count lu sur une seule image" in une["notes"]
    # (3) Final Score hors de [Points ; Points × 1,02] -> a_verifier
    haut = _un_ecran([r252, r253] + _hud(238, HUD_238.replace("1593,669,209", "1500,000,000")))
    assert haut["confidence"] == "a_verifier" and any("hors de [Points HUD" in n for n in haut["notes"])
    # (3) sans HUD : Final Score identique sur 2 images ET (4) -> sûr
    sans = _un_ecran([r252, r253])
    assert sans["confidence"] == "sur" and sans["detail"]["final_images"] == 2
    # (4) Hunter Rank non décroissants -> a_verifier
    zc = {**Z_253, "rang_4": "22,280,102", "rang_6": "62,925,780"}
    bad = _un_ecran([r252, _res(RESULTS_253_REEL, 253, zc)])
    assert bad["confidence"] == "a_verifier" and "contrôle sans Hunter Rank : Hunter Rank lus non décroissants" in bad["notes"]
    # (4) Player's Score + Hunter Rank ≥ Final Score -> a_verifier
    zg = {**Z_253, "joueur": "1,600,000,000", "final": "1,601,097,999"}
    gros = _un_ecran([_res(RESULTS_252, 252, {**Z_252, "joueur": "1,600,000,000"}), _res(RESULTS_253_REEL, 253, zg)])
    assert gros["confidence"] == "a_verifier" and any("≥ Final Score" in n for n in gros["notes"])
    # (1) boss illisible -> a_verifier
    sb = _un_ecran([_res(RESULTS_252, 252, {**Z_252, "boss": ""}), _res(RESULTS_253_REEL, 253, {**Z_253, "boss": ""})])
    assert sb["confidence"] == "a_verifier" and "contrôle sans Hunter Rank : boss illisible" in sb["notes"]
    # les 6 Hunter Rank lus : somme habituelle (Player's Score + 6 Hunter Rank = Final Score)
    ok = ocr_ecrans.lectures_depuis_texte(RESULTS_GB, _m(), CONFIG, "debut-fin", 245)[0]
    assert ok["confidence"] == "sur" and "contrôle sans Hunter Rank" not in ok["notes"]
    assert _un_ecran([ok])["confidence"] == "sur"


def test_v13_conflit_de_lecture():
    a = _res(RESULTS_253_REEL, 253, Z_253)
    b = _res(RESULTS_253_REEL, 254, {**Z_253, "rage": "18"})
    res = _un_ecran([a, b])
    assert res["confidence"] == "a_verifier" and "conflit de lecture : rage_count" in res["notes"]
    # la valeur la plus fréquente l'emporte (pas de conflit)
    c = _res(RESULTS_253_REEL, 255, Z_253)
    res = _un_ecran([a, b, c])
    assert res["score"] == 19 and not any(n.startswith("conflit") for n in res["notes"]) and res["detail"]["rc_images"] == 2
    assert "RC discordant écarté : 18 (t=254)" in res["notes"]                               # v14 : 2 contre 1 accepté


def test_v14_vote_du_rage_count():
    img = lambda t, rc: _res(RESULTS_253_REEL, t, {**Z_253, "rage": str(rc)})
    ok = _un_ecran([img(252, 19), img(253, 19), img(254, 7)])                          # 2 contre 1 : retenu
    assert ok["score"] == 19 and ok["confidence"] == "sur" and "RC discordant écarté : 7 (t=254)" in ok["notes"]
    assert _un_ecran([img(252, 19), img(253, 19), img(254, 7), img(255, 7)])["confidence"] == "a_verifier"      # 2 contre 2
    trois = _un_ecran([img(252, 19), img(253, 19), img(254, 19), img(255, 7), img(256, 7)])                     # 3 contre 2
    assert trois["confidence"] == "a_verifier" and "conflit de lecture : rage_count" in trois["notes"]
    assert not any(n.startswith("RC discordant") for n in trois["notes"])
    quatre = _un_ecran([img(252, 19), img(253, 19), img(254, 19), img(255, 19), img(256, 7), img(257, 8)])      # 4 contre 2 : retenu
    assert quatre["score"] == 19 and [n for n in quatre["notes"] if n.startswith("RC discordant")] == [
        "RC discordant écarté : 7 (t=256)", "RC discordant écarté : 8 (t=257)"]
    # idempotent : refusionner la lecture fusionnée n'ajoute ni ne perd de note
    deux = _un_ecran([ok, img(255, 19)])
    assert deux["detail"]["rc_images"] == 3 and "RC discordant écarté : 7 (t=254)" in deux["notes"]
    assert [n for n in deux["notes"] if n.startswith("RC discordant")] == ["RC discordant écarté : 7 (t=254)"]


def test_v14_sans_hud_trois_hunter_rank_au_moins():
    hud = _hud(238, HUD_238.replace("1593,669,209", "1596,246,179"))
    r252 = _res(RESULTS_252, 252, Z_252)
    deux_rangs = {**Z_253, "rang_4": ""}                                               # seuls les rangs 5 et 6 sont lus (cas du 14/11)
    deux = _un_ecran([r252, _res(RESULTS_253_REEL, 253, deux_rangs)])
    assert deux["confidence"] == "a_verifier" and any("2 Hunter Rank lu(s) (3 au moins" in n for n in deux["notes"])
    avec_hud = _un_ecran([r252, _res(RESULTS_253_REEL, 253, deux_rangs)] + hud)        # avec HUD : inchangé, 0 à 6 rangs suffisent
    assert avec_hud["confidence"] == "sur"
    trois = _un_ecran([r252, _res(RESULTS_253_REEL, 253, Z_253)])                      # 3 rangs lus, sans HUD : accepté
    assert trois["confidence"] == "sur"


def test_v13_regroupement_des_images_d_un_ecran():
    # plus de 15 s entre la première et la dernière image : deux écrans distincts
    tard = _res(RESULTS_253_REEL, 270, {**Z_253, "rage": "18"})
    out = pc.fusionner_ecrans([], "lGDbzyIJcjY", [_res(RESULTS_253_REEL, 252, Z_253), tard], CONFIG)
    assert len([l for l in out if l["score"] is not None]) == 2
    # un HUD de combat entre deux images : deux écrans distincts (deux runs)
    hud = _hud(257)       # HUD à 257 s (chrono 1.00)
    out = pc.fusionner_ecrans([], "lGDbzyIJcjY", [_res(RESULTS_253_REEL, 253, Z_253), _res(RESULTS_253_REEL, 260, {**Z_253, "rage": "18"})] + hud, CONFIG)
    assert len([l for l in out if l["score"] is not None]) == 2
    # écran vu sans Rage Count lisible : pas classé
    assert pc.fusionner_ecrans([], "lGDbzyIJcjY", [_res(RESULTS_252_EXT, 252, VIDE)], CONFIG) == []


def test_v13_zones_ecart_et_format():
    # la zone prime sur l'image entière ; l'écart est noté
    r = _res(RESULTS_252, 252, {**Z_252, "final": "1,601,097,998"})
    assert r["damage"] == 1601097998 and "écart OCR zone/image : final_score" in r["notes"]
    assert "écart OCR zone/image : player_score" in r["notes"] and r["detail"]["player_score"] == 313099049   # image entière : 89 008
    # format non 16:9 : zones non appliquées
    f = _res(RESULTS_252, 252, {"format_ok": False})
    assert "format non standard" in f["notes"] and f["detail"]["player_score"] == 89008
    # lecture des zones par pc : fractions, format
    class O:
        cfg = CONFIG["pc"]
        appels = []

        def __init__(self, taille):
            self.taille = taille

        def dimensions(self, png):
            return self.taille

        def recadrer(self, png, zone, echelle=3):
            self.appels.append(zone)
            assert all(0 <= v <= 1 for v in zone)                       # fractions, jamais des pixels
            return png

        def ocr(self, png, langues=None, psm=6, timeout=120, extra=None):
            return "1"
    o = O((1280, 720))
    z = pc.lire_zones_results(o, "x.png", CONFIG)
    assert z["format_ok"] and set(CONFIG["gb"]["zones"]) <= set(z) and len(o.appels) == len(CONFIG["gb"]["zones"])
    assert {"boss", "joueur", "final", "rage", "temps", *[f"rang_{k}" for k in range(1, 7)]} == set(CONFIG["gb"]["zones"])
    assert pc.lire_zones_results(O((1080, 1920)), "x.png", CONFIG) == {"format_ok": False}      # Short vertical
    assert pc.lire_zones_results(O((1440, 1080)), "x.png", CONFIG) == {"format_ok": False}      # 4:3
    assert pc.lire_zones_results(O((1920, 1080)), "x.png", CONFIG)["format_ok"]                 # 1080p 16:9


def test_v13_cas_lGDbzyIJcjY_de_bout_en_bout():
    """Textes OCR réels du 14/11 : HUD à 228 s et 238 s, Results à 252 s (valeurs, titre/boss illisibles), puis images de
    l'animation sans valeurs lisibles ; les zones ciblées complètent. RC 19 sûr, new_record, ligne gb a_verifier."""
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], duration="PT4M14S")           # 254 s
        d.ecrire(f"runs/{SEM}/_videos.json", videos)

        class Faux(OutilsImages):
            zones = {("a", 252): Z_252, ("a", 253): Z_253}

            def images(self, chemin, segments, dossier, prefixe="f"):
                self.appels.append(("img", self.cur, tuple(segments), prefixe))
                return [(d_ + i, f"{self.cur}@{d_ + i}") for d_, n, p in segments for i in range(0, n, p)]

            def ocr(self, png, langues=None, psm=6, timeout=120, extra=None):
                if "#" not in png and self.appels and self.appels[-1][0] == "img" and self.appels[-1][3] != "f":
                    self.ext = True                                          # images de recherche de l'écran Results
                if "#" not in png and getattr(self, "ext", False) and png in ("a@252", "a@253"):
                    return {"a@252": RESULTS_252_EXT, "a@253": RESULTS_253_REEL}[png]
                if "#" in png:
                    base, zone = png.split("#")
                    vid, t = base.split("@")
                    return self.zones.get((vid, int(t)), {}).get(zone, "")
                return super().ocr(png, langues, psm, timeout)
        HUD_FIN = HUD_238.replace("1593,669,209", "1596,246,179")
        o = Faux({"a": {228: HUD_228, 238: HUD_FIN, 252: RESULTS_252}})
        lignes = []
        pc.lancer("daily", INSTANT, d, config, o, maximum=1, journal=lignes.append, ocr_debug=Path(tmp) / "dbg")
        assert any("formats disponibles : 360p, 720p, 1080p" in x for x in lignes) and any("image lue : 1280x720" in x for x in lignes)
        bil = pc.bilan_essai(d, SEM, {"a"}, config)["par_video"]["a"]
        assert bil["formats_disponibles_p"] == [360, 720, 1080] and bil["image_lue_px"] == [1280, 720] and bil["ecran_results_lu"]
        r0 = bil["resultats"][0]
        assert r0["rage_count"] == 19 and r0["final_score"] == 1601097999 and r0["hud_points"] == 1596246179
        assert r0["ecart_hud_final_pct"] == round((1601097999 - 1596246179) / 1596246179 * 100, 3)
        assert [a[2] for a in o.appels if a[0] == "img" and a[3] != "f"] == [((252, 2, 1),)]
        lec = [l for l in d.lectures(SEM) if l["video_id"] == "a" and l["mode"] == "gb" and l.get("score") is not None]
        assert len(lec) == 1
        l = lec[0]
        assert (l["score"], l["damage"], l["exact"], l["confidence"], l["stage"]) == (19, 1601097999, True, "sur", "Giant Statue")
        assert l["t"] == 252 and "contrôle sans Hunter Rank" in l["notes"] and l["detail"]["new_record"] is True
        assert l["regles"] == config["tri1_version"] == 13
        assert l["detail"]["hunter_ranks"][3:] == [62925780, 58465656, 22280102] and l["detail"]["player_score"] == 313099049
        assert any(n.startswith("lecture fusionnée (") for n in l["notes"])
        huds = [x for x in d.lectures(SEM) if (x.get("detail") or {}).get("ecran") == "combat"]
        assert huds and all(x["score_source"] is None and x["score"] is None for x in huds)            # HUD : jamais une source de score
        ligne = lire_gb(d)
        assert ligne["confidence"] == "a_verifier" and ligne["rank"] is None and "une seule run trouvée" in ligne["notes"]
        rd = ligne["runs_detail"][0]
        assert rd["damage"] == 1601097999 and rd["damage_exact"] is True and rd["hud_rage_count"] == 12 and "points_hud" not in rd
        assert ligne["score"]["runs"] == [19]
        assert d.processed()["a"]["pc"]["results_lus"] == [[252, 253]]
        # 2e passage : aucune relecture de l'écran Results
        o2 = Faux({"a": {228: HUD_228, 238: HUD_FIN, 252: RESULTS_252}})
        pc.lancer("daily", INSTANT, d, config, o2, maximum=1)
        assert not [a for a in o2.appels if a[0] == "img" and a[3] != "f"]


SALON_RECORD = "< Guild Boss ? mn!\n© Time tettin season 6d 9h Personal Record @\nTotal Score Challenge Count 2\n32,842,054480,310 | totatragecoune 332\nGroup? 167 17.281\n(BR) rage rewards 100,000\n"


def test_v14_salon_guild_boss_pas_un_results():
    """Salon Guild Boss (essai du 14/11, nh2D7xZ7dOQ à 2 s) : le bouton « Rage Rewards » n'est pas un écran Results."""
    assert ocr_ecrans.detecter(SALON_RECORD) == "gb_record"            # OCR abîmé (« Total Rage Gount », « Group? ») toléré
    assert ocr_ecrans.detecter("Rage Rewards\n100,000") is None and ocr_ecrans.detecter("Guild Boss\nRage Rewards") is None
    assert ocr_ecrans.detecter("Rage Rewards\nTap the screen to continue.") == "gb_results_partiel"
    assert ocr_ecrans.lectures_depuis_texte(SALON_RECORD, _m(), CONFIG, "debut-fin", 2, VIDE) == []   # pas de lecture parasite (RC 3)


def test_ffmpeg_sans_stdin_et_nouvelle_tentative():
    import subprocess
    import tempfile
    appels = []

    def faux(cmd, **kw):
        appels.append((cmd, kw.get("stdin")))
        if cmd[0] == "ffmpeg" and sum(1 for c, _ in appels if c[0] == "ffmpeg") == 1:
            raise subprocess.TimeoutExpired(cmd, kw["timeout"])           # 1er essai bloqué
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    o = pc.Outils(CONFIG["pc"], executer=faux)
    with tempfile.TemporaryDirectory() as tmp:
        o.images(Path(tmp) / "v.mp4", [(0, 10, 2)], tmp)
    ff = [(c, i) for c, i in appels if c[0] == "ffmpeg"]
    assert len(ff) == 2 and "-nostdin" in ff[0][0] and ff[0][1] == subprocess.DEVNULL            # une seule nouvelle tentative


def test_v12_boss_et_player_score_par_zone():
    c = {"gb": {"boss_noms": ["Giant Statue"]}}
    assert ocr_ecrans.boss_connu("Giant Statue", c) == "Giant Statue" and ocr_ecrans.boss_connu("Gaint Statue\n", c) == "Giant Statue"
    assert ocr_ecrans.boss_connu("Temple Altar", c) is None and ocr_ecrans.boss_connu("", c) is None
    assert ocr_ecrans._nombre_zone("313,099,049") == 313099049 and ocr_ecrans._nombre_zone("a.089.008") is None
    assert ocr_ecrans.detecter(RESULTS_252_EXT) == "gb_results_partiel" and ocr_ecrans.detecter(RESULTS_253_REEL) == "gb_results_partiel"
    (p,) = ocr_ecrans.lectures_depuis_texte(RESULTS_253_REEL, _m(), CONFIG, "debut-fin", 253)
    assert p["score"] is None and p["detail"]["ecran"] == "results_partiel"       # « Rage Rewards » / « Tap the screen » : jamais des valeurs
    assert pc.fusionner_ecrans([], "lGDbzyIJcjY", [p], CONFIG) == []


def test_v12_hud_sans_results_degats_provisoires_et_pas_de_rc():
    config = charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], duration="PT4M14S", title="Guild boss 165RC best team")
        d.ecrire(f"runs/{SEM}/_videos.json", videos)
        # lecture du titre : 165 RC (sans dégâts)
        from tri1 import lectures_texte
        d.ecrire(f"runs/{SEM}/_lectures.json", lectures_texte(videos["a"], [("titre", videos["a"]["title"])], config)[0])
        pc.lancer("daily", INSTANT, d, config, OutilsImages({"a": {228: HUD_228, 238: HUD_238}}), maximum=1)
        assert [l["score"] for l in d.lectures(SEM) if l["mode"] == "gb" and l["score"] is not None] == [165]   # le HUD n'est jamais un RC
        ligne = lire_gb(d)
        rd = ligne["runs_detail"][0]
        assert ligne["score"]["runs"] == [165] and rd["damage"] == 1593669209 and rd["damage_exact"] is False
        assert rd["damage_source"] == "hud" and rd["hud_rage_count"] == 12 and "points_hud" not in rd
        import gb
        assert gb.degats({"damage": 5, "detail": {"damage_source": "hud"}}) == 0 and gb.degats({"damage": 5, "detail": {}}) == 5   # jamais pour le départage


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



def lire_gb(d):
    import json
    return json.loads((Path(d.data) / "runs" / SEM / "gb.json").read_text(encoding="utf-8"))[0]


def test_dimensions_png_et_ocr_chiffres():
    import struct
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 1280, 720) + b"\x08\x02\x00\x00\x00")
        o = pc.Outils(CONFIG["pc"])
        assert o.dimensions(f) == (1280, 720) and o.dimensions(Path(tmp) / "absent.png") is None
        (Path(tmp) / "b.png").write_bytes(b"pas un png")
        assert o.dimensions(Path(tmp) / "b.png") is None
    cmds = []
    o2 = pc.Outils(CONFIG["pc"], executer=lambda cmd, **kw: cmds.append(cmd) or subprocess.CompletedProcess(cmd, 0, stdout="19", stderr=""))
    assert o2.ocr("z.png", "eng", 7, 40, ["-c", "tessedit_char_whitelist=0123456789,.:"]) == "19"
    assert cmds[-1][-2:] == ["-c", "tessedit_char_whitelist=0123456789,.:"] and cmds[-1][cmds[-1].index("--psm") + 1] == "7"


def test_hauteurs_et_publication_par_video():
    import subprocess
    import tempfile
    F = """ID  EXT RESOLUTION FPS | FILESIZE
251 webm audio only tiny 130k
18  mp4  640x360   30 |
247 webm 1280x720  30 |
137 mp4  1920x1080 30 |
"""
    o = pc.Outils(CONFIG["pc"], executer=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=F, stderr=""))
    assert o.hauteurs("x") == [360, 720, 1080]
    cmds = []

    def faux(cmd, **kw):
        cmds.append(cmd)
        Path(cmd[-1]).write_bytes(b"jpg")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "logs", Path(tmp) / "docs"
        src.mkdir()
        for vid in ("Oj_-5x6700s", "a-923ClD9Rc"):                          # identifiants avec « _ » et « - »
            for nom in ("tri3_228_gb_combat", "tri3_252_gb_results", "tri4_30", "recherche_253"):
                (src / f"{vid}_{nom}.txt").write_text("x" * len(nom), encoding="utf-8")
                (src / f"{vid}_{nom}.png").write_bytes(b"png")
        noms = pc.publier_essai(pc.Outils(CONFIG["pc"], executer=faux), src, dst, None, maximum=2, resume={"a": 1}, nom_resume="_resume_2videos.json")
        assert "_resume_2videos.json" in noms and (dst / "_resume_2videos.json").exists()
        for vid in ("Oj_-5x6700s", "a-923ClD9Rc"):
            assert len([n for n in noms if n.startswith(vid) and n.endswith(".txt")]) == 2     # 2 fichiers par vidéo
            assert f"{vid}_tri3_252_gb_results.txt" in noms and f"{vid}_tri3_228_gb_combat.txt" in noms   # écrans reconnus d'abord


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
        o.recadrer(imgs[0][1], (0.02, 0.1, 0.18, 0.07))
        assert cmds[-1][0] == "ffmpeg" and "crop=iw*0.18:ih*0.07:iw*0.02:ih*0.1,scale=iw*3:-1,format=gray" in cmds[-1]
    try:
        pc.Outils(CONFIG["pc"]).ocr("x.png")   # tesseract absent de cet environnement
    except pc.OutilAbsent as e:
        assert "tesseract" in str(e)


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn(); print("ok", nom)
