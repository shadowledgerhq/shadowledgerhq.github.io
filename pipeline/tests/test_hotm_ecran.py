import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hotm_ecran import hotm_champs_ecran, lire_mode, lire_porte


def test_coreen():
    assert lire_mode("플레이어 모드") is False
    assert lire_porte("제 1관문 94 600pt") == {"number": 1, "points": 94600}


def test_japonais():
    assert lire_mode("ハンターモード") is True
    assert lire_porte("第2関門 95 000pt") == {"number": 2, "points": 95000}
    assert lire_porte("第2関門\n95,000 PT") == {"number": 2, "points": 95000}


def test_illisible_et_contradictoire():
    assert lire_mode("bruit") is None
    assert lire_mode("플레이어 모드 ハンターモード") is None
    assert lire_porte("bruit 94 600pt") is None
    assert lire_porte("제 3관문") == {"number": 3, "points": None}


def test_champs_et_alertes():
    ch, al = hotm_champs_ecran("플레이어 모드", "제 1관문 94 600pt", 94600)
    assert ch == {"gate": {"number": 1, "points": 94600}, "hunter_mode": False} and not al
    _, al = hotm_champs_ecran("", "제 1관문 94 600pt", 90000)
    assert len(al) == 2


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
