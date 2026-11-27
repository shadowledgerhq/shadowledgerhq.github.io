"""post_x.py : images du post X du mercredi (lignes sûres rang 1-3 seulement, « — » sinon, HOTM en 3 colonnes)."""
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import post_x
from donnees import Donnees


def _l(rank, nom, total, unit, conf="sur"):
    return {"rank": rank, "channel": nom, "player": nom, "confidence": conf, "score": {"total": total, "unit": unit}}


def _jeu():
    tmp = tempfile.mkdtemp()
    d = Donnees(tmp)
    w = "2026-11-12"
    d.ecrire(f"runs/{w}/_meta.json", {"week": w, "frozen": False})
    d.ecrire(f"runs/{w}/poc.json", [_l(1, "Ann & <Bob>", 1234567, "rank_score"), _l(2, "Cy", 1000, "rank_score", "a_verifier"),
                                    _l(None, "Dee", 5, "rank_score")])
    d.ecrire(f"runs/{w}/bot.json", [_l(1, "Eve", 19.5, "seconds"), _l(2, "Fay", 61.004, "seconds")])
    d.ecrire(f"runs/{w}/gb.json", [_l(1, "Gus", 293, "rage_count"), _l(1, "Hal", 293, "rage_count"), _l(3, "Ike", 100, "rage_count")])
    d.ecrire(f"runs/{w}/hotm-gate-2.json", [_l(1, "Jo", 987654, "points")])
    return tmp, d, w


def test_top3_garde_seulement_sur_avec_rang():
    _, d, w = _jeu()
    assert [l["channel"] for l in post_x.top3(d.lire(f"runs/{w}/poc.json", []))] == ["Ann & <Bob>"]


def test_formats_scores():
    assert post_x.score_txt(_l(1, "x", 19.5, "seconds"), "bot") == "0:19.500"
    assert post_x.score_txt(_l(1, "x", 61.004, "seconds"), "bot") == "1:01.004"
    assert post_x.score_txt(_l(1, "x", 293, "rage_count"), "gb") == "293 RC"
    assert post_x.score_txt(_l(1, "x", 1234567, "rank_score"), "poc") == "1 234 567"
    assert post_x.score_txt(_l(1, "x", 987654, "points"), "hotm") == "987 654 pts"


def test_generation_complete():
    tmp, d, w = _jeu()
    try:
        sortie, rendus = post_x.generer(w, d)
        assert sortie == Path(tmp) / "exports" / w / "x"
        assert len(rendus) == 4
        alt = (sortie / "alt.txt").read_text(encoding="utf-8")
        assert "POC top 3, semaine du 12 novembre 2026 : 1 Ann & <Bob> 1 234 567" in alt
        assert "Cy" not in alt and "Dee" not in alt                      # a_verifier / sans rang : jamais affichés
        assert "1 Gus 293 RC, 1 Hal 293 RC, 3 Ike 100 RC" in alt         # ex aequo conservés
        assert "porte 1 : aucune ligne sûre ; porte 2 : 1 Jo 987 654 pts" in alt
        texte = (sortie / "texte.txt").read_text(encoding="utf-8")
        assert "Quasi définitif, reset jeudi 01h (Paris) · Final at Thursday reset" in texte and len(texte) < 280
        fichiers = {p.name for p in sortie.iterdir()}
        assert {"texte.txt", "alt.txt"} <= fichiers
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_svg_valide_et_echappe():
    import xml.dom.minidom
    _, d, w = _jeu()
    g = post_x.GABARIT.read_text(encoding="utf-8")
    svg = post_x.svg_mode(g, "poc", post_x.top3(d.lire(f"runs/{w}/poc.json", [])), w, {})
    xml.dom.minidom.parseString(svg)
    assert "Ann &amp; &lt;Bob&gt;" in svg and not re.search(r"\{\{\w+\}\}", svg)
    hotm = post_x.svg_hotm(g, post_x.portes(d, w), w, {})
    xml.dom.minidom.parseString(hotm)
    assert "Gate 2" in hotm and not re.search(r"\{\{\w+\}\}", hotm)


def test_gele_et_noms_longs():
    _, d, w = _jeu()
    assert post_x.statut({"frozen": True})[0] == "Classement définitif"
    assert len(post_x.nom_txt({"channel": "x" * 60})) == post_x.NOM_MAX
