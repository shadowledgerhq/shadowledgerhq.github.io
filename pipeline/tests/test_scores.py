import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scores import NON_GERE, chronos, extraire, nombres

from donnees import charger_config
from tri1 import lectures_texte, variante_bot

CONFIG = charger_config()  # réglages réels (v3 : plage BOT 5-180, mots d'hypothèse, semaine passée…)


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
    assert r["valeur"] == 131449789393717 and r["autres"] == ["132T"]  # v3 : premier candidat du texte
    assert extraire("HOTM 제 1관문 94,600pt 2026", "hotm", CONFIG)["valeur"] == 94600
    assert extraire("BOT 00:19.558 / 0:21", "bot", CONFIG)["valeur"] == 19.558
    assert extraire("BOT clear 3", "bot", CONFIG) is None  # hors plage / pas un chrono
    assert extraire("GB 1,234 RC", "gb", CONFIG) == NON_GERE
    assert extraire("POC 2.1B", "poc", CONFIG) is None  # hors plage plausible


# --- v3 : vrais cas du 1er passage (13/11/2026) ---------------------------------------------

def meta(titre="", modes=("poc",), vid="v1"):
    return {"video_id": vid, "channel_id": "UC1", "channel_title": "Ch", "title": titre,
            "published_at": "2026-11-13T10:00:00Z", "lang": "en", "mode_guess": list(modes)}


def test_v3_semaine_passee_et_hypothese():
    titre = "Last Week POC … 133T (Can 150T)"
    r = extraire(titre, "poc", CONFIG)
    assert r["valeur"] == 133 * 10**12 and r["semaine_passee"] is True and r["autres"] == []  # « Can 150T » exclu
    lec, _ = lectures_texte(meta(titre), [("titre", titre)], CONFIG)
    assert lec[0]["score"] == 133 * 10**12 and "semaine précédente ?" in lec[0]["notes"]
    assert extraire("POC 133T", "poc", CONFIG)["semaine_passee"] is False
    assert extraire("POC 133T 150T 가능", "poc", CONFIG)["autres"] == []                # hypothèse après (CJK)
    assert extraire("POC if 150T then 133T", "poc", CONFIG)["valeur"] == 133 * 10**12  # « if » juste avant


def test_v3_bot_millisecondes():
    assert extraire("19.558 バルカ", "bot", CONFIG)["valeur"] == 19.558
    assert extraire("23;223s", "bot", CONFIG)["valeur"] == 23.223
    assert extraire("BOT 19:558", "bot", CONFIG)["valeur"] == 19.558
    assert extraire("clear 19,558 s", "bot", CONFIG)["valeur"] == 19.558
    assert extraire("BOT 223s", "bot", CONFIG) is None          # plage BOT 5-180 s
    assert extraire("BOT 181s", "bot", CONFIG) is None and extraire("BOT 180s", "bot", CONFIG)["valeur"] == 180
    assert [c["valeur"] for c in nombres("131,449,789,393,717")] == [131449789393717]  # milliers POC intacts


def test_v3_chapitres_de_description():
    chapitres = "BOT clear\n00:00 Intro\n00:32 Boss\n01:01 Phase 2\n01:45 Fin\n03:49 Merci"
    assert extraire(chapitres, "bot", CONFIG, "description") is None
    # les mêmes lignes dans un titre ne sont pas des chapitres ; une ligne seule non plus
    assert extraire("0:19 clear", "bot", CONFIG, "description")["valeur"] == 19
    # premier candidat par source, priorité titre > description
    lec, _ = lectures_texte(meta("BOT 19.558s", ("bot",)), [("titre", "BOT 19.558s"), ("description", "20.1s\n0:30")], CONFIG)
    assert lec[0]["score"] == 19.558 and lec[0]["score_source"] == "titre" and any(n.startswith("description") for n in lec[0]["notes"])


def test_v3_variante_bot_et_porte_dapres_le_titre():
    assert variante_bot("時の戦場チャレンジ 19s", CONFIG) == "challenge"
    assert variante_bot("BOT challenge 19s", CONFIG) == "challenge"
    assert variante_bot("時の戦場 シーズン12 19s", CONFIG) == "season"
    assert variante_bot("BOT 19s", CONFIG) is None
    assert variante_bot("season challenge", CONFIG) is None   # ambigu
    lec, _ = lectures_texte(meta("BOT Challenge 19.558s", ("bot",)), [("titre", "BOT Challenge 19.558s")], CONFIG)
    assert lec[0]["bot_variant"] == "challenge"
    lec, _ = lectures_texte(meta("HOTM 第2関門 95,000pt", ("hotm",)), [("description", "第1関門 94,600pt")], CONFIG)
    assert lec[0]["gate"] == 2                                  # porte lue dans le titre, pas dans le texte du score


def test_v3_mots_cles_de_mode_en_mot_entier():
    from youtube import deviner_modes
    assert deviner_modes("my robot clear", CONFIG) == set() and deviner_modes("Bot clear", CONFIG) == {"bot"}
    assert deviner_modes("나혼렙POC 133T", CONFIG) == {"poc"}      # collé à du coréen
    assert deviner_modes("pocket guide", CONFIG) == set()


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
    print("OK")
