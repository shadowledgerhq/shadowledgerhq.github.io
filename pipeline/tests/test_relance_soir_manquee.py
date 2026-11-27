"""BOITE 27/11 (Tâche planifiée) : la relance du weekly (nuit) ne compte pas dans la limite du soir ; une relance lancée > 2 h après son heure est annulée."""
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pc
import rapport_pc
from donnees import Donnees
from semaine import PARIS
from test_pc import INSTANT, SEM, VTT, FauxOutils, config_sans_images, monde
from test_v42_lancement import JOUR, github_fait


def test_relance_de_nuit_ne_bloque_pas_la_relance_du_soir():
    nuit = datetime(2026, 11, 13, 1, 15, tzinfo=PARIS)
    soir = datetime(2026, 11, 13, 21, 15, tzinfo=PARIS)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.json"
        assert "03:15" in pc.programmer_relance(nuit, JOUR, lambda q, b: None, f)
        assert "23:15" in pc.programmer_relance(soir, JOUR, lambda q, b: None, f)           # avant : « déjà programmée »
        assert "déjà été programmée" in pc.programmer_relance(soir, JOUR, lambda q, b: None, f)


def test_relance_manquee_fonction():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.json"
        f.write_text(json.dumps({"a": "2026-11-13T23:30:00"}), encoding="utf-8")
        assert pc.relance_manquee(datetime(2026, 11, 13, 23, 45, tzinfo=PARIS), [f]) is None
        assert "plus de 2 h" in pc.relance_manquee(datetime(2026, 11, 14, 2, 31, tzinfo=PARIS), [f])
        assert pc.relance_manquee(datetime(2026, 11, 13, 23, 0, tzinfo=PARIS), [f]) is None          # heure pas encore arrivée
        assert pc.relance_manquee(INSTANT, [Path(tmp) / "absent.json"]) is None                        # inconnue : jamais d'annulation


def test_relance_manquee_aucun_traitement_et_bloc():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        github_fait(d)
        (Path(tmp) / "report.json").write_text(json.dumps({"jour": JOUR, "n": 1, "a": (INSTANT - timedelta(hours=3)).replace(tzinfo=None).isoformat()}), encoding="utf-8")
        r = pc.lancer("daily", INSTANT, d, config_sans_images(), FauxOutils({v: VTT for v in "abcd"}), relance=True,
                      fichier_relance=Path(tmp) / "r.json", fichier_report=Path(tmp) / "report.json", planifier=lambda q, b: None)
        assert r["traitees"] == 0
        texte = (d.data / "runs" / SEM / "_rapport_pc.md").read_text(encoding="utf-8")
        assert "Relance annulée : heure manquée" in texte
