"""Rapport du PC (`_rapport_pc.md`), échecs tracés, conflit git résolu automatiquement (demande de la discussion 1, critère de gel n° 3)."""
import json
import subprocess
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import etape1
import fusion_pc
import pc
import rapport_pc
from donnees import Donnees
from test_pc import INSTANT, SEM, VTT, FauxOutils, config_sans_images, monde


def fichier(d):
    return (d.data / "runs" / SEM / "_rapport_pc.md").read_text(encoding="utf-8")


def test_un_bloc_par_passage_jamais_efface():
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        pc.lancer("daily", INSTANT, d, config, FauxOutils({v: VTT for v in "abcd"}), fichier_relance=Path(tmp) / "r.json")
        pc.lancer("daily", INSTANT + timedelta(hours=2), d, config, FauxOutils({}), fichier_relance=Path(tmp) / "r.json", relance=True)
        b = rapport_pc.blocs(fichier(d))
        assert len(b) == 2 and "Passage complet" in b[0] and "Passage complet" in b[1]
        premier = b[0]
        pc.lancer("daily", INSTANT, d, config, FauxOutils({}), fichier_relance=Path(tmp) / "r.json")     # même passage rejoué : son bloc est remplacé
        b2 = rapport_pc.blocs(fichier(d))
        assert len(b2) == 2 and b2[1] == b[1]                                                              # l'autre bloc n'est jamais touché
        assert "pc-daily" in premier


def test_passage_github_recopie_le_dernier_bloc_sans_toucher_au_fichier_pc():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", INSTANT, pc.entete_etat(False, 0, 4, 4, ["anti-bot YouTube"]))
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", INSTANT + timedelta(hours=2), pc.entete_etat(True, 4, 0, 0, []))
        avant = fichier(d)
        res = {"gelee": False, "fichiers": {}, "a_verifier": [], "alertes_boss": [], "alertes_semaine_bot": []}
        etape1.ecrire_rapport(d, SEM, "daily", INSTANT + timedelta(hours=3), None, res, [])
        txt = (d.data / "runs" / SEM / "_rapport.md").read_text(encoding="utf-8")
        assert "Dernier passage du PC" in txt and "Passage complet : oui" in txt and "anti-bot" not in txt.split("## À vérifier")[0]
        assert fichier(d) == avant                                                                           # jamais modifié par GitHub
        d2 = monde(tempfile.mkdtemp())
        etape1.ecrire_rapport(d2, SEM, "daily", INSTANT, None, res, [])
        assert "Aucun passage du PC" in (d2.data / "runs" / SEM / "_rapport.md").read_text(encoding="utf-8")


def test_echec_ecrit_son_bloc_avec_la_cause():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        pc.signaler_echec("daily", INSTANT, "git : conflit sur data/", d)
        pc.signaler_echec("daily", INSTANT + timedelta(hours=2), "passage interrompu (PC éteint)", d)
        b = rapport_pc.blocs(fichier(d))
        assert len(b) == 2 and all("Passage complet : non" in x for x in b)
        assert "git : conflit sur data/" in b[0] and "passage interrompu" in b[1]
        assert "Passage complet : non" in (d.data / "runs" / SEM / "_rapport.md").read_text(encoding="utf-8")


def test_verrou_perime_garde_le_detenteur_mort():
    with tempfile.TemporaryDirectory() as tmp:
        v = pc.Verrou(Path(tmp) / "pc.lock")
        (Path(tmp) / "pc.lock").write_text(json.dumps({"pid": 99999999, "passage": "daily", "debut": time.time() - 3600}))
        ok, _ = v.prendre("daily")
        assert ok and v.perime and v.perime["passage"] == "daily"
        v.liberer()


def test_fusion_processed_et_lectures():
    distant = {"a": {"status": "en_cours", "week": "w", "modes": ["poc"]}, "b": {"status": "en_cours", "week": "w"}}
    local = {"a": {"status": "termine", "week": "w", "pc": {"tri3": "fait", "tri4": "fait"}, "pc_needed": True}, "z": {"status": "en_cours"}}
    f = fusion_pc.fusionner_processed(distant, local)
    assert f["a"]["pc"]["tri4"] == "fait" and f["a"]["status"] == "termine" and f["a"]["modes"] == ["poc"]
    assert f["b"] == distant["b"] and "z" in f
    assert fusion_pc.est_propre_pc("data/runs/2026-11-12/_rapport_pc.md") and not fusion_pc.est_propre_pc("data/runs/2026-11-12/_rapport.md")


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_conflit_git_resolu_automatiquement():
    """Le PC et GitHub modifient les mêmes fichiers : distant pour GitHub, PC pour les tris 3-4, `_rapport_pc.md` jamais perdu."""
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        _git(t, "init", "-q", "--bare", "-b", "main", "r.git")
        for nom in ("pcw", "gh"):
            _git(t, "clone", "-q", "r.git", nom)
            for k, v in (("user.email", "a@b"), ("user.name", "t")):
                _git(t / nom, "config", k, v)
        pcw, gh = t / "pcw", t / "gh"
        d0 = Donnees(gh)
        d0.ecrire("processed.json", {"a": {"status": "en_cours", "week": SEM}})
        d0.ecrire(f"runs/{SEM}/poc.json", {"classement": "base"})
        d0.ecrire(f"runs/{SEM}/_rapport.md", "# base\n")
        _git(gh, "checkout", "-q", "-b", "main")
        _git(gh, "add", "."); _git(gh, "commit", "-qm", "init"); _git(gh, "push", "-q", "origin", "main")
        _git(pcw, "pull", "-q", "origin", "main")
        # GitHub : classement + rapport + processed (vidéo b nouvelle)
        d0.ecrire(f"runs/{SEM}/poc.json", {"classement": "github"})
        d0.ecrire(f"runs/{SEM}/_rapport.md", "# github\n")
        d0.ecrire("processed.json", {"a": {"status": "en_cours", "week": SEM}, "b": {"status": "en_cours", "week": SEM}})
        _git(gh, "add", "."); _git(gh, "commit", "-qm", "gh"); _git(gh, "push", "-q", "origin", "main")
        # PC : mêmes fichiers modifiés + tris 3-4 + son rapport (non commités : `tirer` les commite)
        dp = Donnees(pcw)
        dp.ecrire(f"runs/{SEM}/poc.json", {"classement": "pc"})
        dp.ecrire(f"runs/{SEM}/_rapport.md", "# pc\n")
        dp.ecrire("processed.json", {"a": {"status": "termine", "week": SEM, "pc": {"tri4": "fait"}}})
        rapport_pc.ecrire_bloc(dp, SEM, "pc-daily", INSTANT, pc.entete_etat(False, 0, 1, 1, ["git : x"]))
        g = pc.Git(pcw)
        g.tirer()
        assert g.conflit_resolu is True
        assert json.loads((pcw / f"data/runs/{SEM}/poc.json").read_text())["classement"] == "github"        # distant : fichier GitHub
        assert (pcw / f"data/runs/{SEM}/_rapport.md").read_text() == "# github\n"
        p = json.loads((pcw / "data/processed.json").read_text())
        assert p["a"]["pc"]["tri4"] == "fait" and p["a"]["status"] == "termine" and "b" in p                 # fusion par vidéo
        assert len(rapport_pc.blocs((pcw / f"data/runs/{SEM}/_rapport_pc.md").read_text())) == 1             # bloc du PC conservé
        assert _git(pcw, "status", "--porcelain") == ""
        g.pousser("test")
        _git(gh, "pull", "-q", "origin", "main")
        assert (gh / f"data/runs/{SEM}/_rapport_pc.md").exists()


def test_relance_mot_nu_de_la_tache_planifiee():
    """La tâche lance `pc.py daily relance` : le mot nu devient `--relance` (erreur argparse du 15/11 à 02:32)."""
    assert pc.normaliser_argv(["daily", "relance"]) == ["daily", "--relance"]
    assert pc.normaliser_argv(["weekly", "--video", "x"]) == ["weekly", "--video", "x"]


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")


def test_v28_pull_reessaye_quand_le_reseau_coupe():
    """Réseau coupé (« Could not resolve host ») : 3 nouvelles tentatives espacées, puis succès ou abandon ; pas de conflit simulé."""
    class Faux(pc.Git):
        def __init__(self, echecs):
            super().__init__(".", dormir=lambda s: pauses.append(s))
            self.echecs, self.appels = echecs, []

        def _run(self, *args):
            self.appels.append(args[0])
            if args[0] == "pull" and self.echecs > 0:
                self.echecs -= 1
                raise pc.GitErreur("git pull : fatal: unable to access 'https://github.com/x.git/': Could not resolve host: github.com")
            return ""
    pauses = []
    g = Faux(2)
    g._rebase()
    assert pauses == [30, 90] and g.appels.count("pull") == 3 and not getattr(g, "conflit_resolu", False)
    pauses.clear()
    g = Faux(9)
    try:
        g._rebase()
        assert False
    except pc.GitErreur as e:
        assert "resolve host" in str(e)
    assert pauses == [30, 90, 180] and g.appels.count("pull") == 4
