import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot_saison import attendue, controler_semaine_bot, lire_saison_semaine, verdict
from donnees import charger_config
from scores import extraire
from tri1 import lectures_texte

CONFIG = charger_config()
W = "2026-11-12"


def test_lecture():
    assert lire_saison_semaine("BOT S20-4 12.345s") == "S20-4"
    assert lire_saison_semaine("bot s20-4") == "S20-4"
    assert lire_saison_semaine("BOT S20-9") is None      # semaine hors 1-7
    assert lire_saison_semaine("XS20-4") is None         # mot entier
    assert lire_saison_semaine("BOT S20") is None


def test_attendue_et_enchainement():
    assert attendue(W, CONFIG) == (20, 4)
    assert attendue("2026-11-19", CONFIG) == (20, 5)
    assert attendue("2026-12-03", CONFIG) == (20, 7)
    assert attendue("2026-12-10", CONFIG) == (21, 1)     # saisons enchaînées
    assert attendue("2026-11-05", CONFIG) == (20, 3)
    assert attendue("2026-10-15", CONFIG) == (19, 7)


def test_verdicts():
    assert verdict("S20-4", W, CONFIG) == "confirmee"
    assert verdict("S20-3", W, CONFIG) == "precedente"
    assert verdict("S19-7", "2026-10-15", CONFIG) == "confirmee"
    assert verdict("S20-6", W, CONFIG) == "incoherente"
    assert verdict(None, W, CONFIG) is None


def run(vid, sw, notes=None):
    return {"video_id": vid, "mode": "bot", "bot_season_week": sw, "confidence": "sur",
            "notes": list(notes or ["publiée juste après le reset : semaine précédente ?"])}


def test_controle():
    runs = [run("a", "S20-4"), run("b", "S20-3"), run("c", "S20-6"), run("d", "S20-6"), run("e", None)]
    gardees, prec, alertes = controler_semaine_bot(runs, W, CONFIG)
    assert [r["video_id"] for r in prec] == ["b"]
    a = gardees[0]
    assert "semaine confirmée (titre)" in a["notes"] and not any("reset" in n for n in a["notes"])
    c = gardees[1]
    assert c["confidence"] == "a_verifier" and "semaine du titre incohérente : S20-6" in c["notes"]
    assert len(alertes) == 1 and "S20-6" in alertes[0]
    assert gardees[-1]["confidence"] == "sur"   # sans titre lisible : rien ne change


def test_numero_de_saison_jamais_un_score():
    t = "BOT S20-4 19.558"
    r = extraire(t, "bot", CONFIG, "titre")
    assert r["valeur"] == 19.558
    m = {"video_id": "v", "channel_id": "UC", "channel_title": "", "title": t,
         "published_at": "2026-11-12T01:30:00Z", "lang": "en", "mode_guess": ["bot"]}
    lec, _ = lectures_texte(m, [("titre", t)], CONFIG)
    assert lec[0]["bot_season_week"] == "S20-4" and lec[0]["regles"] == 9


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
