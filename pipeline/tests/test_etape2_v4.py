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
    f = t / f"data/runs/{SEM}/bot.json"            # cas testé : BOT sans ligne classée (le vrai classement en a une depuis le 19/11)
    if f.exists():
        bot = json.loads(f.read_text(encoding="utf-8"))
        for r in bot:
            r["rank"] = None
        f.write_text(json.dumps(bot), encoding="utf-8")
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
    assert len(prov) >= 9 and [b["provisional_rank"] for b in prov] == list(range(1, len(prov) + 1))
    assert {"a-923ClD9Rc", "Lt84IhMjBvM", "wJ9CwjKwyco", "5MI-RLj7FSk"} <= {b["video_id"] for b in prov}      # l'ordre suit bot.json (change à chaque classement)
    assert all(b["line_provisional"] and b["rank"] is None and b["confidence"] == "a_verifier"
               and "ligne non classée (score provisoire)" in b["notes"] for b in prov)
    # v8 (top 10 mixte) : GB mêle ses lignes classées (rang gardé) et des provisoires (rank null) ; POC (aucune ligne classée) : tout provisoire
    gb = [b for b in res if b["mode"] == "gb"]
    assert gb and any(not b["line_provisional"] and b["rank"] in (1, 2, 3) for b in gb)
    assert all(b["rank"] is None for b in gb if b["line_provisional"])
    assert all(b["line_provisional"] for b in res if b["mode"] == "poc")
    fichiers = P.exporter(SEM, racine=t, cfg=cfg)
    v1 = prov[0]["video_id"]
    f = t / "exports" / SEM / "builds" / "bot" / f"p01-{v1}-fr.pptx"
    assert f.exists() and len([x for x in fichiers if "/bot/p" in x.replace("\\", "/")]) == 2 * len(prov)
    textes = _pptx_textes(f)
    assert any("CLASSEMENT PROVISOIRE" in x for x in textes) and any(x.startswith("~1") or x == "~1" for x in textes)
    en = _pptx_textes(t / "exports" / SEM / "builds" / "bot" / f"p01-{v1}-en.pptx")
    assert any("PROVISIONAL RANKING" in x for x in en)

    # v8 : une ligne du mode devient classée -> elle perd son statut provisoire (build classé, PowerPoint `01-`), les autres provisoires RESTENT
    ligne = next(r for r in bot if r["video_id"] == v1)
    ligne["rank"], ligne["confidence"] = 1, "sur"
    (t / f"data/runs/{SEM}/bot.json").write_text(json.dumps(bot, ensure_ascii=False), encoding="utf-8")
    res = B.calculer(SEM, racine=t, cfg=cfg, banque=object())
    bots = [b for b in res if b["mode"] == "bot"]
    assert [b["video_id"] for b in bots if b["rank"] == 1] == [v1] and sum(1 for b in bots if b["line_provisional"]) == len(prov) - 1
    P.exporter(SEM, racine=t, cfg=cfg)
    assert (t / "exports" / SEM / "builds" / "bot" / f"01-{v1}-fr.pptx").exists()
    assert not list((t / "exports" / SEM / "builds" / "bot").glob(f"p*-{v1}-*.pptx"))
    assert len(list((t / "exports" / SEM / "builds" / "bot").glob("p*-fr.pptx"))) == len(prov) - 1


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
