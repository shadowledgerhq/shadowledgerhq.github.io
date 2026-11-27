"""Theorycraft (BOITE §8, 27/11) : Results BOT à 2 phases (YSJFLd_OXww : 9.373 / 14.515, dernier t_game 18.433, score de la ligne 19.517).
Le chrono de contrôle est le score de la ligne, jamais la dernière phase lue ; le rapport signale « phases incomplètes »."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rotation


def _fich():
    ev = [{"hunter": "sjw", "slot": "x", "t": 5 + i, "t_game": 2.912 + i * 2.58} for i in range(7)]
    return {"runs": [{"events": ev, "duration_s": 34.5, "run_end_t": 38.0}]}


def _crit6(ctrl):
    return [c for c in ctrl if c[0].startswith("t_game")][0]


def test_deux_phases_chrono_de_la_ligne_pas_d_echec():
    f = _fich()
    nom, ok, detail = _crit6(rotation.controles_bot(f, 19.517, None, [9.373, 14.515]))
    assert ok is True
    assert "phases incomplètes (2 lue(s) sur 3)" in detail


def test_trois_phases_pas_de_mention():
    _, ok, detail = _crit6(rotation.controles_bot(_fich(), 19.517, None, [9.373, 14.515, 19.517]))
    assert ok is True and "incomplètes" not in detail
