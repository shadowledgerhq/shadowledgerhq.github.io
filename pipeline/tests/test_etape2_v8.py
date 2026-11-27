"""SPEC_ETAPE2 v8 : top 10 mixte (classées + provisoires triées par score) ; champ `spec` = config.spec_version."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import builds


def _ligne(vid, total, rank=None, conf="a_verifier", notes=""):
    return {"video_id": vid, "run_id": f"x-{vid}", "rank": rank, "confidence": conf, "notes": notes, "score": {"total": total}}


def _selection(mode_fichier, lignes, top=10, prov=True):
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "data" / "runs" / "2026-11-12"
        d.mkdir(parents=True)
        (d / f"{mode_fichier}.json").write_text(json.dumps(lignes), encoding="utf-8")
        return builds.modes_du_top("2026-11-12", Path(tmp), {"top": top, "builds_provisoires": prov})


def test_bot_provisoires_devant_la_seule_classee():
    """Cas BOT 2026-11-12 : 3 provisoires plus rapides que la seule ligne classée."""
    lignes = [_ligne("Bi5", 28.349, 1, "sur"), _ligne("YSJ", 19.517), _ligne("a92", 22.0), _ligne("znp", 25.5)]
    sel = _selection("bot", lignes)
    assert [l["video_id"] for _, l in sel] == ["YSJ", "a92", "znp", "Bi5"]
    assert [l.get("provisional_rank") for _, l in sel] == [1, 2, 3, None]
    assert [l["rank"] for _, l in sel] == [None, None, None, 1]
    assert [bool(l.get("line_provisional")) for _, l in sel] == [True, True, True, False]


def test_poc_ordre_decroissant_et_limite_top():
    lignes = [_ligne("a", 100, 1, "sur"), _ligne("b", 300), _ligne("c", 200), _ligne("d", 50)]
    sel = _selection("poc", lignes, top=3)
    assert [l["video_id"] for _, l in sel] == ["b", "c", "a"]          # d sort du top 3 : pas de build
    assert sel[2][1]["rank"] == 1 and sel[0][1]["provisional_rank"] == 1


def test_ecart_improbable_et_sans_score_exclus_et_option_off():
    lignes = [_ligne("a", 20, 1, "sur"), _ligne("b", 10, notes="écart improbable"), _ligne("c", None)]
    assert [l["video_id"] for _, l in _selection("bot", lignes)] == ["a"]
    assert [l["video_id"] for _, l in _selection("bot", [_ligne("a", 20, 1, "sur"), _ligne("z", 10)], prov=False)] == ["a"]


def test_porte_inconnue_ignoree():
    assert _selection("hotm-gate-inconnue", [_ligne("a", 1)]) == []


def test_champ_spec_vient_de_la_config():
    cfg = builds.charger_config()
    assert cfg["spec_version"] == 8 and "spec" not in cfg
