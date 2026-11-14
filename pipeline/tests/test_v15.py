"""SPEC §3.1 et §4.1 (v15) : compteurs animés, Personal Record prioritaire, zones du salon, libellés par langue, 1080p."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gb
import ocr_ecrans
import ecrans
import pc
from classement import calculer
from test_classement import HORLOGE, W, lire, preparer
from test_gb import meta as meta_gb
from test_tri34 import (CONFIG, HUD_228, OutilsImages, RESULTS_253_REEL, SALON_RECORD, VIDE, Z_253, _m, _res, _un_ecran, monde, INSTANT, SEM)


def img(t, rc, final="1,601,097,999"):
    return _res(RESULTS_253_REEL, t, {**Z_253, "rage": str(rc), "final": final})


def test_compteur_anime():
    res = _un_ecran([img(229, 1), img(231, 183), img(233, 189), img(234, 189)])                # 1 -> 183 -> 189, 189 sur 2 images à la fin
    assert res["score"] == 189 and res["confidence"] == "sur" and "compteur animé" in res["notes"]
    assert not any(n.startswith(("RC discordant", "conflit")) for n in res["notes"]) and res["detail"]["rc_images"] == 2
    # une valeur plus petite lue APRÈS la valeur finale reste discordante : vote habituel (2 contre 1)
    apres = _un_ecran([img(229, 189), img(231, 189), img(233, 183)])
    assert apres["score"] == 189 and "compteur animé" not in apres["notes"] and "RC discordant écarté : 183 (t=233)" in apres["notes"]
    # ordre décroissant (189 puis 183 puis 1 : cas awb-GlVIa7Q) : pas une animation, conflit
    decr = _un_ecran([img(227, 189), img(230, 183), img(242, 1)])
    assert decr["confidence"] == "a_verifier" and "conflit de lecture : rage_count" in decr["notes"] and "compteur animé" not in decr["notes"]
    # dernière valeur lue une seule fois : pas encore une valeur finale confirmée
    une = _un_ecran([img(229, 1), img(231, 183), img(233, 189)])
    assert une["confidence"] == "a_verifier" and "compteur animé" not in une["notes"]
    # idempotent
    again = _un_ecran([res, img(235, 189)])
    assert again["score"] == 189 and again["detail"]["rc_images"] == 3 and again["notes"].count("compteur animé") == 1


def test_nombre_de_zone_incomplet_rejete():
    n = ocr_ecrans._nombre_zone
    assert n("64,299,126,429,862") == 64299126429862 and n("7.884.144.289.064") == 7884144289064 and n("795,244,088,074 ,") == 795244088074
    assert n("64,299,126,42") is None and n("1,54") is None and n("12345678") is None and n("") is None and n("98,388,39,559,253") is None


# --- Personal Record prioritaire ------------------------------------------------------------------------

def _record(rc=189, total=64299126429862):
    ecran = {"groups": {1: {"rage_count": rc, "damage": "64.29T"}, 2: {"no_history": True}}, "total_rage_count": rc,
             "total_score": total, "challenge_count": 1, "time_left": "6d 22h", "t": 241}
    return ecrans.lectures_gb_record(meta_gb("awb"), ecran, CONFIG)[0]


def _en_run(l, **kw):
    return {**l, "channel_id": "UCawb", "video_id": "awb", "published_at": "2026-11-12T01:07:38Z", **kw}


def test_record_prioritaire_sur_un_results_en_conflit():
    rec = _record()
    res = _en_run(_res(RESULTS_253_REEL, 227, {**Z_253, "rage": "183", "final": "64,299,126,425,862"}), confidence="a_verifier", exact=False,
                  notes=["conflit de lecture : rage_count"])
    d = preparer([_en_run(rec), res])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert (l["score"]["total"], l["rank"], l["confidence"]) == (189, 1, "sur")                  # plus de 189 + 183 additionnés
    assert any("Personal Record fait foi" in n for n in l["notes"].split("; ")) and "une seule run" in l["notes"]
    # Results SÛR de même RC que l'unique groupe joué : même run ; dégâts différents -> le record l'emporte
    sur = _en_run(_res(RESULTS_253_REEL, 227, {**Z_253, "rage": "189", "final": "64,299,126,425,862"}), confidence="sur", exact=True)
    d = preparer([_en_run(rec), sur])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["score"]["total"] == 189 and l["runs_detail"][0]["damage"] == 64299126429862 and "écart Results/record : 64299126425862" in l["notes"]
    # record NON contrôlé : aucune priorité (règles habituelles)
    non = _en_run({**rec, "confidence": "a_verifier", "exact": False})
    assert len(gb.record_prioritaire([non, res])) == 2
    # un Results d'une autre vidéo n'est pas concerné
    autre = {**res, "video_id": "autre"}
    assert len(gb.record_prioritaire([_en_run(rec), autre])) == 2


# --- Personal Record du salon : zones ciblées -----------------------------------------------------------

def test_consensus_des_variantes_et_recoupement_du_total_score():
    c = ocr_ecrans.consensus_zone
    assert c("final", ["64,299,126,429,862", "64,299,126,425", "64,299,126,429,862"]) == "64,299,126,429,862"      # vote entre variantes
    assert c("final", ["92,842,054.460.9109", "32,842,054,460,310", ""]) == "32,842,054,460,310"                  # lecture invalide écartée
    assert c("rage", ["183", "189", "189"]) == "189" and c("rage", ["", "", ""]) == "" and c("boss", ["Gaint Statue", "xx"], CONFIG) == "Gaint Statue"
    # Total Score recoupé avec la somme des dégâts des groupes : 92,8 T contre 17,28 T + 15,55 T = 32,83 T -> écarté
    m = meta_gb("nh")
    ecran = {"groups": {1: {"rage_count": 167, "damage": "17.28T"}, 2: {"rage_count": 165, "damage": "15.55T"}}, "total_rage_count": 332,
             "total_score": 92842054460310, "t": 2}
    rs = ecrans.lectures_gb_record(m, ecran, CONFIG)
    assert [r["detail"]["total_score"] for r in rs] == [None, None] and all(any("incohérent" in n for n in r["notes"]) for r in rs)
    assert all(r["confidence"] == "sur" and any("incohérent" in n for n in r["notes"]) for r in rs)   # les RC restent contrôlés (167 + 165 = 332)
    ok = ecrans.lectures_gb_record(m, {**ecran, "total_score": 32842054460310}, CONFIG)
    assert [r["detail"]["total_score"] for r in ok] == [32842054460310] * 2 and all(r["confidence"] == "sur" for r in ok)


def test_zones_du_salon_record():
    m = meta_gb("nh")
    zones = {**VIDE, "g1_rc": "167", "g1_dmg": "17.28T", "g2_rc": "165", "g2_dmg": "15.55T", "total_rage": "332",
             "total_score": "32,842,054,460,310", "challenge": "2", "time_left": "6d 9h"}
    rs = ocr_ecrans.lectures_depuis_texte(SALON_RECORD, m, CONFIG, "debut-fin", 2, zones)
    assert [(r["team"], r["score"], r["confidence"]) for r in rs] == [(1, 167, "sur"), (2, 165, "sur")]     # 167 + 165 = 332
    assert rs[0]["detail"]["time_left"] == "6d 9h" and rs[0]["detail"]["total_score"] == 32842054460310
    # awb : groupe 2 « No history », un seul groupe joué -> Total Score = Final Score
    awb = {**VIDE, "g1_rc": "189", "g1_dmg": "64.29T", "g2_rc": "", "g2_dmg": "No history", "total_rage": "189",
           "total_score": "64,299,126,429,862", "challenge": "1", "time_left": "6d 22h"}
    (r,) = ocr_ecrans.lectures_depuis_texte(SALON_RECORD, m, CONFIG, "debut-fin", 241, awb)
    assert (r["team"], r["score"], r["confidence"], r["damage"]) == (1, 189, "sur", 64299126429862) and r["detail"]["damage_source"] == "record"
    # image entière lisible + zone qui la contredit : la zone prime, écart noté ; format non 16:9 : zones ignorées
    texte = "Personal Record\nTotal Rage Count 189\nGroup 1 189 64.29T\nGroup 2 No history\nTotal Score\n64,299,126,429,862\n"
    (z,) = ocr_ecrans.lectures_depuis_texte(texte, m, CONFIG, "debut-fin", 241, {**awb, "g1_rc": "188"})
    assert z["score"] == 188 and "écart OCR zone/image : g1_rc" in z["notes"] and z["confidence"] == "a_verifier"   # 188 ≠ Total Rage Count 189
    (f,) = ocr_ecrans.lectures_depuis_texte(texte, m, CONFIG, "debut-fin", 241, {"format_ok": False})
    assert f["score"] == 189 and f["notes"].count("format non standard") == 1
    # zone du Total Rage Count illisible : le total de l'image entière sert, le contrôle reste possible
    (g,) = ocr_ecrans.lectures_depuis_texte(texte, m, CONFIG, "debut-fin", 241, {**awb, "total_rage": ""})
    assert g["confidence"] == "sur"
    assert set(CONFIG["gb"]["zones_record"]) == {"time_left", "total_score", "total_rage", "challenge", "g1_rc", "g1_dmg", "g2_rc", "g2_dmg"}
    assert all(0 <= v <= 1 for z in CONFIG["gb"]["zones_record"].values() for v in z)


# --- libellés par langue --------------------------------------------------------------------------------

HUD_PT = """ao ae _ ee (®) 0.80 TT]
Pontos 7.884.144.289.064 * 9 Ser
Número de Fúrias do Chefão 120 @  WARNING |! r
O monstro chefão se recusa a morrer e torna-se enfurecido!
Equipe A  Equipe B
"""


def test_hud_portugais_et_langues():
    assert ocr_ecrans.detecter(HUD_PT) == "gb_combat" and ocr_ecrans.langue_hud(HUD_PT) == "pt" and ocr_ecrans.langue_hud(HUD_228) == "en"
    h = ocr_ecrans.lire_gb_combat(HUD_PT)
    assert (h["points"], h["rage_count"], h["chrono"], h["langue"]) == (7884144289064, 120, 0.8, "pt")
    (l,) = ocr_ecrans.lectures_depuis_texte(HUD_PT, {**meta_gb("t5d"), "mode_guess": ["gb"]}, CONFIG, "debut-fin", 213)
    assert l["score"] is None and l["detail"]["hud_rage_count"] == 120 and l["detail"]["hud_points"] == 7884144289064
    assert ocr_ecrans.detecter("Pontos 5\n0.80") is None and ocr_ecrans.detecter("Equipe A 0.80") is None          # un libellé ne suffit pas
    assert "pt" in CONFIG["gb"]["libelles"] and "en" in CONFIG["gb"]["libelles"]


HUD_KO = """POINT 10.375.798.059.160 3.18
보스 격노 횟수 x125 WARNING
A팀 편성 정보 보기
"""


def test_hud_coreen_et_publication_apres_le_dernier_hud():
    assert ocr_ecrans.detecter(HUD_KO) == "gb_combat" and ocr_ecrans.langue_hud(HUD_KO) == "ko"
    h = ocr_ecrans.lire_gb_combat(HUD_KO)
    assert (h["points"], h["rage_count"], h["chrono"], h["langue"]) == (10375798059160, 125, 3.18, "ko")
    assert ocr_ecrans.boss_connu("거대 석상", CONFIG) == "거대 석상" and ocr_ecrans.boss_connu("Temple Altar", CONFIG) is None
    assert ocr_ecrans.detecter("POINT 5\n3.18") is None
    # publication : les images qui suivent le dernier HUD (écran Results, langue inconnue) sont choisies
    import subprocess
    import tempfile

    def faux(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"jpg")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "logs", Path(tmp) / "docs"
        src.mkdir()
        for nom in ["tri3_0", "tri3_213_gb_combat", "tri3_215", "tri3_219", "tri3_223", "tri3_229", "tri3_241", "tri3_4"]:
            (src / f"V_{nom}.txt").write_text("x" * (3 + len(nom)), encoding="utf-8")
            (src / f"V_{nom}.png").write_bytes(b"png")
        noms = pc.publier_essai(pc.Outils(CONFIG["pc"], executer=faux), src, dst, None, maximum=5)
        pris = {n for n in noms if n.endswith(".txt")}
        assert "V_tri3_213_gb_combat.txt" in pris and {"V_tri3_215.txt", "V_tri3_241.txt"} <= pris        # début et fin de la zone après le HUD


HUD_KO_REEL = """oor Ma Shoe ; a Mase (y) 3.1 i
poInt 10.375,798,058,160, ~ SE & a ue
BA Ab x125 We RNING if 7
"""


def test_hud_coreen_chrono_lu_par_zone_et_points_abimes():
    assert ocr_ecrans.detecter(HUD_KO_REEL) == "gb_combat_incertain"            # « POINT » + « WARNING » lus, chrono « 3.1 » incomplet
    m = {**meta_gb("mj"), "mode_guess": ["gb"]}
    assert ocr_ecrans.lectures_depuis_texte(HUD_KO_REEL, m, CONFIG, "video-complete", 200) == []
    zones = {**VIDE, "hud_chrono": "3.18", "hud_points": "10,375,798,059,160", "hud_rage": "125"}
    (l,) = ocr_ecrans.lectures_depuis_texte(HUD_KO_REEL, m, CONFIG, "video-complete", 200, zones)
    assert l["detail"]["chrono_hud"] == 3.18 and l["detail"]["hud_rage_count"] == 125 and l["detail"]["hud_points"] == 10375798058160
    # sans compteur de rage lu mais avec Points et chrono : HUD gardé (compteur = information)
    zs = {**VIDE, "hud_chrono": "3.18", "hud_points": "", "hud_rage": ""}
    (l2,) = ocr_ecrans.lectures_depuis_texte(HUD_KO_REEL, m, CONFIG, "video-complete", 200, zs)
    assert l2["detail"]["hud_rage_count"] is None and l2["detail"]["chrono_hud"] == 3.18
    # Points abîmés (7288064 pour 7 884 144 289 064) : jamais des dégâts provisoires
    brut = ocr_ecrans.lectures_depuis_texte(HUD_PT, m, CONFIG, "video-complete", 213)
    fin = ocr_ecrans.regrouper_hud([{**b, "detail": {**b["detail"], "hud_points": 7288064, "chrono_hud": 0.8}} for b in brut], CONFIG)
    assert fin[0]["damage"] is None


RESULTS_PT = """n = 5 Ul l ta efe © Tempo de Progresso 03:00
E a Gigante : "
Pontuacao do Jogador
Rank do Cacador i
| Novo Recorde Quebrado!
Pontuacao Final NumerodeFurias Jy () GS J
7.907,273,299,084 156 Y
Tentar de Novo Sair
"""
RESULTS_KO = """플레이어 스코어 ws
| wy 5,576,463,862,754 격노 보상 © a
계승자 스코어 도
화면을 눌러 계속
WH 56450 0 10661037770748 160
"""
Z_PT = {**VIDE, "_layout": "standard", "boss": "Estatua Gigante", "joueur": "4,254,332,623,094", "rang_1": "2,719,877,951,535", "rang_2": "473,844,449,049",
        "rang_3": "199,639,030,058", "rang_4": "131,808,903,549", "rang_5": "90,867,324,225", "rang_6": "36,903,017,574",
        "final": "7,907,273,299,084", "rage": "156", "temps": "03:00"}
Z_KO = {**VIDE, "_layout": "successeur", "boss": "거대 석상", "joueur": "5,576,463,862,754", "successeur": "0", "rang_1": "3,686,927,733,236",
        "rang_2": "873,686,133,825", "rang_3": "302,730,549,509", "rang_4": "125,782,887,452", "rang_5": "52,090,149,391",
        "rang_6": "43,356,454,581", "final": "10,661,037,770,748", "rage": "160", "temps": "03:00"}


def test_results_portugais_et_coreen_captures_reelles():
    assert ocr_ecrans.detecter(RESULTS_PT) == "gb_results_partiel" and ocr_ecrans.langue_results(RESULTS_PT) == "pt"
    assert ocr_ecrans.detecter(RESULTS_KO) == "gb_results_partiel" and ocr_ecrans.langue_results(RESULTS_KO) == "ko"
    assert ocr_ecrans.mise_en_page_results(RESULTS_PT) == "standard" and ocr_ecrans.mise_en_page_results(RESULTS_KO) == "successeur"
    assert ocr_ecrans.detecter("Pontuacao do Jogador\n7.907.273.299.084") is None                       # un seul libellé ne suffit pas
    # POC coréen : mêmes libellés « 플레이어 스코어 / 계승자 스코어 » mais jamais un Results GB
    assert ocr_ecrans.detecter("이번 기록 플레이어 스코어 계승자 스코어") == "poc"
    for texte, zones, lang, rc, final in ((RESULTS_PT, Z_PT, "pt", 156, 7907273299084), (RESULTS_KO, Z_KO, "ko", 160, 10661037770748)):
        m = {**meta_gb("v"), "lang": lang, "mode_guess": ["gb"]}
        ls = [ocr_ecrans.lectures_depuis_texte(texte, m, CONFIG, "video-complete", t, zones)[0] for t in (231, 232)]
        (res,) = [l for l in pc.fusionner_ecrans([], "v", ls, CONFIG) if l["score"] is not None]
        assert (res["score"], res["damage"]) == (rc, final) and res["detail"]["hunter_ranks_lus"] == 6
        # Player's Score + [Successor Score] + 6 Hunter Rank = Final Score : vérifié (somme exacte lue sur les captures)
        assert res["exact"] is True and res["confidence"] == "sur" and not any("contrôle GB" in n for n in res["notes"]), (lang, res["notes"])
    # successeur illisible alors que la ligne existe : somme non vérifiable
    zs = {**Z_KO, "successeur": ""}
    (a,) = ocr_ecrans.lectures_depuis_texte(RESULTS_KO, {**meta_gb("v"), "mode_guess": ["gb"]}, CONFIG, "video-complete", 231, zs)
    assert a["confidence"] == "a_verifier" and any("Successor Score illisible" in n for n in a["notes"])
    # boss lu : « Estatua Gigante » et « 거대 석상 » (noms de la configuration)
    assert ocr_ecrans.boss_connu("Estatua Gigante\n", CONFIG) in ("Estátua Gigante", "Estátua de Pedra Gigante") and ocr_ecrans.boss_connu("거대 석상", CONFIG) == "거대 석상"


def test_langue_sans_libelles_connus():
    config = pc.charger_config()
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], lang="ko", duration="PT5M")
        d.ecrire(f"runs/{SEM}/_videos.json", videos)
        r = pc.lancer("daily", INSTANT, d, config, OutilsImages({}), maximum=1)
        assert any("libellés ko inconnus" in a for a in r["alertes"])
        p = d.processed()["a"]
        assert p["status"] == "en_cours" and p["pc"]["libelles_inconnus"] == "ko" and p["pc"]["tri4"] == "fait"      # reste en_cours


def test_resolution_1080p_tri3_et_720p_tri4():
    config = pc.charger_config()
    assert "height<=1080" in config["pc"]["images"]["format_video"] and config["pc"]["images"]["tri4_hauteur"] == 720
    with __import__("tempfile").TemporaryDirectory() as tmp:
        d = monde(tmp)
        videos = d.videos(SEM)
        videos["a"].update(mode_guess=["gb"], duration="PT5M")
        d.ecrire(f"runs/{SEM}/_videos.json", videos)
        hauteurs = []

        class O(OutilsImages):
            def images(self, chemin, segments, dossier, prefixe="f", hauteur=None):
                hauteurs.append((segments[0][2], hauteur))
                return super().images(chemin, segments, dossier, prefixe, hauteur)
        pc.lancer("daily", INSTANT, d, config, O({}), maximum=1)
        assert hauteurs[0] == (2, None) and hauteurs[1] == (10, 720)                 # tri 3 : résolution d'origine ; tri 4 : 720p


def test_results_coreen_libelles_espaces():
    """Vrai OCR coréen (vYtRCpFtSOk, 220 s) : libellés espacés (`진 행 시간`) -> Results partiel coréen."""
    import ocr_ecrans as o
    t = "5 © 진 행 시간 03:00\n플레이어 스코어\n계승자 스코어\n헌터 순위\nAIR 달성!\n12859,482,380,262 162\n다 시 하 기 나가기"
    assert o.detecter(t) == "gb_results_partiel"
    assert o.langue_results(t) == "ko"


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)

