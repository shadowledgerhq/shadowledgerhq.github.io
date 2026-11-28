"""« 19R 35.4% » = palier 19 à 35,4 % (Pj6QzXQ81jQ)."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import poc_palier as P

TITRE = "PoC 19R 35.4% / Ennio(no OL 15,17,19R) / Fire + Water / 권좌(엔니오 오버로드x 15,17,19라운드) 19라운드 35.4퍼"


def test_ronde_pourcent():
    m = [(int(a), float(b)) for a, b in P._RONDE_POURCENT.findall(TITRE)]
    assert (19, 35.4) in m
    assert round(P.UNITE_RANK_SCORE * (19 - 1 + 35.4 / 100)) == 18_354_000


if __name__ == "__main__":
    test_ronde_pourcent(); print("OK")
