"""SPEC v39 : RC GB en conflit = jamais un score ; écart improbable GB ; faux BOT (Battlefield of Infinity / Chaos)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import classement as C
import pc
import youtube

RACINE = Path(__file__).resolve().parents[2]
CONFIG = json.loads((RACINE / "pipeline/config/etape1.json").read_text(encoding="utf-8"))
META = {"video_id": "orJG", "channel_id": "c1", "channel_title": "J", "published_at": "2026-11-20T10:00:00Z", "mode_guess": ["gb"]}


def lecture(score, source, notes=(), t=None, detail=None):
    return {"video_id": "orJG", "channel_id": "c1", "channel_title": "J", "published_at": "2026-11-20T10:00:00Z", "lang": "en", "mode": "gb",
            "regles": 19, "bot_season_week": None, "player_ingame": None, "damage": None, "gate": None, "hunter_mode": None, "t": t, "stage": None,
            "team": None, "score": score, "score_source": source, "exact": False, "confidence": "a_verifier", "detail": detail or {},
            "notes": list(notes)}


def test_rc_en_conflit_n_est_jamais_un_score_et_le_texte_reste():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_tri34 as T
    texte = {**lecture(171, "titre", ["score provisoire (titre) : 171 RC"]), "video_id": "lGDbzyIJcjY"}
    r252, r253c = T._res(T.RESULTS_252, 252, T.Z_252), T._res(T.RESULTS_253_REEL, 253, {**T.Z_253, "rage": "18"})
    sortie = pc.fusionner_ecrans([texte], "lGDbzyIJcjY", [r252, r253c], CONFIG)
    ecrans = [l for l in sortie if l["score_source"] in ("debut-fin", "video-complete") and l["mode"] == "gb" and l.get("score") is not None]
    assert ecrans and all((l.get("detail") or {}).get("sans_score") for l in ecrans) and any("conflit de lecture : rage_count" in l["notes"] for l in ecrans)
    restant = [l for l in sortie if l["score_source"] == "titre"]
    assert len(restant) == 1 and restant[0]["score"] == 171 and any(n.startswith("écran en conflit : RC lu ") for n in restant[0]["notes"])
    # idempotent : un 2e passage ne double ni la note ni la lecture
    de_nouveau = pc.fusionner_ecrans(sortie, "lGDbzyIJcjY", [], CONFIG)
    titres = [l for l in de_nouveau if l["score_source"] == "titre"]
    assert len(titres) == 1 and sum(n.startswith("écran en conflit") for n in titres[0]["notes"]) == 1


def test_classement_ignore_l_ecran_en_conflit():
    ecran = lecture(1, "debut-fin", ["conflit de lecture : rage_count"], detail={"sans_score": True})
    assert (ecran["detail"] or {}).get("sans_score")      # la boucle de calculer() écarte `sans_score` (déjà le cas pour le BOT)


def ligne_gb(vid, rc, source="video-complete", sur=False):
    return {"video_id": vid, "channel_id": vid, "score": {"total": rc, "runs": [rc], "unit": "rage_count"}, "confidence": "sur" if sur else "a_verifier",
            "notes": "", "score_source": source, "_fin": 0, "rank": None, "mode": "gb"}


def test_ecart_improbable_gb_fin_de_liste():
    lignes = [ligne_gb(f"v{rc}", rc) for rc in (322, 189, 185, 177, 176, 19, 2)]
    out = C.ordonner(lignes, "gb")
    assert [l["score"]["total"] for l in out[-2:]] == [19, 2] or {l["score"]["total"] for l in out[-2:]} == {19, 2}
    assert all("écart improbable" in l["notes"] for l in out if l["score"]["total"] in (19, 2))
    assert not any("écart improbable" in l["notes"] for l in out if l["score"]["total"] > 100)


def test_ecart_improbable_gb_moins_de_5_lignes():
    lignes = [ligne_gb(f"v{rc}", rc) for rc in (322, 189, 19, 2)]
    assert not any("écart improbable" in l["notes"] for l in C.ordonner(lignes, "gb"))


def test_faux_bot():
    for titre in ("ｵﾀﾒｼｶﾐｯｼｰ Round 31 Day1 Kamish Draft Run 無限の戦場 Battlefield of Infinity", "How to Clear Battlefield of Chaos Easily!"):
        assert "bot" not in youtube.retirer_faux_bot({"bot"}, titre, CONFIG)
    assert "bot" in youtube.retirer_faux_bot({"bot"}, "BoT Battlefield of Time Baruka", CONFIG)
    assert "bot" in youtube.retirer_faux_bot({"bot"}, "Battlefield of Time vs Battlefield of Chaos", CONFIG)
    assert youtube.retirer_faux_bot({"poc", "bot"}, "Battlefield of Infinity PoC", CONFIG) == {"poc"}


# --- v39 §1 : semaine écoulée non gelée traitée par le daily ---------------------------------------------------

def monde_deux_semaines(tmp, gelee=False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_pc as T
    from datetime import datetime, timezone
    from donnees import Donnees
    from etape1 import ouvrir_semaine
    d = Donnees(tmp)
    prec, cour, ancienne = "2026-11-12", "2026-11-19", "2026-11-05"
    videos, processed = {}, {}
    for sem, ids in ((prec, ("pa", "pz")), (cour, ("ca", "cz"))):
        ouvrir_semaine(d, sem)
        d.ecrire(f"runs/{sem}/_videos.json", {v: {"video_id": v, "channel_id": "UC" + v, "channel_title": "Ch " + v, "title": "patch notes update" if v.endswith("z") else "t",
                                                   "published_at": "2026-11-20T10:00:00Z", "lang": "ko", "duration": "PT5M", "mode_guess": ["poc"]} for v in ids})
        for v in ids:
            processed[v] = {"week": sem, "channel_id": "UC" + v, "published_at": "2026-11-20T10:00:00Z", "first_seen": "2026-11-20", "updated_at": "2026-11-20",
                            "last_tri": 1, "status": "en_cours", "modes": ["poc"], "pc_needed": True}
            if v.endswith("z"):
                processed[v]["hors_sujet_probable"] = True
    ouvrir_semaine(d, ancienne)
    d.ecrire("processed.json", processed)
    if gelee:
        m = d.meta(prec)
        m["frozen"] = True
        d.ecrire(f"runs/{prec}/_meta.json", m)
    return d, T, datetime(2026, 11, 21, 19, 30, tzinfo=timezone.utc)


def test_daily_traite_la_semaine_ecoulee_dans_l_ordre():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d, T, instant = monde_deux_semaines(tmp)
        o = T.FauxOutils({})
        r = pc.lancer("daily", instant, d, T.config_sans_images(), o)
        assert o.appels == ["pa", "ca", "pz", "cz"]              # candidates écoulée, candidates courante, puis les autres (écoulée d'abord)
        assert r["week"] == "2026-11-19"
        assert any("semaine 2026-11-05 non gelée" in a for a in r["alertes"])      # N-2 : plus traitée, alerte
        for sem in ("2026-11-12", "2026-11-19"):
            assert "Passage pc-daily" in (d.data / "runs" / sem / "_rapport_pc.md").read_text(encoding="utf-8")      # un bloc par semaine travaillée
        assert not (d.data / "runs" / "2026-11-05" / "_rapport_pc.md").exists()


def test_daily_budget_et_limite_partages():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d, T, instant = monde_deux_semaines(tmp)
        o = T.FauxOutils({})
        pc.lancer("daily", instant, d, T.config_sans_images(), o, maximum=3)
        assert o.appels == ["pa", "ca", "pz"]                    # limite 3 partagée entre les deux semaines


def test_semaine_ecoulee_gelee_non_traitee():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d, T, instant = monde_deux_semaines(tmp, gelee=True)
        o = T.FauxOutils({})
        pc.lancer("daily", instant, d, T.config_sans_images(), o)
        assert o.appels == ["ca", "cz"]


def test_weekly_inchange():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d, T, _ = monde_deux_semaines(tmp)
        from datetime import datetime, timezone
        o = T.FauxOutils({})
        r = pc.lancer("weekly", datetime(2026, 11, 26, 0, 30, tzinfo=timezone.utc), d, T.config_sans_images(), o)
        assert r["week"] == "2026-11-19" and set(o.appels) == {"ca", "cz"}


# --- relectures manuelles (v39 §4, v40 §8) ----------------------------------------------------------------------

def test_relectures_manuelles_une_fois_par_version():
    import tempfile
    import relectures
    from donnees import Donnees
    with tempfile.TemporaryDirectory() as tmp:
        d = Donnees(tmp)
        sem = "2026-11-19"
        base = {"week": sem, "status": "en_cours", "pc_needed": False, "pc": {"tri3": "fait", "tri4": "fait", "results_lus": [[1, 2]]}}
        processed = {"3y8yRhcSq4Y": json.loads(json.dumps(base)), "TjnPwCk_VSc": json.loads(json.dumps(base)),
                     "THxs2Y7QFI0": {**json.loads(json.dumps(base)), "status": "rejete", "pc": {"tri3": "fait", "tri4": "inutile", "rejet": "actualites"}}}
        d.ecrire(f"rejected/{sem}.json", [{"video_id": "THxs2Y7QFI0", "reason": "actualites"}, {"video_id": "autre", "reason": "live"}])
        posees = relectures.poser_manuelles(d, sem, CONFIG, processed, "2026-11-25")
        assert {v for v, _ in posees} == {"3y8yRhcSq4Y", "TjnPwCk_VSc", "THxs2Y7QFI0"}
        a = processed["3y8yRhcSq4Y"]
        assert a["status"] == "en_cours" and a["pc_needed"] and a["pc"]["tri3"] == "fait" and a["pc"]["tri4"] == "a_faire" and a["pc"]["results_lus"] == []
        t = processed["TjnPwCk_VSc"]
        assert t["pc"]["tri3"] == "a_faire" and t["relecture_dernier"] is True
        x = processed["THxs2Y7QFI0"]
        assert x["status"] == "en_cours" and x["pc"]["forcer_tri4"] is True and "rejet" not in x["pc"]
        assert [r["video_id"] for r in d.rejected(sem)] == ["autre"]
        assert relectures.poser_manuelles(d, sem, CONFIG, processed, "2026-11-26") == []        # une seule fois par version
        assert relectures.poser_manuelles(d, "2026-11-12", CONFIG, processed, "2026-11-26") == []     # autre semaine : rien


def test_relecture_dernier_jamais_candidate():
    import ordre_pc
    import tempfile
    from donnees import Donnees
    with tempfile.TemporaryDirectory() as tmp:
        d = Donnees(tmp)
        d.ecrire("runs/2026-11-19/_videos.json", {"a": {"duration": "PT5M"}, "b": {"duration": "PT5M"}})
        p = {"a": {"week": "2026-11-19"}, "b": {"week": "2026-11-19", "relecture_dernier": True}}
        ordre, cand = ordre_pc.ordonner(d, "2026-11-19", ["b", "a"], p, 30)
        assert ordre == ["a", "b"] and cand == {"a"}
