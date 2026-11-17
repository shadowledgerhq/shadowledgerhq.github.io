"""Tests SPEC_ETAPE2 v4 : builds sur classement provisoire (test 18)."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import builds as B
import export_pptx as P

SEM = "2026-11-12"


def _racine_temp():
    """Copie légère du dépôt : lignes de la semaine, règles, base (sans icônes)."""
    t = Path(tempfile.mkdtemp())
    for rel in (f"data/runs/{SEM}", "data/rules", "data/db"):
        src = B.RACINE / rel
        if src.exists():
            shutil.copytree(src, t / rel)
    return t


def _pptx_textes(chemin):
    from pptx import Presentation
    return [sh.text_frame.text for sl in Presentation(str(chemin)).slides for sh in sl.shapes if sh.has_text_frame]


def test_18_bot_sans_ligne_classee_builds_provisoires():
    t = _racine_temp()
    bot = json.loads((t / f"data/runs/{SEM}/bot.json").read_text(encoding="utf-8"))
    assert not any(r.get("rank") for r in bot), "le cas réel suppose un BOT sans ligne classée"
    cfg = B.charger_config()
    assert cfg["builds_provisoires"] is True
    res = B.calculer(SEM, racine=t, cfg=cfg, banque=object())
    prov = sorted((b for b in res if b["mode"] == "bot"), key=lambda b: b["provisional_rank"])
    assert len(prov) >= 9 and prov[0]["video_id"] == "a-923ClD9Rc" and prov[0]["provisional_rank"] == 1
    assert [b["video_id"] for b in prov[:4]] == ["a-923ClD9Rc", "Lt84IhMjBvM", "wJ9CwjKwyco", "5MI-RLj7FSk"]      # v34 : X SLA 19.926 (miniature) avant PADWAE 19.9 (rang prudent 19.999)
    assert all(b["line_provisional"] and b["rank"] is None and b["confidence"] == "a_verifier"
               and "ligne non classée (score provisoire)" in b["notes"] for b in prov)
    # GB a des lignes classées : inchangé, aucun provisoire ; POC (aucune ligne classée) suit la même règle §0
    gb = [b for b in res if b["mode"] == "gb"]
    assert gb and not any(b["line_provisional"] for b in gb) and all(b["rank"] in (1, 2, 3) for b in gb)
    assert all(b["line_provisional"] for b in res if b["mode"] == "poc")
    fichiers = P.exporter(SEM, racine=t, cfg=cfg)
    f = t / "exports" / SEM / "builds" / "bot" / "p01-a-923ClD9Rc-fr.pptx"
    assert f.exists() and len([x for x in fichiers if "/bot/p" in x.replace("\\", "/")]) == 2 * len(prov)
    textes = _pptx_textes(f)
    assert any("CLASSEMENT PROVISOIRE" in x for x in textes) and any(x.startswith("~1") or x == "~1" for x in textes)
    en = _pptx_textes(t / "exports" / SEM / "builds" / "bot" / "p01-a-923ClD9Rc-en.pptx")
    assert any("PROVISIONAL RANKING" in x for x in en)

    # une ligne du mode devient classée : builds et PowerPoint provisoires supprimés au passage suivant
    bot[0]["rank"], bot[0]["confidence"] = 1, "sur"
    (t / f"data/runs/{SEM}/bot.json").write_text(json.dumps(bot, ensure_ascii=False), encoding="utf-8")
    res = B.calculer(SEM, racine=t, cfg=cfg, banque=object())
    assert [b["rank"] for b in res if b["mode"] == "bot"] == [1] and not any(b["line_provisional"] for b in res if b["mode"] != "poc")
    assert not [f for f in (t / f"data/builds/{SEM}/bot").glob("*.json") if json.loads(f.read_text(encoding="utf-8")).get("line_provisional")]
    P.exporter(SEM, racine=t, cfg=cfg)
    assert not list((t / "exports" / SEM / "builds" / "bot").glob("p*.pptx"))
    assert (t / "exports" / SEM / "builds" / "bot" / "01-a-923ClD9Rc-fr.pptx").exists()


def test_provisoire_desactive():
    t = _racine_temp()
    cfg = dict(B.charger_config(), builds_provisoires=False)
    res = B.calculer(SEM, racine=t, cfg=cfg, banque=object())
    assert not [b for b in res if b["mode"] == "bot"]


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
