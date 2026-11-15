"""Réglage des masques d'artefacts sur de vraies captures (essais du 15/11/2026, images 1600×900 de docs/essais/builds/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import builds as B
import icones

RACINE = B.RACINE
CFG = B.charger_config()


def _lire(image, mode, proprietaire):
    from PIL import Image
    img = Image.open(RACINE / "docs" / "essais" / "builds" / image).convert("RGB")
    banque = icones.Banque()
    pieces = banque.categorie("artifact_pieces")
    sortie = {}
    for slot, z in CFG["zones"][mode]["artefacts"][proprietaire]["artifacts"].items():
        r = icones.reconnaitre(icones.recadrer(img, z), "artifact_pieces", banque, CFG["seuil_icone"]["artifact_pieces"],
                               CFG["ecart_icone"], {k for k in pieces if k.endswith("--" + slot)},
                               tuple(CFG["echelles_icone"]["defaut"]), CFG["masques"]["artifact_pieces"])
        sortie[slot] = r["id"].split("--")[0] if r["id"] else None
    return sortie


def test_sjw_bot_poison_bleu_7_sur_8():
    lu = _lire("5MI-RLj7FSk_ocr/5MI-RLj7FSk_compo_artefacts_1.jpg", "bot", "sjw")
    assert sum(v == "set-of-the-architects-blue-poison" for v in lu.values()) >= 7, lu
    assert not [v for v in lu.values() if v not in (None, "set-of-the-architects-blue-poison")], lu   # jamais un autre set


def test_sjw_poc_burning_8_sur_8():
    lu = _lire("v0tuXJNxudk_ocr/v0tuXJNxudk_compo_artefacts_0.jpg", "poc", "sjw")
    assert all(v and v.startswith("set-of-burning") for v in lu.values()), lu


def test_benedictions_sjw_poc_8_sur_8():
    """Icône qui remplit la zone (échelles 0,8-1,0) et `+5` masqué ; vérité lue à l'œil sur la capture."""
    from PIL import Image
    img = Image.open(RACINE / "docs/essais/builds/v0tuXJNxudk_ocr/v0tuXJNxudk_compo_benedictions_0.jpg").convert("RGB")
    banque = icones.Banque()
    vrai = ["monarchs-domain", "life", "we-are-one", "aggressive-defense", "bloodlust", "kasakas-steel-scales",
            "reawakening", "r-sonance-darme"]
    ech = tuple(CFG["echelles_icone"]["blessings"])
    zones = CFG["zones"]["poc"]["benedictions"]["sjw"]["blessings"]
    lu = [icones.reconnaitre(icones.recadrer(img, z), "blessings", banque, 0.0, 0.0, None, ech,
                             CFG["masques"]["blessings"])["best_id"] for z in zones]
    assert lu == vrai, lu


if __name__ == "__main__":
    test_benedictions_sjw_poc_8_sur_8()
    test_sjw_bot_poison_bleu_7_sur_8()
    test_sjw_poc_burning_8_sur_8()
    print("ok")
