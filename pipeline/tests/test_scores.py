import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scores import NON_GERE, chronos, extraire, nombres

from donnees import charger_config
from bot_saison import lire_saison_semaine, titre_challenge
from tri1 import lectures_texte

CONFIG = charger_config()  # réglages réels (v3 : plage BOT 5-180, mots d'hypothèse, semaine passée…)
T = 10**12


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
    assert extraire("GB 1,234 RC", "gb", CONFIG) is None                    # v5 : GB géré (plage 1-500 RC par run)
    assert extraire("GB 165 RC", "gb", {**CONFIG, "plausible": {**CONFIG["plausible"], "gb": None}}) == NON_GERE
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
    assert extraire("POC up to 150T, 133T", "poc", CONFIG)["valeur"] == 133 * 10**12    # « up to » (spec §2.2)
    assert extraire("POC max 150T 133T", "poc", CONFIG)["autres"] == []
    assert extraire("POC ~150T", "poc", CONFIG) is None                                  # « ~ » collé au nombre
    # « semaine passée » : titre seulement
    assert extraire("last week 133T", "poc", CONFIG, "description")["semaine_passee"] is False
    assert extraire("지난주 133T", "poc", CONFIG, "titre")["semaine_passee"] is True


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
    # une ligne qui commence par un horodatage est un chapitre, même seule (spec §2.2)
    assert extraire("0:19 clear", "bot", CONFIG, "description") is None
    # au BOT, tout m:ss sans millièmes de la description est exclu ; avec millièmes ou « s » : lu
    assert extraire("clear en 0:19 !", "bot", CONFIG, "description") is None
    assert extraire("clear 0:19.558", "bot", CONFIG, "description")["valeur"] == 19.558
    assert extraire("clear 21s", "bot", CONFIG, "description")["valeur"] == 21
    # 2 horodatages croissants dans la description (hors début de ligne) : tous exclus
    assert extraire("Boss 0:20 puis fin 1:05 clear 33s", "bot", CONFIG, "description")["valeur"] == 33
    # dans le titre, un chrono m:ss reste un score
    assert extraire("BOT 0:19", "bot", CONFIG, "titre")["valeur"] == 19
    # premier candidat par source, priorité titre > description
    lec, _ = lectures_texte(meta("BOT 19.558s", ("bot",)), [("titre", "BOT 19.558s"), ("description", "20.1s\n0:30")], CONFIG)
    assert lec[0]["score"] == 19.558 and lec[0]["score_source"] == "titre" and any(n.startswith("description") for n in lec[0]["notes"])


def test_v3_challenge_et_porte_dapres_le_titre():
    assert titre_challenge("時の戦場チャレンジ 19s", CONFIG) and titre_challenge("BOT challenge 19s", CONFIG)
    assert titre_challenge("BOT 챌린지", CONFIG) and not titre_challenge("BOT 19s", CONFIG)
    lec, _ = lectures_texte(meta("BOT Challenge 19.558s", ("bot",)), [("titre", "BOT Challenge 19.558s")], CONFIG)
    assert "challenge ? (mode supprimé)" in lec[0]["notes"] and lec[0]["confidence"] == "a_verifier" and "bot_variant" not in lec[0]
    lec, _ = lectures_texte(meta("BOT 19.558s", ("bot",)), [("titre", "BOT 19.558s")], CONFIG)
    assert not any("challenge" in n for n in lec[0]["notes"])
    lec, _ = lectures_texte(meta("HOTM 第2関門 95,000pt", ("hotm",)), [("titre", "HOTM 第2関門 95,000pt")], CONFIG)
    assert lec[0]["gate"] == 2
    lec, _ = lectures_texte(meta("HOTM 95,000pt", ("hotm",)), [("titre", "HOTM 95,000pt"), ("description", "第1関門")], CONFIG)
    assert lec[0]["gate"] is None                               # porte : titre seulement


def test_v3_mots_cles_de_mode_en_mot_entier():
    from youtube import deviner_modes
    assert deviner_modes("my robot clear", CONFIG) == set() and deviner_modes("Bot clear", CONFIG) == {"bot"}
    assert deviner_modes("나혼렙POC 133T", CONFIG) == {"poc"}      # collé à du coréen
    assert deviner_modes("pocket guide", CONFIG) == set()


def test_v5_rage_count():
    for t, v in [("165 RC", 165), ("RC 167", 167), ("332RC", 332), ("Rage Count 165", 165), ("rage count: 165", 165), ("GB 165 rc", 165)]:
        assert extraire(t, "gb", CONFIG)["valeur"] == v, t
    assert extraire("RC 501", "gb", CONFIG) is None and extraire("0 RC", "gb", CONFIG) is None      # plage 1-500
    assert extraire("RC 1,234", "gb", CONFIG) is None and extraire("15 763 121 797 048 dégâts", "gb", CONFIG) is None
    assert extraire("GB 165 RC (Can 200 RC)", "gb", CONFIG)["autres"] == []                      # hypothèse exclue
    assert extraire("GB 167 RC puis 165 RC", "gb", CONFIG)["autres"] == ["165 RC"]               # premier candidat
    lec, _ = lectures_texte(meta("Giant Statue 332RC", ("gb",)), [("titre", "Giant Statue 332RC")], CONFIG)
    assert lec[0]["mode"] == "gb" and lec[0]["score"] == 332 and lec[0]["exact"] is False
    assert extraire("가나다 RC 165", "gb", {**CONFIG, "rage_count_mots": ["가나다"]})["valeur"] == 165


# --- v8 : vrais titres du 1er passage ----------------------------------------------------------

def test_v10_semaine_du_titre():
    assert lire_saison_semaine("bot S20-4 19s", CONFIG) == "S20-4" and lire_saison_semaine("BOT s20", CONFIG) is None
    assert lire_saison_semaine("BOT S20-5", CONFIG) is None and lire_saison_semaine("PS5-1 BOT", CONFIG) is None


def test_v8_degats_gb_dans_le_titre():
    titre = "64.2 T Light team (Guild boss) -  189 rc guide !!"
    lec, _ = lectures_texte(meta(titre, ("gb",), vid="awb-GlVIa7Q"), [("titre", titre)], CONFIG)
    assert lec[0]["score"] == 189 and lec[0]["damage"] == 64.2 * T and lec[0]["detail"]["damage_exact"] is False
    assert lec[0]["regles"] == CONFIG["tri1_version"]
    lec, _ = lectures_texte(meta("Guild Boss 165RC! Best F2P", ("gb",)), [("titre", "Guild Boss 165RC! Best F2P")], CONFIG)
    assert lec[0]["damage"] is None and "damage_exact" not in lec[0]["detail"]
    lec, _ = lectures_texte(meta("RC 165 (can 80T) 17.28T", ("gb",)), [("titre", "RC 165 (can 80T) 17.28T")], CONFIG)
    assert lec[0]["damage"] == 17_280_000_000_000                       # hypothèse exclue


def test_v8_alerte_publiee_juste_apres_le_reset():
    def notes(publie):
        m = {**meta("BOT 19s", ("bot",)), "published_at": publie}
        return lectures_texte(m, [("titre", "BOT 19s")], CONFIG)[0][0]["notes"]
    note = "publiée juste après le reset : semaine précédente ?"
    assert note in notes("2026-11-12T01:50:30Z") and note in notes("2026-11-12T02:59:59Z") and note in notes("2026-11-12T00:00:00Z")
    assert note not in notes("2026-11-12T03:00:00Z") and note not in notes("2026-11-12T03:07:23Z") and note not in notes("2026-11-11T23:59:00Z")
    # sans effet sur le statut
    lec = lectures_texte({**meta("BOT 19s", ("bot",)), "published_at": "2026-11-12T01:00:00Z"}, [("titre", "BOT 19s")], CONFIG)[0][0]
    assert lec["confidence"] == "a_verifier" and lec["score"] == 19


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
    print("OK")


def test_v22_rage_dans_les_titres_gb():
    cfg = {**CONFIG, "rage_count_mots": ["rage"]}
    for t in ("Guild Boss Rage: 159", "GB Rage 159 !", "159 Rage", "Rage Count 159"):
        assert extraire(t, "gb", cfg)["valeur"] == 159, t
    assert extraire("Boss Rage: 159", "gb", cfg) is None
    assert extraire("Boss Rage 159", "gb", cfg) is None
    assert extraire("Rage 1590", "gb", cfg) is None
