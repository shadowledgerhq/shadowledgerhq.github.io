"""SPEC_ETAPE1 v27 : RESULT du BOT lu par zone (temps de jeu, phases), repli `a_verifier`, anti-animation (temps lu sur ≥ 2 images)."""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ecrans
import ocr_ecrans as O
import pc
from donnees import charger_config

CFG = charger_config()
CAPT = Path(__file__).resolve().parents[2] / "docs" / "essais" / "composition"
META = {"video_id": "x", "channel_id": "c", "published_at": "2026-11-16T00:00:00Z", "title": "BOT", "mode_guess": ["bot"]}
# VRAI texte tesseract (jpn+eng, psm 6, image entière) de bot_results_sans_sjw_ja.png : Phase1 -> « Men 4 », 進行時間 -> 信行時間
JA_REEL = """RESULT.    : Nw Z ss,  \\           /    © 信行時間 nn2g
ZEDERES—IL        パ    ンっ 。
Men 4     00:04.734       .              He
Phase2        00:15.212     レグ2     |     1  |            ゴ
Phase 02           トノ              Ue"""
JA_REEL_1 = "人   意    |       Sand        ON\nPhase2    yi  .    a の  で   A   NM a.\n(Phases 7  人人li Lj)   ya \\   OX."     # capture 1 : aucun temps lu


class Tesseract:
    """Outils minimaux avec le vrai tesseract (les tests sont sautés s'il est absent)."""
    def dimensions(self, png):
        from PIL import Image
        return Image.open(png).size

    def ocr(self, png, langues=None, psm=6, timeout=40, extra=None):
        return subprocess.run(["tesseract", str(png), "stdout", "-l", langues or "eng", "--psm", str(psm), *(extra or [])],
                              capture_output=True, text=True).stdout


def _tesseract_ok():
    return shutil.which("tesseract") is not None


def _zones(nom, tmp_path):
    cible = Path(tmp_path) / "img.png"
    shutil.copy(CAPT / nom, cible)
    return pc.lire_zones_bot(Tesseract(), cible, CFG)


def _lecture(zb, t, texte="", cfg=CFG):
    l = O.lectures_depuis_texte(texte, META, cfg, "video-complete", t=t, zones={"bot": zb})
    assert len(l) == 1
    return l[0]


def _fusion(lectures):
    return pc.fusionner_ecrans([], "x", lectures, CFG)


def test_vote_zone_exige_un_accord_et_le_format_strict():
    assert O.vote_zone(["00:29", "00:29", "00:25"], O._TEMPS_JEU) == "00:29"
    assert O.vote_zone(["00:29", "00:25", ""], O._TEMPS_JEU) is None          # jamais une valeur lue une seule fois
    assert O.vote_zone(["010:04.734", "010:04.734"], O._TEMPS_STRICT) is None  # chiffre en trop : pas de lecture
    zb = O.zones_bot_lues([["00:04.734", "00:04.734"], ["00:15.212", "00:15.212"], ["00:10.000", "00:10.000"]], ["00:29", "00:29"], CFG)
    assert zb == {"phases": [4.734, 15.212], "temps_jeu": 29}                   # phases non croissantes : la liste est coupée


def test_libelle_ocr_信行時間_et_titre_結果():
    assert "信行時間" in O.libelles_bot("play_time", CFG) and "結果" in O.libelles_bot("titre", CFG)
    texte = "結果\nPhase1 00:04.734\nPhase2 00:15.212\nPhase3 00:29.224\n信行時間 00:29\nxx 00:29.224"
    assert O.detecter(texte, CFG) == "bot"
    e = O.lire_bot(texte, CFG)
    assert e["play_time"] == 29 and e["chrono"] == 29.224 and not e.get("via_zones")


def test_repli_titre_et_2_temps_a_verifier_jamais_sur():
    for texte in ("RESULT\nPhase1 00:04.734\nPhase2 00:15.212", "結果\nMen 4 00:04.734\nPhase2 00:15.212"):
        assert O.detecter(texte, CFG) == "bot"
        l = _fusion(O.lectures_depuis_texte(texte, META, CFG, "video-complete", t=5))
        assert len(l) == 1 and l[0]["confidence"] == "a_verifier" and ecrans.NOTE_BOT_TEMPS_NON_LU in l[0]["notes"]
    assert O.detecter("Phase2 00:15.212\nPhase3 00:20.000", CFG) is None          # sans titre ni zone : pas un RESULT


def test_captures_ja_lues_par_zone(tmp_path):
    if not _tesseract_ok():
        return
    z2 = _zones("bot_results_sans_sjw_ja.png", tmp_path)
    assert z2 == {"phases": [4.734, 15.212, 29.224], "temps_jeu": 29}
    z1 = _zones("bot_results_ja.png", tmp_path)
    assert z1 == {"phases": [9.095, 14.91, 19.558], "temps_jeu": None}          # temps de jeu masqué par le décor


def test_2e_capture_sur_apres_2_images_a_verifier_avec_une_seule(tmp_path):
    if not _tesseract_ok():
        return
    zb = _zones("bot_results_sans_sjw_ja.png", tmp_path)
    une = _lecture(zb, 10, JA_REEL)
    assert une["detail"]["v27_sur"] and une["score"] == 29.224 and une["stage"] is None      # lecture de l'image : cohérente
    seule = _fusion([une])
    assert seule[0]["confidence"] == "a_verifier" and ecrans.NOTE_BOT_INSTABLE in seule[0]["notes"]    # un temps vu sur 1 image : animation ?
    deux = _fusion([_lecture(zb, 10, JA_REEL), _lecture(zb, 12, JA_REEL)])
    assert len(deux) == 1 and deux[0]["confidence"] == "sur" and deux[0]["exact"] and ecrans.NOTE_BOT_INSTABLE not in deux[0]["notes"]
    assert deux[0]["detail"]["par_t"] == [10, 12] and deux[0]["score"] == 29.224
    # idempotent : relire les mêmes images ne double rien et ne change pas le verdict
    de_nouveau = pc.fusionner_ecrans(deux, "x", [_lecture(zb, 10, JA_REEL), _lecture(zb, 12, JA_REEL)], CFG)
    assert len(de_nouveau) == 1 and de_nouveau[0]["detail"]["par_t"] == [10, 12] and de_nouveau[0]["confidence"] == "sur"
    # la 1re lecture (1 image, a_verifier) devient sûre quand une 2e image la confirme à une fusion ultérieure
    suite = pc.fusionner_ecrans(seule, "x", [_lecture(zb, 12, JA_REEL)], CFG)
    assert suite[0]["confidence"] == "sur"


def test_1re_capture_au_moins_a_verifier(tmp_path):
    if not _tesseract_ok():
        return
    zb = _zones("bot_results_ja.png", tmp_path)
    l = O.lectures_depuis_texte(JA_REEL_1, META, CFG, "video-complete", t=7, zones={"bot": zb})
    assert len(l) == 1                                                              # reconnue par les zones, l'OCR entier n'a lu aucun temps
    r = _fusion(l + O.lectures_depuis_texte(JA_REEL_1, META, CFG, "video-complete", t=9, zones={"bot": zb}))
    assert r[0]["confidence"] == "a_verifier" and ecrans.NOTE_BOT_TEMPS_NON_LU in r[0]["notes"] and r[0]["score"] == 19.558


def test_temps_de_jeu_incoherent_a_verifier():
    zb = {"phases": [4.734, 15.212, 29.224], "temps_jeu": 15}
    r = _fusion([_lecture(zb, 1), _lecture(zb, 2)])
    assert r[0]["confidence"] == "a_verifier" and any("temps de jeu 15 ≠ dernière phase tronquée 29" in n for n in r[0]["notes"])


def test_animation_lecture_intermediaire_ecartee_si_la_run_est_stable():
    final = {"phases": [4.734, 15.212, 29.224], "temps_jeu": 29}
    partiel = {"phases": [4.734, 15.212], "temps_jeu": 29}                          # animation : Phase3 pas encore affichée
    r = _fusion([_lecture(partiel, 3), _lecture(final, 5), _lecture(final, 7)])
    assert len(r) == 1 and r[0]["score"] == 29.224 and r[0]["confidence"] == "sur"
    assert "lectures instables du même run écartées" in r[0]["notes"]
    seul = _fusion([_lecture(partiel, 3)])                                          # sans lecture stable : gardée, à vérifier
    assert len(seul) == 1 and seul[0]["confidence"] == "a_verifier"


def test_chemin_v26_inchange_sur_en_une_image():
    texte = "RESULT\nBoss\nPhase1 00:04.734\nPhase2 00:15.212\nPhase3 00:29.224\n進行時間 00:29\nxx 00:29.224"
    l = _fusion(O.lectures_depuis_texte(texte, META, CFG, "video-complete", t=3))
    assert len(l) == 1 and l[0]["confidence"] == "sur" and not l[0]["detail"].get("v27") and l[0]["stage"] == "Boss"


def test_passage_complet_bot_ja_images_reelles(tmp_path):
    """Boucle de `pc.traiter_images` avec le vrai tesseract : la 2e capture lue à 2 instants -> `sur` ; la 1re (temps de jeu masqué) `a_verifier`."""
    if not _tesseract_ok():
        return
    import tempfile
    from test_pc import INSTANT, SEM, monde
    from test_tri34 import OutilsImages
    for nom, attendu, score in (("bot_results_sans_sjw_ja.png", "sur", 29.224), ("bot_results_ja.png", "a_verifier", 19.558)):
        with tempfile.TemporaryDirectory() as tmp:
            d = monde(tmp)
            videos = d.videos(SEM)
            videos["a"].update(mode_guess=["bot"], lang="ja", duration="PT1M")
            d.ecrire(f"runs/{SEM}/_videos.json", videos)
            copies = []
            for i in range(2):
                c = Path(tmp) / f"f{i}.png"
                shutil.copy(CAPT / nom, c)
                c.write_bytes(c.read_bytes() + bytes([i]))        # deux images distinctes (octets différents)
                copies.append(c)

            class Vrai(OutilsImages):
                def images(self, chemin, segments, dossier, prefixe="f", hauteur=None):
                    return [(0, str(copies[0])), (2, str(copies[1]))]

                def reduire(self, png, largeur):
                    cible = Path(png).with_name(Path(png).stem + "_p.png")
                    shutil.copy(png, cible)
                    return cible

                def dimensions(self, png):
                    return Tesseract().dimensions(png)

                def empreinte(self, png):
                    return Path(png).read_bytes().hex()[-64:] + str(Path(png).name)

                def ocr(self, png, langues=None, psm=6, timeout=120, extra=None):
                    return Tesseract().ocr(png, langues or "eng", psm, timeout, extra)

            pc.lancer("daily", INSTANT, d, CFG, Vrai({}), maximum=1)
            bots = [l for l in d.lectures(SEM) if l["video_id"] == "a" and l["mode"] == "bot" and l["score_source"] != "titre"]
            assert len(bots) == 1 and bots[0]["confidence"] == attendu and bots[0]["score"] == score, (nom, bots)
            assert len(bots[0]["detail"]["par_t"]) == 2 and bots[0]["stage"] is None


if __name__ == "__main__":
    import tempfile
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            with tempfile.TemporaryDirectory() as t:
                f(t) if f.__code__.co_argcount else f()
    print("OK")
