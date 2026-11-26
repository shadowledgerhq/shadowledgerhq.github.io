"""v43 : passage GitHub de midi (12:00-15:59 Paris) ; il ne marque pas passages.daily (garde-fou du PC)."""
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import etape1
from donnees import Donnees, charger_config
from semaine import PARIS


def _lancer(instant, **kw):
    os.environ.pop("YOUTUBE_API_KEY", None)
    tmp = tempfile.mkdtemp()
    try:
        d = Donnees(tmp)
        etape1.lancer("midi", instant, d=d, config=charger_config(), **kw)
        sem = etape1.id_semaine(instant)
        return d.meta(sem)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_midi_dans_creneau_ne_marque_pas_daily():
    meta = _lancer(datetime(2026, 11, 27, 12, 5, tzinfo=PARIS))
    assert meta["passages"] == {"midi": "2026-11-27"}


def test_midi_hors_creneau_ne_fait_rien():
    assert not _lancer(datetime(2026, 11, 27, 19, 5, tzinfo=PARIS))


if __name__ == "__main__":
    test_midi_dans_creneau_ne_marque_pas_daily()
    test_midi_hors_creneau_ne_fait_rien()
    print("OK")
