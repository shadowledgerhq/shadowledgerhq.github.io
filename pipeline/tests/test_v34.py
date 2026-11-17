"""SPEC v34 : tri 2 (texte de la miniature), chronos BOT incomplets (intervalles, remplacement, rang prudent, désaccord), relecture
automatique du top 10 provisoire, boss BOT juste après le reset. Cas réel : wJ9CwjKwyco (X SLA, BOT 2026-11-12, miniature « 19.926 »)."""
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrono_bot
import miniature
import pc
import relectures
import scores
from classement import calculer
from test_classement import CONFIG, HORLOGE, W, lec, lire, preparer

MINIATURE = Path(__file__).resolve().parents[2] / "docs" / "essais" / "miniatures" / "wJ9CwjKwyco_maxresdefault.jpg"
META = {"video_id": "wJ9CwjKwyco", "channel_id": "UCX", "channel_title": "X SLA", "published_at": "2026-11-12T01:50:30Z", "lang": "en",
        "mode_guess": ["bot"], "title": "19s Baruka"}


def prov(vid, ch, score, source="titre", brut=None, jour=13, **kw):
    """Run BOT provisoire lue dans un texte."""
    brut = brut or str(score)
    return lec(vid, ch, "bot", score, jour=jour, t=None, exact=False, confidence="a_verifier", score_source=source, bot_season_week=None,
               notes=[f"score provisoire ({source}) : {brut}"], **kw)


# --- intervalles ---------------------------------------------------------------------------------------------------------------

def test_bornes_des_chronos():
    assert chrono_bot.bornes(19.0, 0) == (19.0, 19.999) and chrono_bot.bornes(19.9, 1) == (19.9, 19.999)
    assert chrono_bot.bornes(19.92, 2) == (19.92, 19.929) and chrono_bot.bornes(19.926, 3) == (19.926, 19.926)


def test_scores_chronos_porte_les_decimales():
    d = lambda t: [(c["valeur"], c["decimales"]) for c in scores.chronos(t)]
    assert d("19s") == [(19.0, 0)] and d("19초") == [(19.0, 0)] and d("19.9s") == [(19.9, 1)] and d("00:19") == [(19.0, 0)]
    assert d("19.926") == [(19.926, 3)] and d("00:19.926") == [(19.926, 3)] and d("Play Time 00:19") == [(19.0, 0)]


# --- réconciliation d'une vidéo ------------------------------------------------------------------------------------------------

def test_titre_arrondi_remplace_par_la_miniature_precise():
    r, ecartees = chrono_bot.reconcilier_video([prov("wJ9", "UCX", 19.0, brut="19s"), prov("wJ9", "UCX", 19.926, "miniature", "19.926")])
    assert (r["score"], r["score_source"]) == (19.926, "miniature") and "titre arrondi : 19s" in r["notes"] and "_tri" not in r
    assert not any("rang prudent" in n for n in r["notes"]) and len(ecartees) == 1
    assert r["notes"][0] == "score provisoire (miniature) : 19.926"


def test_titre_arrondi_vers_le_haut_partie_entiere_n_moins_1():
    r, _ = chrono_bot.reconcilier_video([prov("v", "UCX", 20.0, brut="20s"), prov("v", "UCX", 19.926, "miniature", "19.926")])
    assert r["score"] == 19.926 and "titre arrondi : 20s" in r["notes"]


def test_dixieme_est_compatible_et_remplace():
    r, _ = chrono_bot.reconcilier_video([prov("v", "UCX", 19.9, brut="19.9s"), prov("v", "UCX", 19.926, "miniature", "19.926")])
    assert r["score"] == 19.926 and "titre arrondi : 19.9s" in r["notes"]


def test_sans_lecture_precise_rang_prudent_a_la_borne_haute():
    r, ecartees = chrono_bot.reconcilier_video([prov("v", "UCX", 19.0, brut="19s")])
    assert r["score"] == 19.0 and r["_tri"] == 19.999 and "chrono incomplet : rang prudent" in r["notes"] and ecartees == []
    r, _ = chrono_bot.reconcilier_video([prov("v", "UCX", 19.9, brut="19.9s")])
    assert r["score"] == 19.9 and r["_tri"] == 19.999


def test_lecture_precise_incompatible_est_un_desaccord_a_verifier():
    r, _ = chrono_bot.reconcilier_video([prov("v", "UCX", 19.0, brut="19s"), prov("v", "UCX", 25.4, "miniature", "25.400")])
    assert r["score"] == 19.0 and "titre/miniature en désaccord" in r["notes"] and r["_tri"] == 19.999
    r, _ = chrono_bot.reconcilier_video([prov("v", "UCX", 19.558, brut="19.558"), prov("v", "UCX", 21.2, "miniature", "21.200")])
    assert r["score"] == 19.558 and "titre/miniature en désaccord" in r["notes"] and "_tri" not in r
    r, _ = chrono_bot.reconcilier_video([prov("v", "UCX", 19.558, brut="19.558"), prov("v", "UCX", 19.9, "miniature", "19.900")])
    assert not any("désaccord" in n for n in r["notes"])          # moins de 1 s d'écart entre deux lectures précises


def test_autre_source_notee_dans_la_lecture_compte_comme_lecture_precise():
    run = prov("v", "UCX", 19.0, brut="19s")
    run["notes"].append("description : 19.926")
    r, _ = chrono_bot.reconcilier_video([run])
    assert r["score"] == 19.926 and r["score_source"] == "description" and "titre arrondi : 19s" in r["notes"]


def test_ecran_et_hud_ne_sont_jamais_touches():
    ecran = lec("e", "UCX", "bot", 19.926, score_source="debut-fin", t=182)
    assert chrono_bot.reconcilier([ecran, prov("e2", "UCY", 40.0, brut="40s")])[0] is ecran


# --- classement : cas wJ9 ------------------------------------------------------------------------------------------------------

def _bot(lectures):
    d = preparer(lectures)
    calculer(W, d, CONFIG, HORLOGE)
    return lire(d, "bot")


def test_ordre_bot_wj9_avec_la_miniature():
    """aaaa 19.558, Rui 19.754, X SLA 19.926 (miniature), PADWAE 19.9 (trié à 19.999)."""
    lignes = _bot([prov("a", "UCA", 19.558, jour=12), prov("r", "UCR", 19.754, jour=13),
                   prov("wJ9", "UCX", 19.0, brut="19s", jour=12), prov("wJ9", "UCX", 19.926, "miniature", "19.926", jour=12),
                   prov("p", "UCP", 19.9, brut="19.9s", jour=12)])
    assert [(l["player"], l["score"]["total"]) for l in lignes] == [("uca", 19.558), ("ucr", 19.754), ("ucx", 19.926), ("ucp", 19.9)]
    assert "chrono incomplet : rang prudent" in lignes[3]["notes"] and "titre arrondi : 19s" in lignes[2]["notes"]
    assert all(l["confidence"] == "a_verifier" and "_tri" not in l for l in lignes)


def test_sans_miniature_le_rang_prudent_met_les_arrondis_apres_les_precis():
    lignes = _bot([prov("a", "UCA", 19.558), prov("r", "UCR", 19.754), prov("wJ9", "UCX", 19.0, brut="19s", jour=12),
                   prov("p", "UCP", 19.9, brut="19.9s", jour=13), prov("z", "UCZ", 19.95, jour=14)])
    assert [l["player"] for l in lignes] == ["uca", "ucr", "ucz", "ucx", "ucp"]       # 19.95 précis avant les bornes hautes 19.999
    assert [l["score"]["total"] for l in lignes] == [19.558, 19.754, 19.95, 19.0, 19.9]   # le score affiché reste celui qui a été lu


def test_meilleure_run_d_un_joueur_utilise_la_borne_haute():
    lignes = _bot([prov("v1", "UCA", 19.0, brut="19s"), prov("v2", "UCA", 19.5, jour=14)])
    assert lignes[0]["score"]["total"] == 19.5 and lignes[0]["video_id"] == "v2"


# --- miniature (tri 2) ---------------------------------------------------------------------------------------------------------

def test_vote_de_la_miniature():
    textes = ["19,926,", "19:926,.", "192926", "10.026", ""]
    v = miniature.voter(textes, "bot", CONFIG, 2)
    assert v["valeur"] == 19.926 and v["votes"] == 2 and v["autres"] == []
    assert miniature.voter(textes, "bot", CONFIG, 3) is None
    assert miniature.voter(["up to 19.926"], "bot", CONFIG, 1) is None            # hypothèse exclue (règles du tri 1)
    assert miniature.voter(["", "x"], "bot", CONFIG, 1) is None


def test_lecture_de_miniature_est_provisoire():
    (lecture,) = miniature.lectures_texte("wJ9CwjKwyco", META, ["19,926,", "19:926,", "19.926"], CONFIG)
    assert (lecture["score"], lecture["score_source"], lecture["exact"], lecture["confidence"]) == (19.926, "miniature", False, "a_verifier")
    assert lecture["detail"]["texte_miniature"] is True and "score provisoire (miniature) : 19.926" in lecture["notes"]
    assert pc.est_texte(lecture) and not pc._est_ecran(lecture)


class _Outils:
    def ocr(self, png, langues=None, psm=6, timeout=40, extra=None):
        return subprocess.run(["tesseract", str(png), "stdout", "-l", langues or "eng", "--psm", str(psm), *(extra or [])],
                              capture_output=True, text=True, timeout=timeout).stdout


class _Reponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _ouvrir(url):
    if "maxresdefault" not in url:
        raise OSError("404")
    return _Reponse(MINIATURE.read_bytes())


@pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract absent")
def test_wj9_miniature_reelle_donne_19_926(tmp_path):
    lecs, plein, etat = miniature.lire("wJ9CwjKwyco", META, _Outils(), CONFIG, tmp_path, "eng", _ouvrir)
    assert etat == "fait" and [(l["score"], l["score_source"]) for l in lecs] == [(19.926, "miniature")]
    assert lecs[0]["detail"]["votes_miniature"] >= 2


@pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract absent")
def test_traiter_miniature_ajoute_la_lecture_une_seule_fois(tmp_path):
    etat = {}
    titre = prov("wJ9CwjKwyco", "UCX", 19.0, brut="19s")
    lectures = pc.traiter_miniature("wJ9CwjKwyco", META, _Outils(), CONFIG, [titre], etat, telecharger=_ouvrir)
    assert etat["tri2"] == "fait" and [(l["score_source"], l["score"]) for l in lectures] == [("titre", 19.0), ("miniature", 19.926)]
    assert pc.traiter_miniature("wJ9CwjKwyco", META, _Outils(), CONFIG, lectures, etat, telecharger=_ouvrir) is lectures      # idempotent
    # classement : la miniature remplace le titre arrondi
    d = preparer(lectures)
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "bot")
    assert l["score"]["total"] == 19.926 and l["score_source"] == "miniature" and "titre arrondi : 19s" in l["notes"]


def test_miniature_introuvable_est_absente_et_ne_leve_pas(tmp_path):
    def non(url):
        raise OSError("404")
    etat = {}
    assert pc.traiter_miniature("x", META, _Outils(), CONFIG, [], etat, telecharger=non) == []
    assert etat["tri2"] == "absent"


def test_un_ecran_lu_remplace_le_texte_de_la_miniature():
    (mini,) = miniature.lectures_texte("wJ9CwjKwyco", META, ["19.926", "19,926"], CONFIG)
    ecran = lec("wJ9CwjKwyco", "UCX", "bot", 19.926, score_source="video-complete", t=21)
    ecran.update(channel_id="UCX", published_at="2026-11-12T01:50:30Z")
    res = pc.fusionner_ecrans([mini], "wJ9CwjKwyco", [ecran], CONFIG)
    assert [(l["score_source"], l["t"]) for l in res if l["video_id"] == "wJ9CwjKwyco" and l["mode"] == "bot"] == [("video-complete", 21)]


# --- relecture automatique -----------------------------------------------------------------------------------------------------

def _monde(tmp_path, lignes, processed):
    from donnees import Donnees
    d = Donnees(tmp_path)
    d.ecrire(f"runs/{W}/bot.json", lignes)
    return d, processed


def _l(vid, conf="a_verifier"):
    return {"video_id": vid, "video_ids": [vid], "confidence": conf, "rank": None}


def _p(**kw):
    base = {"week": W, "status": "termine", "regles": 17, "pc_needed": False, "pc": {"tri3": "fait", "tri4": "fait", "results_lus": []}}
    base.update(kw)
    return base


def test_relecture_automatique_top_10_provisoire(tmp_path):
    lignes = [_l("wJ9"), _l("sure", "sur"), _l("lue"), _l("recente"), _l("deja"), _l("encours")] + [_l(f"x{i}") for i in range(10)]
    processed = {"wJ9": _p(), "sure": _p(), "lue": _p(pc={"results_lus": [[10, 20]]}), "recente": _p(regles=18), "deja": _p(relecture_auto=18),
                 "encours": _p(status="en_cours"), "x9": _p()}
    d, processed = _monde(tmp_path, lignes, processed)
    posees = relectures.poser(d, W, CONFIG, processed, "2026-11-17")
    assert posees == [("wJ9", "bot")]                                  # x9 est hors du top 10 ; sûre, lue, récente, déjà posée : non
    p = processed["wJ9"]
    assert (p["status"], p["pc_needed"], p["relecture"], p["relecture_auto"]) == ("en_cours", True, "2026-11-17", CONFIG["tri1_version"])
    assert p["pc"]["tri3"] == "a_faire" and p["pc"]["tri4"] == "a_faire" and p["pc"]["results_lus"] == []
    assert relectures.lignes_rapport(posees)[0].endswith("wJ9 (bot)")
    # un seul passage : la vidéo relue (même sans rien trouver) n'est pas reposée
    p["status"] = "termine"
    assert relectures.poser(d, W, CONFIG, processed, "2026-11-18") == []


# --- boss BOT juste après le reset ---------------------------------------------------------------------------------------------

def _run_boss(vid, ch, boss, pub, score):
    return lec(vid, ch, "bot", score, stage=boss, published_at=pub, bot_season_week=None)


def test_boss_bot_different_juste_apres_le_reset_est_la_semaine_precedente():
    pub_proche, pub_tard = "2026-11-12T03:00:00Z", "2026-11-13T12:00:00Z"            # reset = 2026-11-12 00:00Z
    lectures = [_run_boss("b1", "UC1", "Baruka", pub_tard, 20.0), _run_boss("b2", "UC2", "Baruka", pub_tard, 21.0),
                _run_boss("b3", "UC3", "Baruka", pub_tard, 22.0),
                _run_boss("proche-bon", "UC4", "Baruka", pub_proche, 23.0), _run_boss("proche-autre", "UC5", "Tar", pub_proche, 18.0),
                _run_boss("tard-autre", "UC6", "Tar", pub_tard, 24.0)]
    lectures[3]["notes"].append("publiée juste après le reset : semaine précédente ?")
    d = preparer(lectures)
    calculer(W, d, CONFIG, HORLOGE)
    lignes = {l["video_id"]: l for l in lire(d, "bot")}
    assert "proche-autre" not in lignes                                              # rejetée : semaine_precedente
    rejets = json.loads((d.data / "rejected" / f"{W}.json").read_text(encoding="utf-8"))
    assert [(r["video_id"], r["reason"], r["detail"]) for r in rejets] == [("proche-autre", "semaine_precedente", "Tar")]
    assert "semaine précédente ?" not in lignes["proche-bon"]["notes"] and lignes["proche-bon"]["confidence"] == "sur"
    assert lignes["tard-autre"]["confidence"] == "a_verifier" and "boss différent : Tar" in lignes["tard-autre"]["notes"]
    boss = json.loads((d.data / "runs" / W / "_boss.json").read_text(encoding="utf-8"))
    assert [(b["classement"], b["stage"]) for b in boss] == [("bot", "Baruka")]


def test_miniature_avec_grands_nombres_ne_donne_pas_de_chrono():
    """VFDbdYFzor4 (17/11) : « 60.279.160 » (Hunter Rank) lu « 60.278 » sur 2 variantes : pas un chrono."""
    assert miniature.lectures_texte("VFD", META, ["60.278", "60,278", "11.736.161.929 3.082.023.106"], CONFIG) == []
    assert len(miniature.lectures_texte("wJ9", META, ["19.926", "19,926"], CONFIG)) == 1


def test_miniature_bot_ignore_les_chronos_arrondis():
    """Essai du 17/11 sur 33 miniatures BOT : `7s`, `10s`, `130s`, `149s` (bruit) lus sans millièmes : jamais un score."""
    assert miniature.voter(["7s", "7 s", "10.0s", "130 sec"], "bot", CONFIG, 1) is None
    assert miniature.voter(["00:19.926", "19.926s"], "bot", CONFIG, 2)["valeur"] == 19.926


def test_miniature_seule_source_exige_trois_lectures(tmp_path, monkeypatch):
    """g50pPUDoTvw (17/11) : minuteur de HUD « 02:29.725 » lu 2 fois sur une vidéo sans score dans le titre : pas de ligne ; avec un score au
    titre, 2 lectures suffisent."""
    def faux_lire(vid, meta, outils, config, tmp, langues, telecharger_fn, journal):
        return miniature.lectures_texte(vid, meta, ["29.725", "29,725"], config), "", "fait"
    monkeypatch.setattr(miniature, "lire", faux_lire)
    etat = {}
    assert pc.traiter_miniature("g50", {**META, "video_id": "g50"}, None, CONFIG, [], etat) == [] and etat["tri2"] == "fait"
    titre = prov("g50", "UCX", 40.0, brut="40s")
    res = pc.traiter_miniature("g50", {**META, "video_id": "g50"}, None, CONFIG, [titre], {})
    assert [l["score_source"] for l in res] == ["titre", "miniature"]
