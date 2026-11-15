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


def test_ocr_reel_stats_par_position_et_accord_fiche():
    """Textes réels (essai PC v0tuXJNxudk, 15/11) : libellés perdus -> stats par position ; écran sans nom -> SJW par accord avec la fiche."""
    lire = lambda n: (Path(__file__).parent / "ocr_reel" / f"{n}.txt").read_text(encoding="utf-8")
    r = E.lire_stats(lire("16_stats"), T.DB, T.CFG)
    assert r["stats"]["attack"] == 85562 and r["stats"]["mana"] == 5423 and r["stats"]["defense"] == {"percent": 85.22, "rating": 144098}
    assert r["stats"]["crit-rate"] == {"percent": 50.0, "rating": 4507} and r["stats"]["defense-penetration"]["percent"] == 41.74 and len(r["stats"]) == 9
    obs = {}
    E.integrer(obs, [("fiche_sjw", lire("0_fiche_sjw")), ("stats", lire("4_stats")), ("stats", lire("16_stats"))], T.DB, T.CFG)
    s = obs["sjw"]["stats"]
    assert s["hp"] == 108376 and s["attack"] == 138984 and s["defense"]["rating"] == 70380 and "accuracy" not in s   # accuracy : ligne illisible, jamais devinée
    assert s["defense-penetration"]["percent"] == 43.02 and not obs.get("unmatched")
    assert obs["hunters"][0]["id"] == "christopher-reed" and obs["hunters"][0]["stats"]["hp"] == 81263
    seul = {}
    E.integrer(seul, [("stats", lire("4_stats"))], T.DB, T.CFG)         # sans fiche : aucun accord possible, écran non rattaché
    assert "sjw" not in seul and seul["unmatched"][0]["stats"]["hp"] == 108376


def test_zones_fiche_et_statues_avec_faux_ocr():
    """Lecture par zone (faux recadrage/OCR) : attributs de la fiche, grades + statue sélectionnée (la plus lumineuse) + options."""
    import tempfile
    from PIL import Image, ImageDraw
    import composition as C
    zs = T.CFG["ecrans"]["statues"]["zones"]
    za = T.CFG["ecrans"]["fiche_sjw"]["zones_attributs"]
    with tempfile.TemporaryDirectory() as d:
        im = Image.new("RGB", (1600, 900), (30, 30, 50))
        x, y, l, h = zs["selection"][4]                              # statue 5 sélectionnée : losange clair
        ImageDraw.Draw(im).rectangle([x * 1600, y * 900, (x + l) * 1600, (y + h) * 900], fill=(200, 200, 220))
        png = Path(d) / "f.png"
        im.save(png)

        class Faux:
            def __init__(self):
                self.zone = None
            def recadrer(self, p, zone, echelle=3, seuil=None):
                self.zone = [round(v, 4) for v in zone]
                return p
            def ocr(self, p, langues=None, psm=6, timeout=0, extra=None):
                arr = lambda zones: [[round(v, 4) for v in z] for z in zones]
                if self.zone in arr(za.values()):
                    return ["19", "10", "10", "1,335", "10"][arr(za.values()).index(self.zone)]
                if self.zone in arr(zs["grades"]):
                    return "DECBB"[arr(zs["grades"]).index(self.zone)]
                return "攻撃力/防御力(%) 20%" if self.zone == arr(zs["options"])[0] else ""
        o = Faux()
        fiche = C._lire_zones(o, T.CFG, "fiche_sjw", png, 8, lambda m: None)
        sta = C._lire_zones(o, T.CFG, "statues", png, 44, lambda m: None)
    obs = {}
    notes = E.integrer(obs, fiche + fiche + sta, T.DB, T.CFG)
    assert obs["sjw"]["stats"] == {"strength": 19, "vitality": 10, "agility": 10, "intelligence": 1335, "perception": 10}, obs["sjw"]
    assert [x["grade"] for x in obs["statues"]] == list("DECBB") and obs["statues"][4]["options"][0]["text_read"] == "攻撃力/防御力(%) 20%"
    assert all(not x["options"] for x in obs["statues"][:4]), "options rattachées à la seule statue sélectionnée"
    # sélection non détectée (image uniforme) : grades gardés, options non rattachées (jamais « statue 1 » par défaut)
    plat = {}
    E.fusionner_zones(plat, [], [{"t": 1, "grades": list("DECBB"), "selection": None, "options": ["x", "", ""]}], notes2 := [])
    assert all(not x["options"] for x in plat["statues"]) and any("non rattachées" in n for n in notes2)
    # deux lectures en désaccord : valeur non lue
    n3 = []
    obs3 = {}
    E.fusionner_zones(obs3, [{"strength": 19}, {"strength": 18, "vitality": 10}], [], n3)
    assert obs3["sjw"]["stats"] == {"vitality": 10} and any("désaccord" in n for n in n3)
    perdu = {}
    E.fusionner_zones(perdu, [{"strength": 9}, {"strength": 19}], [], n3 := [])       # essai PC 15/11 : « 1 » initial perdu -> la lecture la plus longue
    assert perdu["sjw"]["stats"] == {"strength": 19} and any("plus longue" in n for n in n3)


def test_images_classees_composition_apres_les_statues_sont_lues():
    """Essai PC 15/11 : le panneau d'options des statues (bouton jaune visible) est classé « composition » ; juste après une
    liste de statues, ces images-là sont aussi lues, pas les autres."""
    import composition
    txt = {"s1.png": "彫像 所持彫像", "c1.png": "彫像 所持彫像 彫像オプション", "c2.png": "彫像 所持彫像 彫像オプション", "c3.png": "彫像 所持彫像",
           "c4.png": "彫像 所持彫像", "c5.png": "彫像 所持彫像", "x.png": "rien"}

    class Faux:
        def reduire(self, png, largeur):
            return png

        def ocr(self, png, langues, psm, timeout):
            return txt[Path(png).name]
    cfg = {**T.CFG, "hors_compo": {"pas": 2, "ocr_max": 50, "suite_images": 2, "langues": "jpn+eng"}}
    toutes = [(t, Path(n)) for t, n in enumerate(["s1.png", "c1.png", "c2.png", "c3.png", "c4.png", "c5.png", "x.png"])]
    autres = [toutes[0], toutes[-1]]
    lus = composition._lire_hors_composition(Faux(), cfg, autres, lambda m: None, None, "V", toutes)
    assert len(lus) == 4, lus                          # s1 puis c1-c3 (images forcées tant que l'écran dure), plafond `lectures_max` = 4 : c4, c5 ignorées


def test_ocr_reel_statues_par_zone_une_statue_selectionnee_a_la_fois():
    """Essai PC 15/11 : t=40 sans sélection ni panneau, t=42 panneau complet (statue 3), t=44 statue 5 mais panneau en fondu (vide)."""
    lire = lambda t: (Path(__file__).parent / "ocr_reel" / f"statues_zone_{t}.txt").read_text(encoding="utf-8")
    obs = {}
    E.integrer(obs, [("statues_zone", lire(t)) for t in (40, 42, 44)], T.DB, T.CFG)
    st = obs["statues"]
    assert [x["grade"] for x in st] == list("DECBB")
    assert [len(x["options"]) for x in st] == [0, 0, 3, 0, 0], "options rattachées à la statue 3 (celle du panneau complet) seulement"
    o = st[2]["options"]
    assert (o[0]["label"], o[0]["value"]) == ("攻撃力/防御力(%)", "60%") and (o[1]["label"], o[1]["value"]) == ("追加攻撃力/防御力", "8,000")
    assert (o[2]["label"], o[2]["value"]) == ("追加魔力", "190")


# Texte SYNTHÉTIQUE (aucune capture lue : les mots JA 過負荷 / 付与 / 武器 / 通常攻撃 sont des hypothèses [À CONFIRMER]) : 9 cartes, ordre colonne par colonne.
SUBJ_TXT = """討伐支援
討伐熟練度
攻撃力/防御力/最大HP +20%
過負荷ダメージ +10%
クリティカルダメージ +20%
ストッカー/サポーター/バスターがチームにいる場合
属性付与効果 +200%
ストッカー/サポーター/バスターがチームにいる場合
属性ダメージ +100%
ストッカー/サポーター/バスターがチームにいる場合
過負荷ダメージ +100%
継承者 攻撃力/防御力/最大HP +200%
スキル 属性付与 +500%
通常攻撃/コア攻撃/武器スキル +500%
1/1  1/1  1/1"""


def _db_reelle():
    import builds
    return builds.charger_db(), builds.charger_config()


def test_subjugation_premiere_ligne_de_chaque_colonne():
    db, cfg = _db_reelle()
    assert E.detecter("討伐支援\n討伐熟練度", cfg) == "subjugation"
    r = E.lire_subjugation(SUBJ_TXT, db, cfg)
    assert r["ids"] == ["poc-cap-c1-atk-def-hp", "poc-cap-c2-infusion", "poc-cap-c3-successor-stats"], r
    assert len(r["cartes"]) == 9 and not r["ambigues"]
    obs = {}
    E.integrer(obs, [("subjugation", SUBJ_TXT)], db, cfg)
    assert obs["subjugation_support"] == r["ids"]


def test_subjugation_carte_illisible_ou_ambigue_jamais_devinee():
    db, cfg = _db_reelle()
    texte = "討伐支援\n???? +20%\n過負荷ダメージ +10%\n継承者 +200% 継承者 属性付与 +200%"
    r = E.lire_subjugation(texte, db, cfg)
    assert r["ids"][0] == "poc-cap-c1-overload-dmg"        # la 1re carte lue de la colonne 1 (celle d'avant est illisible : non devinée)
    assert r["ids"][1] is None
    assert E.lire_subjugation("", db, cfg)["ids"] == [None, None, None]
    # 10 % n'est pas 100 % : la carte « +100% » ne vaut pas la carte « +10% »
    r = E.lire_subjugation("過負荷ダメージ +100%", db, cfg)
    assert r["ids"] == [None, "poc-cap-c2-overload-dmg", None]


def test_sonde_popup_sur_image_classee_composition():
    """Le popup garde le bouton jaune visible : l'image est « composition » mais doit être lue (1 sur `compo_pas`)."""
    import composition
    textes = {"c0.png": "rien", "c1.png": SUBJ_TXT, "c2.png": SUBJ_TXT, "c3.png": SUBJ_TXT}

    class Faux:
        def reduire(self, png, largeur):
            return png

        def ocr(self, png, langues, psm, timeout):
            return textes[Path(png).name]
    db, cfg = _db_reelle()
    cfg = {**cfg, "hors_compo": {"pas": 1, "ocr_max": 10, "langues": "jpn+eng", "compo_pas": 1, "compo_ocr_max": 10}}
    toutes = [(i * 2, Path(n)) for i, n in enumerate(textes)]
    lus = composition._lire_hors_composition(Faux(), cfg, [], lambda m: None, None, "VID", toutes)
    assert [e for e, _ in lus] == ["subjugation", "subjugation"]       # `lectures_max` = 2
    sans = composition._lire_hors_composition(Faux(), {**cfg, "hors_compo": {**cfg["hors_compo"], "compo_pas": 0}}, [], lambda m: None, None, "VID", toutes)
    assert sans == []


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
