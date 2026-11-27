"""pipeline/video/script_md.py régénère à l'identique le script.md déjà versionné (videos/<semaine>/<mode>/)."""
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def test_script_md_identique_aux_fichiers_versionnes():
    jsons = sorted((RACINE / "videos").glob("*/*/video.json"))
    for j in jsons:
        with tempfile.TemporaryDirectory() as tmp:
            sortie = Path(tmp) / "script.md"
            subprocess.run([sys.executable, str(RACINE / "pipeline/video/script_md.py"), str(j), str(sortie)], check=True)
            assert sortie.read_text(encoding="utf-8") == (j.parent / "script.md").read_text(encoding="utf-8"), j
