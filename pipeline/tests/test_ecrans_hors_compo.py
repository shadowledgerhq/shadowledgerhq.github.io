"""Écrans hors composition (SPEC v3 §1.4, tests 14-15) sur les textes lus des captures POC JA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecrans_hors_compo as E
import test_etape2 as T

STATS_TXT = """ハンター
能力値情報
全体
武器
アーティファクト
HP 81263
魔力 5423
攻撃力 85562
精密度 88.32% (28905) ?
防御力 85.22% (144098)
クリティカル率 50% (4607) ?
クリティカルダメージ 207.07% (18296) ?
クールタイム短縮 0% (0)
防御力貫通 47.74% (45680)
ダメージ増加 39.31% (32382) ?
クリストファー・リード
ハンター管理局"""
FICHE_TXT = """水篠旬
筋力
19
活力 10
速度
10
知能
1,335
感覚 10
SKILL 01
SKILL 02
ULTIMATE
SKILL
QTE 01
QTE 02
QTE 03"""
GEMMES_TXT = """宝石情報
All
装着中の宝石
16
16
16
16
16
能力値情報
攻撃力(%) 80%
HP(%) 80%
防御力(%) 80%
防御力貫通 15,440
追加魔力 1,920"""
STATUES_TXT = """彫像
所持彫像 5/5
D
E
C
B
B
ナイトの像
彫像オプション (ハンター専用)
A
追加攻撃力/防御力
5,350
D
ダメージ増加
1,000
S
追加攻撃力/防御力
8,000"""


def test_14_detection_et_stats():
    assert E.detecter(STATS_TXT, T.CFG) == "stats" and E.detecter(FICHE_TXT, T.CFG) == "fiche_sjw"
    assert E.detecter(GEMMES_TXT, T.CFG) == "gemmes" and E.detecter(STATUES_TXT, T.CFG) == "statues"
    assert E.detecter("n'importe quoi", T.CFG) is None
    r = E.lire_stats(STATS_TXT, T.DB, T.CFG)
    s = r["stats"]
    assert len(s) == 10, s
    assert s["accuracy"] == {"percent": 88.32, "rating": 28905}
    assert s["cooldown-reduction"] == {"percent": 0.0, "rating": 0}
    assert s["defense"] == {"percent": 85.22, "rating": 144098} and s["defense-penetration"]["rating"] == 45680
    assert s["hp"] == 81263 and s["attack"] == 85562 and s["crit-rate"]["percent"] == 50.0
    assert "クリストファー・リード" in r["candidats"]


def test_14_stats_rattachees_par_le_nom_ou_unmatched():
    sans_ja = {**T.DB, "hunters": {k: {**v, "name": {l: n for l, n in v["name"].items() if l != "ja"}} for k, v in T.DB["hunters"].items()}}
    obs = {"hunters": [], "notes": []}
    E.integrer(obs, [("stats", STATS_TXT)], sans_ja, T.CFG)    # sans name.ja : unmatched, stats gardées
    assert obs["unmatched"][0]["text_read"] == "クリストファー・リード" and obs["unmatched"][0]["stats"]["hp"] == 81263
    obs = {"hunters": [], "notes": []}
    E.integrer(obs, [("stats", STATS_TXT)], T.DB, T.CFG)       # base réelle : name.ja présent -> chasseur trouvé
    assert obs["hunters"][0]["id"] == "christopher-reed" and obs["hunters"][0]["position"] is None
    assert "chasseur trouvé par l'écran de stats" in obs["notes"]


def test_chasseur_trouve_par_stats_prend_un_emplacement_libre():
    o = T.obs_hunters(n=2)
    o["hunters"].append({"position": None, "id": T.HUNTERS[2], "weapon": {}, "artifacts": [], "cores": [], "stats": {"hp": 5}})
    b = T.build(T.ctx("bot"), o, T.REGLES_TOUT)
    h3 = b["hunters"][2]
    assert h3["id"] == T.HUNTERS[2] and h3["position_inconnue"] and h3["stats"] == {"hp": 5}


def test_15_fiche_sjw_attributs():
    a = E.lire_attributs(FICHE_TXT, T.CFG)
    assert a == {"strength": 19, "vitality": 10, "agility": 10, "intelligence": 1335, "perception": 10}


def test_gemmes_et_statues():
    g = E.lire_gemmes(GEMMES_TXT, T.CFG)
    assert [c["level"] for c in g["colors"]] == [16] * 5
    assert {"stat": "attack", "unit": "percent", "value": 80.0} in g["bonuses"]
    assert {"stat": "defense-penetration", "unit": "flat", "value": 15440} in g["bonuses"]
    assert {"stat": "mana", "unit": "flat", "value": 1920} in g["bonuses"] and len(g["bonuses"]) == 5
    s = E.lire_statues(STATUES_TXT, T.CFG)
    assert [x["grade"] for x in s] == list("DECBB")
    assert [o["grade"] for o in s[0]["options"]] == list("ADS") and s[0]["options"][1]["text_read"] == "ダメージ増加"
    assert all(not x["options"] for x in s[1:])


def test_integration_complete_dans_un_build():
    obs = T.obs_hunters()
    E.integrer(obs, [("gemmes", GEMMES_TXT), ("statues", STATUES_TXT), ("fiche_sjw", FICHE_TXT)], T.DB, T.CFG)
    b = T.build(T.ctx("bot"), obs, T.REGLES_TOUT)
    assert b["found"]["gems"] and b["found"]["statues"]


def test_lecture_hors_composition_avec_faux_ocr():
    import composition
    textes = {"a.png": STATS_TXT, "b.png": "rien", "c.png": GEMMES_TXT, "d.png": STATS_TXT, "e.png": STATS_TXT}

    class Faux:
        def reduire(self, png, largeur):
            return png

        def ocr(self, png, langues, psm, timeout):
            return textes[Path(png).name]
    cfg = {**T.CFG, "hors_compo": {"pas": 1, "ocr_max": 10, "langues": "jpn+eng"}}
    autres = [(i * 2, Path(n)) for i, n in enumerate(textes)]
    lus = composition._lire_hors_composition(Faux(), cfg, autres, lambda m: None, None, "VID")
    assert [e for e, _ in lus] == ["stats", "gemmes", "stats"]          # 2 lectures au plus par type, « rien » ignoré
    obs = T.obs_hunters()
    import ecrans_hors_compo as E2
    E2.integrer(obs, lus, T.DB, T.CFG)
    assert obs["gems"]["colors"] and obs["hunters"][-1]["id"] == "christopher-reed"


def test_ocr_reel_ka_katakana_et_valeurs_refusees():
    """Essai PC 15/11 : `攻撃カ` (katakana) doit être reconnu ; `Lv.170/170` n'est jamais un attribut."""
    r = E.lire_stats("HP 81263\n攻撃カ 85562\n防御カ 85.22% (144098)\nクリティカルダメージ 207.07% (18296)", T.DB, T.CFG)
    assert r["stats"]["attack"] == 85562 and r["stats"]["defense"]["rating"] == 144098 and r["stats"]["crit-damage"]["percent"] == 207.07
    a = E.lire_attributs("筋カ\n19\n活力\n速度\nLv.170/170\n526828\n知能\n1,335\n感覚", T.CFG)
    assert a == {"strength": 19, "intelligence": 1335}, a          # vitality/agility/perception : non lus, jamais devinés


def test_t_debut_vidéo_à_deux_runs():
    """Vidéo à 2 runs : la run 2 repart du résultat de la run 1 (ses écrans ne sont pas ceux de la run 1) ; autre vidéo ou t absent : 0."""
    import builds as B
    ligne = {"run_id": "r", "mode": "poc", "video_id": "V", "runs_detail": [{"t": 120}, {"t": 300}, {"video_id": "W", "t": 50}, {}]}
    assert [c["t_debut"] for c in B.contextes("poc", ligne, "2026-11-12")] == [0, 120, 0, 0]
    assert [c["t_debut"] for c in B.contextes("poc", {"run_id": "r", "video_id": "V"}, "s")] == [0]


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
