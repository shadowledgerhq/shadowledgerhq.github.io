import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scores import NON_GERE, chronos, extraire, nombres

CONFIG = {"plausible": {"poc": [1e12, 1e16], "hotm": [1000, 200000], "bot": [5, 600], "gb": None}}


def vals(texte):
    return [(c["valeur"], c["arrondi"]) for c in nombres(texte)]


def test_milliers():
    for t in ["131,449,789,393,717", "131 449 789 393 717", "131 449 789 393 717",
              "131 449 789 393 717", "131 449 789 393 717",
              "131.449.789.393.717"]:
        assert vals(t) == [(131449789393717, False)], t


def test_suffixes_latins():
    assert vals("2.1B") == [(2100000000, True)]
    assert vals("2,1B") == [(2100000000, True)]
    assert vals("Same strat get 132T") == [(132 * 10**12, True)]
    assert vals("132t") == [(132 * 10**12, True)]
    assert vals("1.5bn dmg") == [(1500000000, True)]
    assert vals("94.6K") == [(94600, True)]
    assert vals("3 times") == [(3, False)]


def test_coreen_japonais():
    assert vals("131조 4497억") == [(131 * 10**12 + 4497 * 10**8, True)]
    assert vals("1억 2345만 6789") == [(123456789, True)]
    assert vals("131兆4497億") == [(131 * 10**12 + 4497 * 10**8, True)]
    assert vals("5000万") == [(5 * 10**7, True)]
    assert vals("1.5억") == [(150000000, True)]


def test_points():
    assert vals("94,600pt") == [(94600, False)]
    assert vals("94600 points") == [(94600, False)]


def test_decimal_vs_milliers():
    assert vals("2,100") == [(2100, False)]
    assert vals("2,10") == [(2.1, False)]


def test_ignores():
    assert vals("2026-11-13") == []
    assert vals("13/11/2026") == []
    assert vals("13.11.2026") == []
    assert vals("2026년 11월 13일") == []
    assert vals("Nov 13, 2026") == []
    assert vals("season 2026") == []
    assert vals("Lv.170") == []
    assert vals("niv. 100") == []
    assert vals("CP 13,879,026") == []
    assert vals("전투력 13,879,026") == []
    assert vals("戦闘力 3,405,259") == []
    assert vals("13,879,026 power") == []
    assert vals("v1 POC 131,449,789,393,717 CP 13,879,026") == [(131449789393717, False)]
    assert vals("제 3관문") == []
    assert vals("第3関門") == []
    assert vals("gate 3") == []
    assert vals("4K 60fps 1080p") == []
    assert vals("clear 03:00") == []  # durée hors BOT
    assert vals("in 19s") == []


def test_chronos():
    assert [c["valeur"] for c in chronos("00:19.558")] == [19.558]
    assert [c["valeur"] for c in chronos("0:19")] == [19.0]
    assert [c["valeur"] for c in chronos("19.558s")] == [19.558]
    assert [c["valeur"] for c in chronos("19초")] == [19.0]
    assert [c["valeur"] for c in chronos("19秒")] == [19.0]
    assert [c["valeur"] for c in chronos("1:02.5")] == [62.5]
    assert chronos("00:19.558")[0]["arrondi"] is False
    assert chronos("0:19")[0]["arrondi"] is True
    assert chronos("2026-11-13") == []


def test_extraire():
    r = extraire("POC 131,449,789,393,717 (prev 132T) CP 13,879,026 Lv.170", "poc", CONFIG)
    assert r["valeur"] == 132 * 10**12 and r["autres"] == ["131,449,789,393,717"]
    assert extraire("HOTM 제 1관문 94,600pt 2026", "hotm", CONFIG)["valeur"] == 94600
    assert extraire("BOT 00:19.558 / 0:21", "bot", CONFIG)["valeur"] == 19.558
    assert extraire("BOT clear 3", "bot", CONFIG) is None  # hors plage / pas un chrono
    assert extraire("GB 1,234 RC", "gb", CONFIG) == NON_GERE
    assert extraire("POC 2.1B", "poc", CONFIG) is None  # hors plage plausible


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
    print("OK")
