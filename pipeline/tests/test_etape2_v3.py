"""Tests SPEC_ETAPE2 v3 : noms écrits, statues, gemmes, stats du successeur (sans OCR ni image)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import noms
import test_etape2 as T

STATUES = [{"position": i + 1, "grade": g, "options": [{"text_read": "攻撃力 +5%", "lang": "ja", "grade": "S", "id": None}] * 3}
           for i, g in enumerate("DECBB")]
GEMS = {"colors": [{"position": i + 1, "color": None, "level": 10} for i in range(5)],
        "bonuses": [{"stat": "attack", "unit": "percent", "value": 12.0}, {"stat": "hp", "unit": "percent", "value": 8.5}]}


def test_normaliser_et_apparier():
    objets = {"x": {"name": {"ja": "クリストファー・リード", "en": "Christopher Reed", "ko": "", "fr": ""}},
              "y": {"name": {"ja": "ハン・ソンイ", "en": "Han Song-yi"}}}
    assert noms.normaliser("クリストファー・ リード") == noms.normaliser("クリストファーリード")
    r = noms.apparier("クリストファー・リード", objets)
    assert r["id"] == "x" and r["methode"] == "exact"
    r = noms.apparier("クリストファー・リ一ド", objets)            # un caractère mal lu
    assert r["id"] == "x" and r["methode"] == "approche"
    assert noms.apparier("まったく違う", objets)["id"] is None
    assert noms.apparier("", objets)["id"] is None
    assert noms.apparier("christopher reed", objets)["id"] == "x"
    deux = {"a": {"name": {"en": "Same"}}, "b": {"name": {"fr": "same"}}}
    assert noms.apparier("Same", deux)["id"] is None            # ambigu : jamais deviné


def test_croiser_desaccord():
    assert noms.croiser("a", "b") == ("a", True)
    assert noms.croiser("a", "a") == ("a", False)
    assert noms.croiser(None, "b") == ("b", False)


def test_build_v3_statues_gemmes_stats_successeur():
    o = T.obs_hunters(statues=STATUES, gems=GEMS)
    o["successor"] = {"id": T.SUCC, "level": None, "stats": {"attack": 1000}}
    b = T.build(T.ctx("bot"), o, T.REGLES_TOUT)
    assert b["spec"] == 3 and len(b["statues"]) == 5 and len(b["gems"]["colors"]) == 5
    assert b["successor"]["stats"] == {"attack": 1000}
    assert b["found"]["statues"] and b["found"]["gems"] and b["found"]["successor_stats"]


def test_v16_sans_statues_ni_gemmes_statut_inchange():
    b = T.build(T.ctx("bot"), T.obs_hunters(), T.REGLES_TOUT)
    assert b["statues"] is None and b["gems"] is None
    assert b["found"]["statues"] is None and b["found"]["gems"] is None


def test_statues_gemmes_ne_changent_pas_le_statut():
    sans = T.build(T.ctx("hotm", True), T.obs_hunters(), {"sjw": False, "shadows": True, "successor": True})
    avec = T.build(T.ctx("hotm", True), T.obs_hunters(statues=STATUES, gems=GEMS), {"sjw": False, "shadows": True, "successor": True})
    assert sans["status"] == avec["status"] == "build_complet"


def test_slides_statues_gemmes():
    from pptx import Presentation
    o = T.obs_hunters(statues=STATUES, gems=GEMS)
    b = T.build(T.ctx("hotm", True), o, {"sjw": False, "shadows": True, "successor": True})
    sans = T.build(T.ctx("hotm", True), T.obs_hunters(), {"sjw": False, "shadows": True, "successor": True})
    with tempfile.TemporaryDirectory() as t:
        n = {}
        for nom, bb in (("avec", b), ("sans", sans)):
            for lang in ("fr", "en"):
                f = Path(t) / f"{nom}-{lang}.pptx"
                T.P.generer_fichier([bb], T.row_pour(bb), lang, f)
                n[nom, lang] = len(Presentation(str(f)).slides)
        assert n["avec", "fr"] == n["sans", "fr"] + 2 == n["avec", "en"]
        assert n["sans", "fr"] == 7                                   # test 1 de la spec : 6 + Sources


def test_portraits_chasseurs_jamais_devines_sur_la_capture_bot():
    """Les portraits de la banque n'ont pas le style des cartes : sur la capture BOT, aucun chasseur ne doit être « reconnu »."""
    import icones
    from PIL import Image
    im = Image.open(T.RACINE / "docs" / "essais" / "composition" / "bot_personnages_ja.png").convert("RGB")
    banque = icones.Banque(T.RACINE)
    for o in ("hunter_1", "hunter_2", "hunter_3"):
        zone = icones.recadrer(im, T.CFG["zones"]["bot"]["personnages"][o]["hunter_face"])
        r = icones.reconnaitre(zone, "hunters", banque, seuil=T.CFG["seuil_icone"]["hunters"])
        assert r["id"] is None, (o, r)


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
