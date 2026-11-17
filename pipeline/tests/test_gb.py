import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecrans
import gb
from classement import calculer
from donnees import charger_config
from test_classement import HORLOGE, W, lec, lire, preparer

CONFIG = charger_config()
T = 10**12


def meta(vid, jour=14, heure=10, titre="Giant Statue GB"):
    return {"video_id": vid, "channel_id": "UCX", "channel_title": "Joueur X", "title": titre,
            "published_at": f"2026-11-{jour:02d}T{heure:02d}:00:00Z", "lang": "en", "mode_guess": ["gb"]}


RECORD = {"stage": "Giant Statue", "t": 5, "groups": {1: {"rage_count": 167, "damage": "17.28T"}, 2: {"rage_count": 165, "damage": "15.55T"}},
          "total_rage_count": 332, "total_score": 32_842_054_460_310, "challenge_count": 12, "time_left": "6d 9h"}
RESULTS = {"stage": "Giant Statue", "t": 40, "rage_count": 165, "final_score": 15_763_121_797_048, "player_score": 3_763_121_797_048,
           "hunter_ranks": [2 * T] * 6, "play_time": "03:00", "new_record": True}


def test_v30_personal_record_ne_classe_aucune_run():
    """SPEC v30 §4.7 : Personal Record 167 + 165 dans v1 (sans Results) : aucune run classée ; un Results de RC 165 dans une AUTRE
    vidéo n'est pas rattaché au record : classé seul (165), jamais 332."""
    rec = ecrans.lectures_gb_record(meta("v1", heure=10), RECORD, CONFIG)
    assert [(r["team"], r["score"], r["confidence"], r["exact"]) for r in rec] == [(1, 167, "sur", True), (2, 165, "sur", True)]
    res = ecrans.lecture_gb_results(meta("v2", heure=12), RESULTS, CONFIG)
    assert res["confidence"] == "sur" and res["exact"] and res["damage"] == 15_763_121_797_048 and res["team"] is None
    d = preparer(rec + [res])
    r = calculer(W, d, CONFIG, HORLOGE)
    gb_l = lire(d, "gb")
    assert len(gb_l) == 1
    l = gb_l[0]
    assert l["score"] == {"total": 165, "runs": [165], "unit": "rage_count"}
    assert l["confidence"] == "sur" and l["rank"] == 1 and l["video_ids"] == ["v2"] and l["runs_detail"][0]["team"] is None
    assert r["records_seuls"] == ["v1 : Personal Record seul : aucune run filmée"]

def test_results_de_meme_rc_qu_un_seul_groupe_du_record_recoit_ce_groupe():
    """v30 §4.7 (2a) : même vidéo, RC du Results égal au RC d'un seul groupe du record -> `team` attribué ; total = ce Results seul."""
    res = ecrans.lecture_gb_results(meta("v1", heure=12), RESULTS, CONFIG)                    # RC 165 = groupe 2
    d = preparer(ecrans.lectures_gb_record(meta("v1"), RECORD, CONFIG) + [res])
    r = calculer(W, d, CONFIG, HORLOGE)
    l = lire(d, "gb")[0]
    assert l["score"]["total"] == 165 and l["score"]["runs"] == [165] and l["runs_detail"][0]["team"] == 2
    assert "groupe 2 d'après le Personal Record (RC égal)" in l["notes"] and r["records_seuls"] == []
    # RC égal aux DEUX groupes : ambigu, pas d'attribution
    egal = {**RECORD, "groups": {1: {"rage_count": 165, "damage": "17.28T"}, 2: {"rage_count": 165, "damage": "15.55T"}}, "total_rage_count": 330}
    d = preparer(ecrans.lectures_gb_record(meta("v1"), egal, CONFIG) + [res])
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "gb")[0]["runs_detail"][0]["team"] is None
    # RC différent des deux groupes : pas d'attribution
    d = preparer(ecrans.lectures_gb_record(meta("v1"), RECORD, CONFIG) + [ecrans.lecture_gb_results(meta("v1", heure=12), {**RESULTS, "rage_count": 170}, CONFIG)])
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "gb")[0]["runs_detail"][0]["team"] is None

def test_controle_total_rage_count():
    rec = ecrans.lectures_gb_record(meta("v1"), {**RECORD, "total_rage_count": 333}, CONFIG)
    assert all(r["confidence"] == "a_verifier" and not r["exact"] for r in rec)
    d = preparer(rec)
    res = calculer(W, d, CONFIG, HORLOGE)
    assert not (d.data / "runs" / W / "gb.json").exists() and res["records_seuls"]      # v30 : le Personal Record ne classe rien
    assert ecrans.lectures_gb_record(meta("v1"), {**RECORD, "total_rage_count": None}, CONFIG)[0]["confidence"] == "a_verifier"   # illisible

def test_saison_du_record():
    # Time Left 1d 2h : capture estimée le 17/11 22:00Z, après la publication du 13/11 : saison précédente -> rejeté
    rec = ecrans.lectures_gb_record(meta("v1", jour=13, heure=0), {**RECORD, "time_left": "1d 2h"}, CONFIG)
    d = preparer(rec)
    calculer(W, d, CONFIG, HORLOGE)
    assert not (d.data / "runs" / W / "gb.json").exists()
    assert [(r["video_id"], r["reason"]) for r in d.rejected(W)] == [("v1", "semaine_precedente")]
    # temps restant illisible -> a_verifier, pas rejeté
    d = preparer(ecrans.lectures_gb_record(meta("v1"), {**RECORD, "time_left": None}, CONFIG))
    calculer(W, d, CONFIG, HORLOGE)
    assert not (d.data / "runs" / W / "gb.json").exists() and d.rejected(W) == []       # v30 : jamais classé, mais pas rejeté
    # v7 : marge selon la plus petite unité affichée (reset 19/11 00:00Z ; publié 14/11 00:00Z)
    def garde(time_left, jour=14, heure=0):
        d = preparer(ecrans.lectures_gb_record(meta("v1", jour=jour, heure=heure), {**RECORD, "time_left": time_left}, CONFIG))
        calculer(W, d, CONFIG, HORLOGE)
        return d.rejected(W) == []          # v30 : le Personal Record ne classe plus ; « gardé » = pas rejeté (bonne saison)
    assert garde("4d 23h") and not garde("4d 22h")                        # heures : 60 min (capture à +60 min gardée, +120 min rejetée)
    assert garde("4d 23h 59m") and not garde("4d 23h 58m")                # minutes : 1 min
    assert garde("5d", jour=13, heure=12) and not garde("5d", jour=12, heure=20)   # jours seulement : 24 h (capture à +12 h gardée, +28 h rejetée)
    assert gb.plus_petite_unite("6d 9h") == "h" and gb.plus_petite_unite("6d") == "d" and gb.plus_petite_unite("6d 9h 20m") == "m"
    assert gb.plus_petite_unite("") is None and gb.plus_petite_unite("bruit") is None
    assert gb.tolerances({"record_tolerance_minutes": 90}) == {"d": 1440, "h": 90, "m": 1}


def test_v7_damage_exact_null_sans_degats():
    d = preparer([lec("g1", "UCG", "gb", 167, team=1), lec("g2", "UCG", "gb", 165, team=2, damage=15 * T)])
    calculer(W, d, CONFIG, HORLOGE)
    r1, r2 = lire(d, "gb")[0]["runs_detail"]
    assert r1["damage"] is None and r1["damage_exact"] is None            # pas de dégâts lus -> null
    assert r2["damage"] == 15 * T and r2["damage_exact"] is True


def test_v7_mot_cle_gb():
    from youtube import deviner_modes
    for ok in ("GB 165 RC", "Giant Statue GB", "(GB) clear", "GB: 332RC", "Guild Boss"):
        assert deviner_modes(ok, CONFIG) == {"gb"}, ok
    for ko in ("12GB", "128 GB RAM", "8\u00a0GB", "gba", "gbp"):
        assert deviner_modes(ko, CONFIG) == set(), ko


def test_gb_egalite_departagee_par_les_degats():
    lectures = [lec("a1", "UCA", "gb", 167, team=1, damage=17 * T), lec("a2", "UCA", "gb", 165, team=2, damage=15 * T),
                lec("b1", "UCB", "gb", 167, team=1, damage=18 * T), lec("b2", "UCB", "gb", 165, team=2, damage=16 * T, jour=12),
                lec("c1", "UCC", "gb", 170, team=1, damage=1 * T), lec("c2", "UCC", "gb", 170, team=2, damage=1 * T)]
    d = preparer(lectures)
    calculer(W, d, CONFIG, HORLOGE)
    assert [(l["channel_id"], l["score"]["total"], l["rank"]) for l in lire(d, "gb")] == [("UCC", 340, 1), ("UCB", 332, 2), ("UCA", 332, 3)]
    # égalité de RC et de dégâts : published_at le plus récent le plus tôt (§4.2) ; `_degats` n'est jamais écrit
    assert all("_degats" not in l for l in lire(d, "gb"))


def test_gb_meme_groupe_jamais_additionne_et_groupe_illisible():
    d = preparer([lec("a1", "UCA", "gb", 167, team=1, damage=17 * T), lec("a2", "UCA", "gb", 160, team=1, damage=16 * T)])
    calculer(W, d, CONFIG, HORLOGE)
    l = lire(d, "gb")[0]
    assert l["score"]["total"] == 167 and l["rank"] == 1 and "une seule run" in l["notes"]       # v16 : classée (même groupe jamais additionné)
    d = preparer([lec("b1", "UCB", "gb", 167, damage=17 * T), lec("b2", "UCB", "gb", 165, damage=15 * T)])
    calculer(W, d, CONFIG, HORLOGE)
    l = lire(d, "gb")[0]
    assert l["score"]["total"] == 167 and l["rank"] == 1 and "groupes inconnus : 2e run non additionnée (165, b2)" in l["notes"]   # v18


def test_total_score_du_record_ne_sert_plus_au_classement():
    a = ecrans.lectures_gb_record(meta("v1"), {**RECORD, "total_score": 33 * T}, CONFIG)
    d = preparer(a)
    calculer(W, d, CONFIG, HORLOGE)
    assert not (d.data / "runs" / W / "gb.json").exists()

def test_controle_results_gb():
    ok, pb = ecrans.controle_gb_results(3 * T, [T] * 6, 9 * T)
    assert ok and not pb
    ok, pb = ecrans.controle_gb_results(3 * T, [T] * 6, 9 * T + 1)
    assert not ok and "≠ Final Score" in pb[0]
    bad = ecrans.lecture_gb_results(meta("v2"), {**RESULTS, "final_score": 1}, CONFIG)
    assert bad["confidence"] == "a_verifier" and bad["score"] == 165
    part = ecrans.lecture_gb_results(meta("v2"), {**RESULTS, "rage_count": None}, CONFIG)
    assert part["score"] is None and part["detail"]["ecran"] == "results_partiel"      # v12 : lecture partielle, jamais classée


# --- BOT (v4-v5) ------------------------------------------------------------------------------

BOT = {"stage": "Baruka", "phases": [9.281, 14.986, 19.926], "chrono": 19.926, "play_time": 19, "player_ingame": "ThenaX", "armes_sjw": True, "t": 30}


def test_bot_results_controles_et_challenge():
    m = {**meta("b1", titre="BOT S20-4 19.926"), "mode_guess": ["bot"]}
    lecture = ecrans.lecture_bot(m, BOT, CONFIG)
    assert lecture["score"] == 19.926 and lecture["confidence"] == "sur" and lecture["exact"] and lecture["player_ingame"] == "ThenaX"
    assert lecture["bot_season_week"] == "S20-4" and "bot_variant" not in lecture   # v10 : plus de variante
    ch = ecrans.lecture_bot({**m, "title": "BOT challenge"}, BOT, CONFIG)
    assert "challenge ? (mode supprimé)" in ch["notes"]
    for mauvais in ({**BOT, "play_time": 20}, {**BOT, "chrono": 19.9}, {**BOT, "phases": [9.281, 9.281, 19.926]}, {**BOT, "play_time": None}):
        assert ecrans.lecture_bot(m, mauvais, CONFIG)["confidence"] == "a_verifier"
    d = preparer([{**lecture, "published_at": "2026-11-14T10:00:00Z"}])
    calculer(W, d, CONFIG, HORLOGE)
    l = lire(d, "bot")[0]
    assert l["player_ingame"] == "ThenaX" and l["rank"] == 1 and l["score"]["total"] == 19.926


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn(); print("ok", nom)
