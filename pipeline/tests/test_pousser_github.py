"""Poussée du passage GitHub avec conflit contre le PC (workflow daily/weekly) : GitHub l'emporte, le PC garde ses fichiers."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pc
import pousser_github
import rapport_pc
from donnees import Donnees
from test_pc import INSTANT, SEM


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def test_conflit_pc_puis_github_resolu_automatiquement():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        _git(t, "init", "-q", "--bare", "-b", "main", "r.git")
        for nom in ("pcw", "gh"):
            _git(t, "clone", "-q", "r.git", nom)
            for k, v in (("user.email", "a@b"), ("user.name", "t")):
                _git(t / nom, "config", k, v)
        pcw, gh = t / "pcw", t / "gh"
        dg = Donnees(gh)
        dg.ecrire("processed.json", {"a": {"status": "en_cours", "week": SEM}})
        dg.ecrire(f"runs/{SEM}/poc.json", {"classement": "base"})
        _git(gh, "checkout", "-q", "-b", "main")
        _git(gh, "add", "."); _git(gh, "commit", "-qm", "init"); _git(gh, "push", "-q", "origin", "main")
        _git(pcw, "pull", "-q", "origin", "main")
        # le PC pousse d'abord : classement, tris 3-4, son rapport
        dp = Donnees(pcw)
        dp.ecrire(f"runs/{SEM}/poc.json", {"classement": "pc"})
        dp.ecrire("processed.json", {"a": {"status": "termine", "week": SEM, "pc": {"tri4": "fait"}}})
        rapport_pc.ecrire_bloc(dp, SEM, "pc-daily", INSTANT, pc.entete_etat(True, 1, 0, 0, []))
        _git(pcw, "add", "."); _git(pcw, "commit", "-qm", "pc"); _git(pcw, "push", "-q", "origin", "main")
        # GitHub (clone ancien) : mêmes fichiers + vidéo b nouvelle
        dg.ecrire(f"runs/{SEM}/poc.json", {"classement": "github"})
        dg.ecrire("processed.json", {"a": {"status": "en_cours", "week": SEM}, "b": {"status": "en_cours", "week": SEM}})
        _git(gh, "add", "."); _git(gh, "commit", "-qm", "gh")
        assert pousser_github.pousser(gh, tentatives=1) is True
        _git(pcw, "pull", "-q", "origin", "main")
        assert json.loads((pcw / f"data/runs/{SEM}/poc.json").read_text())["classement"] == "github"
        p = json.loads((pcw / "data/processed.json").read_text())
        assert p["a"]["pc"]["tri4"] == "fait" and p["a"]["status"] == "termine" and "b" in p
        assert len(rapport_pc.blocs((pcw / f"data/runs/{SEM}/_rapport_pc.md").read_text())) == 1
        assert _git(gh, "status", "--porcelain") == ""


def test_sans_conflit_simple_rebase():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        _git(t, "init", "-q", "--bare", "-b", "main", "r.git")
        _git(t, "clone", "-q", "r.git", "gh")
        for k, v in (("user.email", "a@b"), ("user.name", "t")):
            _git(t / "gh", "config", k, v)
        gh = t / "gh"
        Donnees(gh).ecrire("x.json", {"a": 1})
        _git(gh, "checkout", "-q", "-b", "main")
        _git(gh, "add", "."); _git(gh, "commit", "-qm", "init"); _git(gh, "push", "-q", "origin", "main")
        Donnees(gh).ecrire("x.json", {"a": 2})
        _git(gh, "add", "."); _git(gh, "commit", "-qm", "maj")
        assert pousser_github.pousser(gh, tentatives=1) is True


if __name__ == "__main__":
    test_conflit_pc_puis_github_resolu_automatiquement()
    test_sans_conflit_simple_rebase()
    print("OK")
