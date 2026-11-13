import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot_saison import attendue, controler_semaine_bot, lire_saison_semaine, position, precedente, verdict
from donnees import charger_config
from scores import extraire
from tri1 import lectures_texte

CONFIG = charger_config()
W = "2026-11-12"


def test_lecture():
    assert lire_saison_semaine("BOT S20-4 12.345s", CONFIG) == "S20-4"
    assert lire_saison_semaine("bot s20-4", CONFIG) == "S20-4"
    assert lire_saison_semaine("BOT S20-5", CONFIG) is None   # semaine hors 1-4
    assert lire_saison_semaine("XS20-4", CONFIG) is None      # mot entier
    assert lire_saison_semaine("BOT S20", CONFIG) is None


def test_cycle_4_plus_1():
    assert attendue("2026-10-22", CONFIG) == (20, 1)
    assert attendue(W, CONFIG) == (20, 4)
    assert position("2026-11-19", CONFIG)[0] == "calcul" and attendue("2026-11-19", CONFIG) is None
    assert attendue("2026-11-26", CONFIG) == (21, 1)
    assert attendue("2026-10-15", CONFIG) is None and position("2026-10-15", CONFIG)[:2] == ("calcul", 19)
    assert attendue("2026-10-08", CONFIG) == (19, 4)
    assert precedente("2026-11-26", CONFIG) == (20, 4)    # par-dessus la semaine de calcul
    assert precedente("2026-11-19", CONFIG) == (20, 4)
    assert precedente(W, CONFIG) == (20, 3)


def test_verdicts():
    assert verdict("S20-4", W, CONFIG) == "confirmee"
    assert verdict("S20-3", W, CONFIG) == "precedente"
    assert verdict("S20-2", W, CONFIG) == "incoherente"
    assert verdict("S20-4", "2026-11-26", CONFIG) == "precedente"
    assert verdict("S21-1", "2026-11-26", CONFIG) == "confirmee"
    assert verdict("S20-4", "2026-11-19", CONFIG) == "precedente"
    assert verdict("S21-1", "2026-11-19", CONFIG) == "incoherente"
    assert verdict(None, W, CONFIG) is None


def run(vid, sw, notes=None):
    return {"video_id": vid, "mode": "bot", "bot_season_week": sw, "confidence": "sur",
            "notes": list(notes or ["publiée juste après le reset : semaine précédente ?"])}


def test_controle():
    runs = [run("a", "S20-4"), run("b", "S20-3"), run("c", "S20-2"), run("d", "S20-2"), run("e", None)]
    gardees, prec, alertes = controler_semaine_bot(runs, W, CONFIG)
    assert [r["video_id"] for r in prec] == ["b"]
    a = gardees[0]
    assert "semaine confirmée (titre)" in a["notes"] and not any("reset" in n for n in a["notes"])
    c = gardees[1]
    assert c["confidence"] == "a_verifier" and "semaine du titre incohérente : S20-2" in c["notes"]
    assert len(alertes) == 1 and "S20-2" in alertes[0]
    assert gardees[-1]["confidence"] == "sur"


def test_semaine_de_calcul():
    runs = [run("a", None, []), run("b", "S20-4", []), run("c", "S21-1", [])]
    gardees, prec, alertes = controler_semaine_bot(runs, "2026-11-19", CONFIG)
    assert [r["video_id"] for r in prec] == ["b"]                      # S20-4 : semaine précédente de jeu
    assert all("semaine de calcul : run de la semaine précédente ?" in r["notes"] and r["confidence"] == "a_verifier"
               for r in gardees)
    assert any("semaine de calcul" in a for a in alertes)
    g, p, _ = controler_semaine_bot([run("x", "S20-4", [])], "2026-11-26", CONFIG)
    assert not g and len(p) == 1                                       # rejet par-dessus la semaine de calcul
    g, p, _ = controler_semaine_bot([run("y", "S21-1", [])], "2026-11-26", CONFIG)
    assert g[0]["notes"] == ["semaine confirmée (titre)"] and not p


def test_challenge_et_numero_de_saison_jamais_un_score():
    t = "BOT S20-4 19.558"
    assert extraire(t, "bot", CONFIG, "titre")["valeur"] == 19.558
    m = {"video_id": "v", "channel_id": "UC", "channel_title": "", "title": t,
         "published_at": "2026-11-12T01:30:00Z", "lang": "en", "mode_guess": ["bot"]}
    lec, _ = lectures_texte(m, [("titre", t)], CONFIG)
    assert lec[0]["bot_season_week"] == "S20-4" and lec[0]["regles"] == 10
    r = [{**lec[0], "notes": list(lec[0]["notes"]) + ["challenge ? (mode supprimé)"], "confidence": "sur"}]
    g, _, _ = controler_semaine_bot(r, W, CONFIG)
    assert g[0]["confidence"] == "a_verifier"


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
