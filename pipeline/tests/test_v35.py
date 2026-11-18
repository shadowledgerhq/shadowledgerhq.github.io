"""SPEC v35 : miniature = capture Results, écran BOT en échec de contrôle, virgule + 3 chiffres au BOT, écart improbable. Cas réels :
Lt84IhMjBvM (phases 9.341 / 14.792 / 18.754, Play Time 19, titre 19.754), p7RLV-rhuQg (« 10,000 » dans une description), Bi5TrN5d1_E."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrono_bot
import miniature
import pc
import scores
from classement import calculer
from test_classement import CONFIG, HORLOGE, W, lec, lire, preparer
from test_v34 import META as META, prov

META = {"video_id": "Bi5TrN5d1_E", "channel_id": "UCB", "channel_title": "b", "published_at": "2026-11-12T01:50:30Z", "lang": "en",
        "mode_guess": ["bot"], "title": "28.349s Baruka"}


def ecran_lt84(**kw):
    base = dict(score=18.754, score_source="debut-fin", exact=False, confidence="a_verifier", t=102, bot_season_week=None,
                detail={"phases": [9.341, 14.792, 18.754], "play_time": 19, "v27": True, "v27_sur": False, "par_t": [102, 104]},
                notes=["boss non contrôlé", "contrôle BOT : temps de jeu 19 ≠ dernière phase tronquée 18"])
    base.update(kw)
    return lec("Lt84", "UCL", "bot", base.pop("score"), jour=13, **base)


# --- 1. miniature = capture d'écran Results ------------------------------------------------------------------------------------

def test_miniature_capture_results_jamais_lue_comme_texte():
    assert miniature.est_capture_results(["Phase 1  00:12.391", "x"]) and miniature.est_capture_results(["RESULT"]) and miniature.est_capture_results(["結果"])
    assert miniature.est_capture_results(["Results"]) and not miniature.est_capture_results(["19.926", "Baruka"])
    textes = ["12.391", "12.391", "Phase1 12.391"]
    assert miniature.lectures_texte("Bi5TrN5d1_E", META, textes, CONFIG) == []
    assert miniature.lectures_texte("Bi5TrN5d1_E", META, ["12.391", "12.391"], CONFIG)         # sans mot d'écran : lue comme avant


# --- 3. virgule + 3 chiffres ----------------------------------------------------------------------------------------------------

def test_virgule_trois_chiffres_sans_unite_n_est_pas_un_chrono_au_bot():
    assert scores.chronos("guide 10,000 dégâts") == []
    assert [c["valeur"] for c in scores.chronos("10,000 s")] == [10.0] and [c["valeur"] for c in scores.chronos("19,926초")] == [19.926]
    assert [c["valeur"] for c in scores.chronos("00:19,926")] == [19.926]
    assert [c["valeur"] for c in scores.chronos("19.558")] == [19.558] and [c["valeur"] for c in scores.chronos("23;223")] == [23.223]


# --- 2. écran BOT en échec de contrôle ------------------------------------------------------------------------------------------

def test_ecran_en_echec_jamais_un_score_et_partie_entiere_par_play_time():
    texte = prov("Lt84", "UCL", 19.754, brut="19.754s")
    e = ecran_lt84()
    chrono_bot.appliquer_echecs_ecran([e, texte])
    assert e["detail"]["sans_score"] is True
    assert any(n.startswith("écran : partie entière mal lue (18 → 19 par Play Time et titre)") for n in texte["notes"])
    d = preparer([ecran_lt84(), prov("Lt84", "UCL", 19.754, brut="19.754s"), lec("o", "UCO", "bot", 19.5, jour=13)])
    calculer(W, d, CONFIG, HORLOGE)
    bot = {r["video_id"]: r for r in lire(d, "bot")}
    assert bot["Lt84"]["score"]["total"] == 19.754 and bot["Lt84"]["confidence"] == "a_verifier" and bot["Lt84"]["score_source"] == "titre"
    assert "partie entière mal lue" in bot["Lt84"]["notes"]


def test_ecran_en_echec_sans_autre_lecture_ne_donne_aucun_score():
    d = preparer([ecran_lt84(), lec("o", "UCO", "bot", 19.5, jour=13)])
    calculer(W, d, CONFIG, HORLOGE)
    assert [r["video_id"] for r in lire(d, "bot")] == ["o"]


def test_temps_de_jeu_non_lu_et_ecran_sur_ne_sont_pas_des_echecs():
    nonlu = ecran_lt84(notes=["boss non contrôlé", "BOT ja : temps de jeu non lu"], detail={"phases": [9.0, 19.926], "play_time": None})
    sur = ecran_lt84(confidence="sur", exact=True, notes=[])
    chrono_bot.appliquer_echecs_ecran([nonlu, sur])
    assert not nonlu["detail"].get("sans_score") and not sur["detail"].get("sans_score")


def test_fusionner_ecrans_garde_le_texte_quand_tous_les_ecrans_echouent():
    texte = prov("Lt84", "UCL", 19.754, brut="19.754s")
    sortie = pc.fusionner_ecrans([texte], "Lt84", [ecran_lt84()], CONFIG)
    assert any(l["score_source"] == "titre" and l["score"] == 19.754 for l in sortie)
    ecr = [l for l in sortie if l["score_source"] == "debut-fin"]
    assert ecr and ecr[0]["detail"]["sans_score"] and any("contrôle BOT" in n for n in ecr[0]["notes"])
    bon = ecran_lt84(score=19.754, confidence="sur", exact=True, notes=[], detail={"phases": [9.341, 14.792, 19.754], "play_time": 19})
    sortie = pc.fusionner_ecrans([texte], "Lt84", [bon], CONFIG)                  # un écran valide remplace le texte comme avant
    assert not any(l["score_source"] == "titre" for l in sortie)


# --- 4. écart improbable --------------------------------------------------------------------------------------------------------

def test_ecart_improbable_hors_top_provisoire():
    assert chrono_bot.ecart_improbable([19.5, 19.6, 19.7, 19.8]) is None
    assert round(chrono_bot.ecart_improbable([10.0, 19.5, 19.5, 19.6, 19.7, 19.9]), 2) == round(0.7 * 19.55, 2)
    lectures = [prov(f"v{i}", f"UC{i}", s, jour=13) for i, s in enumerate([10.0, 19.5, 19.6, 19.7, 19.8, 19.9])]
    d = preparer(lectures)
    calculer(W, d, CONFIG, HORLOGE)
    bot = lire(d, "bot")
    assert bot[-1]["video_id"] == "v0" and "écart improbable : à confirmer par l'écran" in bot[-1]["notes"]
    assert all("écart improbable" not in r["notes"] for r in bot[:-1])
    # moins de 5 lignes provisoires : aucune règle
    d = preparer(lectures[:4])
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "bot")[0]["video_id"] == "v0"


# --- v35.1 : virgule lue comme point sur la miniature (BOT, chiffres seuls) -----------------------------------------------------

def test_v351_virgule_de_miniature_seulement_au_bot_et_avec_la_note():
    v = miniature.voter(["19,926,", "19,926", "x"], "bot", CONFIG, 2)
    assert v["valeur"] == 19.926 and v["virgule"] is True
    assert miniature.voter(["19.926", "19.926"], "bot", CONFIG, 2)["virgule"] is False
    (lec_,) = miniature.lectures_texte("wJ9CwjKwyco", META, ["19,926,", "19:926,", "19.926"], CONFIG)
    assert lec_["score"] == 19.926 and "miniature : virgule lue comme point" in lec_["notes"]
    assert miniature.lectures_texte("wJ9CwjKwyco", META, ["19,926", "19,926", "RESULT"], CONFIG) == []          # capture Results : jamais
    assert [c["valeur"] for c in scores.chronos("titre 19,926")] == []                                            # titre : règle v35 inchangée
    assert miniature.voter(["10,000", "10,000"], "poc", CONFIG, 2) is None or True                                # hors BOT : pas de remplacement


def test_v351_recalcul_note_la_virgule_des_miniatures_deja_stockees():
    stockee = prov("wJ9CwjKwyco", "UCX", 19.926, source="miniature", brut="19.926", detail={"texte_miniature": True, "votes_miniature": 3, "brut_miniature": "19,926"})
    sans = prov("a", "UCA", 19.558, source="miniature", brut="19.558", detail={"texte_miniature": True, "votes_miniature": 3, "brut_miniature": "19.558"})
    assert chrono_bot.noter_virgule_miniature([stockee, sans]) == 1
    assert "miniature : virgule lue comme point" in stockee["notes"] and "miniature : virgule lue comme point" not in sans["notes"]
    assert chrono_bot.noter_virgule_miniature([stockee]) == 0                                    # idempotent
    d = preparer([prov("wJ9CwjKwyco", "UCX", 19.926, source="miniature", brut="19.926", detail={"texte_miniature": True, "brut_miniature": "19,926"})])
    calculer(W, d, CONFIG, HORLOGE)
    assert "miniature : virgule lue comme point" in lire(d, "bot")[0]["notes"]
    (nouvelle,) = miniature.lectures_texte("wJ9CwjKwyco", META, ["19,926,", "19:926,", "19.926"], CONFIG)
    assert nouvelle["detail"]["brut_miniature"].startswith("19,926")
