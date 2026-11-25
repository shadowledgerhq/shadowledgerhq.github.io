"""SPEC_ETAPE2 v7 §2.1 : plusieurs cartes par chasseur (`<id>.png`, `<id>--tenue<N>.png`), sans opencv (correspondances simulées)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image

import portraits as P

CFG = {"portraits": {"min_corr_biblio": 40, "rapport": 2}}


def img(couleur):
    return Image.new("RGB", (8, 8), couleur)


def faux(monkeypatch_table):
    """Remplace `correspondances` : score = table[(couleur carte, couleur vue)]."""
    def f(vue, carte):      # même ordre d'arguments que `apparier_cartes` : (image vue, carte de référence)
        return monkeypatch_table.get((carte.getpixel((0, 0)), vue.getpixel((0, 0))), 0)
    P.correspondances = f


def test_charger_regroupe_les_tenues_par_identifiant():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "hunters_cartes"
        d.mkdir()
        for nom, c in (("a.png", (1, 0, 0)), ("a--tenue2.png", (2, 0, 0)), ("b.png", (3, 0, 0))):
            img(c).save(d / nom)
        cartes = P.charger_cartes(tmp)
        assert sorted(cartes) == ["a", "b"] and len(cartes["a"]) == 2 and len(cartes["b"]) == 1
        assert P.identifiant("a--tenue2") == "a" and P.identifiant("a") == "a"


def test_deux_cartes_du_meme_chasseur_ne_se_bloquent_pas():
    orig = P.correspondances
    try:
        base, tenue = (1, 0, 0), (2, 0, 0)
        vue = (9, 9, 9)
        faux({(base, vue): 80, (tenue, vue): 78})          # les deux tenues de `a` proches : pas un conflit
        trouves, m = P.apparier_cartes({1: img(vue)}, {"a": [img(base), img(tenue)], "b": [img((3, 0, 0))]}, CFG)
        assert trouves == {1: "a"} and m[1]["a"] == 80
    finally:
        P.correspondances = orig


def test_la_tenue_alternative_peut_etre_la_meilleure():
    orig = P.correspondances
    try:
        base, tenue, vue = (1, 0, 0), (2, 0, 0), (9, 9, 9)
        faux({(base, vue): 10, (tenue, vue): 90})
        trouves, _ = P.apparier_cartes({1: img(vue)}, {"a": [img(base), img(tenue)]}, CFG)
        assert trouves == {1: "a"}
    finally:
        P.correspondances = orig


def test_deux_chasseurs_differents_proches_restent_non_apparies():
    orig = P.correspondances
    try:
        a, b, vue = (1, 0, 0), (3, 0, 0), (9, 9, 9)
        faux({(a, vue): 80, (b, vue): 70})                   # 80 < 2 × 70 : ambigu
        trouves, _ = P.apparier_cartes({1: img(vue)}, {"a": [img(a)], "b": [img(b)]}, CFG)
        assert trouves == {}
    finally:
        P.correspondances = orig


def test_ancien_format_image_seule_toujours_accepte():
    orig = P.correspondances
    try:
        a, vue = (1, 0, 0), (9, 9, 9)
        faux({(a, vue): 80})
        trouves, _ = P.apparier_cartes({1: img(vue)}, {"a": img(a)}, CFG)
        assert trouves == {1: "a"}
    finally:
        P.correspondances = orig
