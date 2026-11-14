"""SPEC §4.1 (v16) : une ligne POC ou GB avec une seule run `sur` est classée ; complétée par une 2e run plus tard."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecrans
import ocr_ecrans
from classement import calculer
from donnees import charger_config
from test_classement import CONFIG, HORLOGE, T, W, lec, lire, preparer
from test_gb import meta as meta_gb


def test_poc_une_seule_run_sure_classee_puis_completee():
    d = preparer([lec("a1", "UCA", "poc", 100 * T, team=1), lec("b1", "UCB", "poc", 90 * T, team=1), lec("b2", "UCB", "poc", 40 * T, team=2)])
    calculer(W, d, CONFIG, HORLOGE)
    poc = lire(d, "poc")
    assert [(l["channel_id"], l["rank"], l["score"]["total"], l["confidence"]) for l in poc] == [("UCB", 1, 130 * T, "sur"), ("UCA", 2, 100 * T, "sur")]
    assert "une seule run" in poc[1]["notes"] and "une seule run" not in poc[0]["notes"]
    # la 2e run (autre équipe) arrive plus tard dans la semaine : elle s'ajoute au total
    d = preparer([lec("a1", "UCA", "poc", 100 * T, team=1), lec("a2", "UCA", "poc", 70 * T, team=2, jour=15)])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "poc")
    assert l["score"]["total"] == 170 * T and l["rank"] == 1 and "une seule run" not in l["notes"]


def test_une_seule_run_provisoire_reste_a_verifier():
    d = preparer([lec("a1", "UCA", "poc", 100 * T, exact=False, confidence="a_verifier", score_source="titre", team=1)])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "poc")
    assert l["confidence"] == "a_verifier" and l["rank"] is None and "une seule run trouvée" in l["notes"]
    # une run sûre + une run provisoire (titre) d'une autre équipe : le provisoire n'est jamais additionné à une run exacte
    # (§4.3) ; la run sûre est classée seule, la 2e run s'ajoutera quand elle sera lue à l'écran
    d = preparer([lec("b1", "UCB", "poc", 100 * T, team=1),
                  lec("b2", "UCB", "poc", 60 * T, exact=False, confidence="a_verifier", score_source="titre", team=2)])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "poc")
    assert l["rank"] == 1 and l["score"]["total"] == 100 * T and l["confidence"] == "sur" and "une seule run" in l["notes"]


# --- GB : Personal Record (cas de la spec) --------------------------------------------------------------

AWB = """< Guild Boss 2 ial
@ time Lettinseason 6d 22h } Personal Record 2
Total Score Challenge Count 1
B4.299,126,429,862 | totalrage count 189
Group 1 £189 64.29T @
Group 2 No history
"""


def test_awb_record_un_seul_groupe_classe_189():
    m = meta_gb("awb-GlVIa7Q")
    ecran = ocr_ecrans.lire_gb_record(AWB)
    assert ecran["groups"][2] == {"no_history": True} and ecran["groups"][1]["rage_count"] == 189
    ecran.update(total_score=64299126429862, total_rage_count=189, challenge_count=1, time_left="6d 22h", t=241)
    (r,) = ecrans.lectures_gb_record(m, ecran, CONFIG)
    assert (r["team"], r["score"], r["score_source"], r["confidence"], r["exact"]) == (1, 189, "record", "sur", True)
    assert r["damage"] == 64299126429862 and r["detail"]["damage_exact"] is True and r["detail"]["damage_source"] == "record"
    d = preparer([{**r, "channel_id": "UCawb", "video_id": "awb", "published_at": "2026-11-12T01:07:38Z"}])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert (l["score"]["total"], l["rank"], l["confidence"]) == (189, 1, "sur") and "une seule run" in l["notes"]
    assert l["runs_detail"][0]["team"] == 1 and l["runs_detail"][0]["damage"] == 64299126429862 and l["runs_detail"][0]["damage_exact"] is True
    assert l["runs_detail"][0]["damage_source"] == "record"


def test_nh2d_record_deux_groupes_classe_332():
    m = meta_gb("nh2D7xZ7dOQ")
    ecran = {"groups": {1: {"rage_count": 167, "damage": "17.28T"}, 2: {"rage_count": 165, "damage": "15.55T"}},
             "total_rage_count": 332, "total_score": 32842054460310, "challenge_count": 2, "time_left": "6d 9h", "t": 2}
    rs = ecrans.lectures_gb_record(m, ecran, CONFIG)
    assert [(r["team"], r["score"], r["confidence"]) for r in rs] == [(1, 167, "sur"), (2, 165, "sur")]
    assert all(r["detail"].get("damage_source") is None for r in rs)            # deux groupes joués : dégâts arrondis par groupe
    d = preparer([{**r, "channel_id": "UCnh", "video_id": "nh", "published_at": "2026-11-13T10:14:16Z"} for r in rs])
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert (l["score"]["total"], l["rank"], l["confidence"]) == (332, 1, "sur") and "une seule run" not in l["notes"]


def test_record_non_controle_ne_donne_pas_le_total_score():
    m = meta_gb("x")
    ecran = {"groups": {1: {"rage_count": 189, "damage": "64.29T"}, 2: {"no_history": True}}, "total_rage_count": None,     # Total Rage Count illisible
             "total_score": 4299126429862, "t": 1}                                                                          # « B4.299… » lu pour « 64,299… »
    (r,) = ecrans.lectures_gb_record(m, ecran, CONFIG)
    assert r["confidence"] == "a_verifier" and r["detail"].get("damage_source") is None and r["damage"] == 64290000000000


def test_record_groupe_illisible_reste_a_verifier():
    m = meta_gb("x")
    ecran = {"groups": {1: {"rage_count": 189, "damage": "64.29T"}}, "total_rage_count": 189, "total_score": 5, "t": 1}   # groupe 2 ni lu ni « No history »
    (r,) = ecrans.lectures_gb_record(m, ecran, CONFIG)
    assert r["confidence"] == "a_verifier" and r["detail"].get("damage_source") is None


def test_publication_d_essai_sans_pull_ni_conflit():
    """Essai du 14/11 : `git pull --rebase --autostash` échouait (data/ modifié par --no-git) et laissait un fichier « unmerged »."""
    import subprocess
    import tempfile
    import pc

    def git(cwd, *a):
        return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        git(tmp, "init", "-q", "--bare", "r.git")
        git(tmp, "clone", "-q", "r.git", "w")
        w = tmp / "w"
        for k, v in (("user.email", "a@b"), ("user.name", "t")):
            git(w, "config", k, v)
        git(w, "checkout", "-q", "-b", "main")
        (w / "data").mkdir()
        (w / "docs/essais/ocr").mkdir(parents=True)
        (w / "data/x").write_text("1")
        (w / "docs/essais/ocr/old.txt").write_text("old")
        git(w, "add", ".")
        git(w, "commit", "-qm", "i")
        git(w, "push", "-q", "origin", "main")
        git(tmp, "clone", "-q", "-b", "main", "r.git", "w2")
        w2 = tmp / "w2"
        for k, v in (("user.email", "a@b"), ("user.name", "t")):
            git(w2, "config", k, v)
        (w2 / "data/x").write_text("remote")
        git(w2, "commit", "-qam", "remote")
        git(w2, "push", "-q", "origin", "main")
        # côté PC : data/ modifié par un essai --no-git, fichiers d'essai neufs et modifiés
        (w / "data/x").write_text("local")
        (w / "docs/essais/ocr/new.txt").write_text("new")
        (w / "docs/essais/ocr/old.txt").write_text("changed")
        avant = git(w, "rev-parse", "HEAD")
        assert pc.Git(w).pousser_chemin("essai", "docs/essais/ocr") is True
        assert git(w, "rev-parse", "HEAD") == avant and (w / "data/x").read_text() == "local"          # HEAD et data/ intacts
        assert not (w / "docs/essais/ocr/new.txt").exists() and (w / "docs/essais/ocr/old.txt").read_text() == "old"
        assert "unmerged" not in git(w, "status") and "claude/essai-pc-" in git(w, "ls-remote", "origin")
        branche = [l.split("refs/heads/")[1] for l in git(w, "ls-remote", "origin").splitlines() if "essai-pc" in l][0]
        git(w2, "fetch", "-q", "origin", branche)
        assert git(w2, "show", f"origin/{branche}:docs/essais/ocr/new.txt") == "new"               # le contenu est bien sur la branche
        assert pc.Git(w).pousser_chemin("essai", "docs/essais/ocr") is False                         # rien de nouveau : pas de commit


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
