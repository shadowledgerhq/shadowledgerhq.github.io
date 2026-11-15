"""Passage PC : état en tête du rapport, relance anti-bot unique par soir (discussion 1, critère de gel n° 3)."""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pc
from donnees import Donnees
from test_pc import INSTANT, SEM, VTT, FauxOutils, config_sans_images, monde


def rapport(d):
    return (d.data / "runs" / SEM / "_rapport.md").read_text(encoding="utf-8")


def test_passage_complet_entete():
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        r = pc.lancer("daily", INSTANT, d, config, FauxOutils({v: VTT for v in "abcd"}), fichier_relance=Path(tmp) / "r.json")
        assert r["traitees"] == 4 and r["bloquantes"] == []
        tete = rapport(d).split("\n")[:8]
        assert "Passage complet" in "".join(tete[:4]) and "- Erreurs bloquantes : aucune" in tete
        assert any(l.startswith("- Vidéos traitées ce passage : 4") for l in tete)


def test_antibot_relance_unique_par_soir():
    config = config_sans_images()
    planifiees = []
    with tempfile.TemporaryDirectory() as tmp:
        fichier = Path(tmp) / "relance.json"
        d = monde(tmp)
        o = FauxOutils({"a": VTT}, erreurs=["b"], erreurs_msg={"b": "HTTP Error 429: Too Many Requests"})
        r = pc.lancer("daily", INSTANT, d, config, o, planifier=lambda q, bat: planifiees.append(q), fichier_relance=fichier)
        assert r["complet"] is False and "anti-bot YouTube" in r["bloquantes"][0]
        assert planifiees == [datetime(2026, 11, 13, 22, 30)]                 # 20:30 Paris + 2 h
        tete = rapport(d).split("\n")[:9]
        assert "Passage complet : non" in tete[2] and "anti-bot" in tete[2]
        assert any(l.startswith("- Relance automatique : 13/11/2026 22:30") for l in tete)
        assert any("anti-bot" in l and l.startswith("- Erreurs bloquantes") for l in tete)
        assert any(l.startswith("- Durée du passage : ") and l.endswith(" min") for l in rapport(d).split("\n")[:12])
        # 2e blocage le même soir : pas de nouvelle relance ; la relance elle-même n'en programme pas non plus
        o2 = FauxOutils({}, erreurs=["b"], erreurs_msg={"b": "HTTP Error 429: Too Many Requests"})
        pc.lancer("daily", INSTANT, d, config, o2, planifier=lambda q, bat: planifiees.append(q), fichier_relance=fichier)
        pc.lancer("daily", INSTANT, d, config, o2, planifier=lambda q, bat: planifiees.append(q), fichier_relance=Path(tmp) / "autre.json", relance=True)
        assert len(planifiees) == 1
        assert "déjà été programmée" in rapport(d) or "déjà la relance" in rapport(d)


def test_relance_non_programmable_et_nouveau_soir():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.json"
        assert "non programmée (boom)" in pc.programmer_relance(INSTANT, "2026-11-13", lambda q, b: "boom", f)
        assert not f.exists()                                                   # échec : le soir n'est pas consommé
        assert "22:30" in pc.programmer_relance(INSTANT, "2026-11-13", lambda q, b: None, f)
        assert "22:30" in pc.programmer_relance(INSTANT, "2026-11-14", lambda q, b: None, f)   # soir suivant : permis


def test_erreur_bloquante_et_crash():
    config = config_sans_images()
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        class Absent(FauxOutils):
            def sous_titres(self, vid, dossier):
                raise pc.OutilAbsent("yt-dlp introuvable")
        r = pc.lancer("daily", INSTANT, d, config, Absent({}), fichier_relance=Path(tmp) / "r.json")
        assert r["complet"] is False and any("yt-dlp introuvable" in b for b in r["bloquantes"])
        assert "Passage complet : non" in rapport(d)
        pc.signaler_crash("daily", INSTANT, RuntimeError("boom"), d)
        tete = rapport(d).split("\n")[:6]
        assert "Passage complet : non" in tete[2] and any("crash : RuntimeError : boom" in l for l in tete)


def test_scripts_windows():
    bat = (Path(__file__).resolve().parents[1] / "pc" / "installer.bat").read_text(encoding="utf-8")
    for morceau in ("git checkout -- data", "git pull origin main", "installer_taches.ps1", "ExecutionPolicy Bypass",
                    "Start-ScheduledTask", "ShadowLedger PC quotidien", "tâches créées", "prochain passage"):
        assert morceau.lower() in bat.lower(), morceau
    lanceur = (Path(__file__).resolve().parents[1] / "pc" / "lancer_pc.bat").read_text(encoding="utf-8")
    assert "%1 %2" in lanceur


def test_json_abime_nomme_le_fichier_et_ecriture_atomique():
    import subprocess
    from donnees import JsonAbime
    with tempfile.TemporaryDirectory() as tmp:
        d = Donnees(tmp)
        d.ecrire("a/b.json", {"x": 1})
        assert not list((d.data / "a").glob("*.tmp"))           # fichier temporaire remplacé, pas laissé
        (d.data / "a" / "b.json").write_text('{"x": 1,\n<<<<<<< HEAD\n"y": 2}', encoding="utf-8")
        try:
            d.lire("a/b.json", None)
            assert False
        except JsonAbime as e:
            assert "b.json" in str(e) and "conflit" in str(e) and "ligne 2" in str(e)
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        try:
            pc.Git(tmp).verifier_json()
            assert False
        except pc.GitErreur as e:
            assert "b.json" in str(e) and "rien n'est commité" in str(e)
        (d.data / "a" / "b.json").write_text('{"x": 1}', encoding="utf-8")
        pc.Git(tmp).verifier_json()                              # fichier réparé : passe


def test_git_delai_maximal():
    import time
    with tempfile.TemporaryDirectory() as tmp:
        g = pc.Git(tmp, delai_s=0.001)
        t = time.time()
        try:
            g._run("--version")
        except pc.GitErreur as e:
            assert "sans réponse" in str(e)
        assert time.time() - t < 5


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn(); print("ok", nom)
