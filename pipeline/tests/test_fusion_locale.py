import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fusion_locale as F


def test_processed_garde_le_plus_avance():
    base = {"a": {"status": "en_cours", "pc": {}}, "b": {"status": "termine", "pc": {"tri4": "fait"}}}
    loc = {"a": {"status": "en_cours", "pc": {"tri3": "fait", "tri4": "fait"}}, "b": {"status": "en_cours", "pc": {}}, "c": {"status": "en_cours"}}
    fus, ajout, rempl = F.fusionner_processed(base, loc)
    assert (ajout, rempl) == (1, 1) and fus["a"]["pc"]["tri4"] == "fait" and fus["b"]["status"] == "termine" and "c" in fus


def test_lectures_sans_doublon():
    l1 = {"video_id": "a", "mode": "poc", "score": 1.0, "score_source": "titre"}
    l2 = {"video_id": "a", "mode": "poc", "score": 2.0, "score_source": "ocr", "t": 5}
    res, n = F.fusionner_lectures_locales([l1], [dict(l1), l2])
    assert n == 1 and res == [l1, l2]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn(); print("ok", nom)
