"""Rien de public avant le lancement (CONTEXTE §2, 26/11/2026) : site noindex, déploiement manuel, aucun envoi vers les réseaux."""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_site

RACINE = Path(__file__).resolve().parents[2]
INTERDITS = re.compile(r"api\.twitter\.com|api\.x\.com|discord(app)?\.com/api|webhooks?/\d|videos\(\)\.insert|MediaFileUpload|upload/youtube|tiktok.*/post", re.I)


def test_site_prive():
    assert check_site.verifier(RACINE) == []


def test_controle_detecte_page_sans_noindex():
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / "site").mkdir()
        (Path(t) / "site" / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        (Path(t) / "site" / "a.html").write_text("<html><head></head></html>")
        assert any("a.html" in e for e in check_site.verifier(t))
        (Path(t) / "site" / "a.html").write_text('<meta name="robots" content="noindex">')
        assert check_site.verifier(t) == []


def test_aucun_script_ne_publie():
    for dossier in ("pipeline", "tools", "outils-pc"):
        for f in (RACINE / dossier).rglob("*"):
            if f.suffix in (".py", ".bat", ".ps1") and "tests" not in f.parts and f.name != "check_site.py":
                assert not INTERDITS.search(f.read_text(encoding="utf-8", errors="replace")), f


def test_deploiement_site_manuel_seulement():
    for wf in (RACINE / ".github" / "workflows").glob("*.yml"):
        t = wf.read_text(encoding="utf-8")
        if "deploy-pages" in t or "upload-pages-artifact" in t:
            assert wf.name == "deployer-site.yml"
            assert re.search(r"^on:\n  workflow_dispatch:", t, re.M) and "schedule" not in t and "push:" not in t


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")
