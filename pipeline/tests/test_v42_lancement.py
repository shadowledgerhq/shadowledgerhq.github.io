"""v42 (discussion 7) : ligne « Lancement », critère de gel n° 3 (semaine vide, passage manuel), garde-fou « passage GitHub du jour »."""
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pc
import rapport_pc
from test_pc import INSTANT, SEM, VTT, FauxOutils, config_sans_images, monde

JOUR = "2026-11-13"


def bloc_pc(d):
    return rapport_pc.blocs((d.data / "runs" / SEM / "_rapport_pc.md").read_text(encoding="utf-8"))


def github_fait(d):
    meta = pc.ouvrir_semaine(d, SEM)
    meta.setdefault("passages", {})["daily"] = JOUR
    d.ecrire(f"runs/{SEM}/_meta.json", meta)


def lancer(d, tmp, instant=INSTANT, **kw):
    return pc.lancer("daily", instant, d, config_sans_images(), FauxOutils({v: VTT for v in "abcd"}),
                     fichier_relance=Path(tmp) / "r.json", fichier_report=Path(tmp) / "report.json", planifier=lambda quand, bat: None, **kw)


def test_semaine_vide_ne_compte_pas():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        d.ecrire("processed.json", {})                       # semaine sans aucune vidéo
        github_fait(d)
        lancer(d, tmp, planifie=True)
        b = bloc_pc(d)[-1]
        assert "Top 10 couvert : semaine vide" in b and "Lancement : planificateur" in b and "Critère de gel n° 3 : 0/2" in b
        lancer(d, tmp, INSTANT + timedelta(minutes=9), planifie=True)         # 2e passage planifié sur la semaine vide : toujours 0/2
        assert "Critère de gel n° 3 : 0/2" in bloc_pc(d)[-1]


def test_passage_manuel_ne_compte_pas_et_planifie_compte():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        github_fait(d)
        lancer(d, tmp)                                       # lancé à la main (3_passage_complet.bat)
        b = bloc_pc(d)[-1]
        assert "Lancement : manuel" in b and "Critère de gel n° 3 : 0/2" in b
        assert pc.lancement_du_passage(False, True) == "planificateur" and pc.lancement_du_passage(True, True) == "relance"
        assert pc.lancement_du_passage(False, True, {"vid"}) == "manuel"
        lancer(d, tmp, INSTANT + timedelta(minutes=9), planifie=True)
        assert "Lancement : planificateur" in bloc_pc(d)[-1]


def test_passage_github_absent_reporte_puis_abandonne_apres_2_relances():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)                                       # aucun passage GitHub du jour dans _meta.json
        planifiees = []
        for i in range(3):
            r = pc.lancer("daily", INSTANT + timedelta(minutes=30 * i), d, config_sans_images(), FauxOutils({v: VTT for v in "abcd"}),
                          planifie=(i == 0), relance=(i > 0), fichier_report=Path(tmp) / "report.json",
                          planifier=lambda quand, bat: planifiees.append(quand))
            assert r.get("reporte") and r["traitees"] == 0
        b = bloc_pc(d)
        assert "Passage reporté : passage GitHub du jour absent" in b[0] and "Lancement : planificateur" in b[0]
        assert "Relance automatique : 13/11/2026 21:00" in b[0]
        assert len(planifiees) == 2 and "aucune (2 relances" in b[2]
        assert all(p["status"] == "en_cours" for p in d.processed().values())       # rien n'a été traité
        # un passage manuel n'est pas bloqué
        assert not lancer(d, tmp, INSTANT + timedelta(hours=3)).get("reporte")
