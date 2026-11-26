"""data/runs/index.json (SPEC_SITE §3) : écrit à chaque calcul de classement."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from donnees import Donnees, mettre_a_jour_index


def test_index_boards_et_gel():
    tmp = tempfile.mkdtemp()
    try:
        d = Donnees(tmp)
        d.ecrire("runs/2026-11-12/_meta.json", {"week": "2026-11-12", "frozen": True, "frozen_at": "2026-11-19T01:00:00Z"})
        for n in ("bot", "poc", "hotm-gate-inconnue", "_boss", "_lectures"):
            d.ecrire(f"runs/2026-11-12/{n}.json", [])
        d.ecrire("runs/2026-11-19/_meta.json", {"week": "2026-11-19", "frozen": False, "frozen_at": None})
        d.ecrire("runs/2026-11-19/gb.json", [])
        d.ecrire("runs/sans-meta/gb.json", [])
        assert mettre_a_jour_index(d) is True
        idx = json.loads((Path(tmp) / "data/runs/index.json").read_text(encoding="utf-8"))
        assert idx == {"weeks": [
            {"week": "2026-11-12", "frozen": True, "frozen_at": "2026-11-19T01:00:00Z", "boards": ["bot", "poc"]},
            {"week": "2026-11-19", "frozen": False, "frozen_at": None, "boards": ["gb"]}]}
        assert mettre_a_jour_index(d) is False   # idempotent
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
