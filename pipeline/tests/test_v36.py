"""SPEC v36 : lecture BOT de secours incomplète = borne basse (jamais un score), contrôle des lectures provisoires, publication Top 10 non couvert.
Cas réels : YSJFLd_OXww (phases 9.373 / 14.515, Play Time non lu ; miniature 19.517), Bi5TrN5d1_E (28.349 sûr)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrono_bot
import ecrans
import export_excel as ex
from classement import calculer
from test_classement import CONFIG, HORLOGE, W, lec, lire, preparer
from test_v34 import prov

CFG = {"bot": {"phases_par_boss": {"defaut": 3, "baruka": 3}}}


def ecran_ysj(phases, play_time=None, **kw):
    base = dict(score=phases[-1], score_source="debut-fin", exact=False, confidence="a_verifier", t=38, bot_season_week=None,
                detail={"phases": phases, "play_time": play_time, "v27": True, "v27_sur": False, "par_t": [38, 40]},
                notes=["boss non contrôlé", "BOT ja : temps de jeu non lu"])
    base.update(kw)
    return lec("YSJ", "UCY", "bot", base.pop("score"), jour=13, **base)


def test_phases_du_boss_baruka_inconnu_et_defaut():
    assert chrono_bot.phases_du_boss("Baruka", CFG) == 3 and chrono_bot.phases_du_boss(None, CFG) == 3
    assert chrono_bot.phases_du_boss("Boss inconnu", {"bot": {"phases_par_boss": {"defaut": 4}}}) == 4
    assert chrono_bot.phases_du_boss("Boss inconnu", {}) == 3


def test_deux_phases_sur_trois_sans_play_time_borne_basse_jamais_un_score():
    e = ecran_ysj([9.373, 14.515])
    assert chrono_bot.marquer_borne_basse(e, CFG) is True
    assert e["detail"]["borne_basse"] == 14.515 and e["detail"]["sans_score"] is True and e["confidence"] == "a_verifier" and not e["exact"]
    assert "phases incomplètes (2/3) : borne basse 14.515" in e["notes"]
    chrono_bot.marquer_borne_basse(e, CFG)                                              # idempotent
    assert e["notes"].count("phases incomplètes (2/3) : borne basse 14.515") == 1


def test_trois_phases_sans_play_time_reste_a_verifier_inchange():
    e = ecran_ysj([9.373, 14.515, 19.517])
    assert chrono_bot.marquer_borne_basse(e, CFG) is False
    assert "borne_basse" not in e["detail"] and "sans_score" not in e["detail"] and e["confidence"] == "a_verifier"


def test_play_time_lu_ou_texte_ne_sont_pas_des_bornes_basses():
    assert chrono_bot.marquer_borne_basse(ecran_ysj([9.373, 14.515], play_time=14), CFG) is False
    assert chrono_bot.marquer_borne_basse(prov("v", "UC", 19.5), CFG) is False


def test_lecture_bot_cree_la_borne_basse_a_la_source():
    ecran = {"phases": [9.373, 14.515], "chrono": None, "play_time": None, "via_zones": True, "stage": None, "t": 38}
    l = ecrans.lecture_bot({"video_id": "YSJ", "channel_id": "UCY", "channel_title": "y", "published_at": "2026-11-17T06:43:48+01:00", "lang": "ko",
                            "title": "Baruka"}, ecran, CONFIG)
    assert l["detail"]["borne_basse"] == 14.515 and l["detail"]["sans_score"] is True


def test_ysjfld_miniature_19_517_gardee_borne_basse_notee_compatible():
    mini = prov("YSJ", "UCY", 19.517, source="miniature", brut="19.517")
    d = preparer([ecran_ysj([9.373, 14.515]), mini, lec("o", "UCO", "bot", 19.558, jour=13)])
    calculer(W, d, CONFIG, HORLOGE)
    bot = {r["video_id"]: r for r in lire(d, "bot")}
    assert bot["YSJ"]["score"]["total"] == 19.517 and bot["YSJ"]["score_source"] == "miniature" and bot["YSJ"]["confidence"] == "a_verifier"
    assert "borne basse de l'écran 14.515 : compatible" in bot["YSJ"]["notes"]


def test_provisoire_inferieur_a_la_borne_basse_a_verifier():
    mini = prov("YSJ", "UCY", 12.0, source="miniature", brut="12.0")
    d = preparer([ecran_ysj([9.373, 14.515]), mini])
    calculer(W, d, CONFIG, HORLOGE)
    r = lire(d, "bot")[0]
    assert r["confidence"] == "a_verifier" and "provisoire inférieur à la borne basse de l'écran" in r["notes"]


def test_borne_basse_seule_ne_donne_aucune_ligne():
    d = preparer([ecran_ysj([9.373, 14.515]), lec("o", "UCO", "bot", 19.558, jour=13)])
    calculer(W, d, CONFIG, HORLOGE)
    assert [r["video_id"] for r in lire(d, "bot")] == ["o"]


# --- publication : Top 10 non couvert -------------------------------------------------------------------------------------------

def ligne_bot(joueur, total, rank, conf):
    return {"mode": "bot", "player": joueur, "channel": joueur, "video_id": joueur, "video_ids": [joueur], "rank": rank, "confidence": conf,
            "score": {"total": total, "unit": "seconds"}, "published_at": "2026-11-16T11:00:00+01:00", "notes": ""}


def test_top10_non_couvert_ordre_commun_et_rang_officiel_jamais_devant_un_meilleur_provisoire():
    runs = [ligne_bot("Bi5T", 28.349, 1, "sur"), ligne_bot("YSJ", 19.517, None, "a_verifier"), ligne_bot("znpy", 19.599, None, "a_verifier")]
    l = ex.lignes_mode(runs, "bot", couvert=False)
    assert [x["Joueur"] for x in l] == ["YSJ", "znpy", "Bi5T"]
    assert [x["Rang"] for x in l] == [None, None, None]                                   # « 1er » jamais affiché derrière des provisoires meilleurs
    assert l[0]["Statut"] == "À vérifier" and l[2]["Statut"] == "Sûr"


def test_top10_non_couvert_sans_provisoire_meilleur_le_rang_reste():
    runs = [ligne_bot("A", 19.0, 1, "sur"), ligne_bot("B", 19.5, None, "a_verifier")]
    assert [x["Rang"] for x in ex.lignes_mode(runs, "bot", couvert=False)] == [1, None]


def test_top10_couvert_ordre_inchange():
    runs = [ligne_bot("Bi5T", 28.349, 1, "sur"), ligne_bot("YSJ", 19.517, None, "a_verifier")]
    assert [x["Joueur"] for x in ex.lignes_mode(runs, "bot", couvert=True)] == ["Bi5T", "YSJ"]


def test_fusionner_ecrans_borne_basse_ne_remplace_pas_le_titre():
    import pc
    titre = prov("YSJ", "UCY", 19.517, source="titre", brut="19.517s")
    nouvelle = ecran_ysj([9.373, 14.515])
    res = pc.fusionner_ecrans([titre], "YSJ", [nouvelle], CONFIG)
    sources = sorted(l["score_source"] for l in res if l["video_id"] == "YSJ")
    assert sources == ["debut-fin", "titre"]                                       # le titre reste (restauré), la borne basse est gardée avec sa note
    e = next(l for l in res if l["score_source"] == "debut-fin")
    assert e["detail"]["borne_basse"] == 14.515 and e["detail"]["sans_score"] is True
