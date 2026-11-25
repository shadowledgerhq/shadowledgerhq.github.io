"""POC refonte du 19/11/2026 : élément, équipes, doublons, alerte chasseur commun, ligne jamais `sûr`."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import builds as B
import classement as C
import elements

CFG = {"fichier_hotm_porte_inconnue": "x", "doublon_modes": ["poc"], "poc_refonte": {"semaine_debut": "2026-11-19", "classement_sur": True}, "elements_titre": {"fire": ["fire"], "water": ["water"]}}


def run(vid, team, score, element=None, refonte=True, hunters=(), t=10):
    return {"video_id": vid, "mode": "poc", "channel_id": "c1", "channel_title": "J", "published_at": "2026-11-20T10:00:00Z", "team": team,
            "score": score, "exact": True, "confidence": "sur", "score_source": "debut-fin", "t": t, "stage": None, "notes": [], "_cle": "c1",
            "element": element, "element_source": "ecran" if element else None, "detail": {"hunter_ids": list(hunters)}, **({"_refonte": True} if refonte else {})}


def test_semaine():
    assert elements.refonte_poc("2026-11-19", CFG) and elements.refonte_poc("2026-11-26", CFG)
    assert not elements.refonte_poc("2026-11-12", CFG) and not elements.refonte_poc("2026-11-19", {})


def test_meme_element_ne_distingue_plus_mais_l_equipe_oui():
    a, b = run("v", 1, 5, "fire"), run("v", 2, 4, "fire")
    assert elements.distinctes(a, b) == "oui"                       # même élément : autorisé, l'équipe lue tranche
    a, b = run("v", None, 5, "fire", refonte=False), run("w", None, 4, "fire", refonte=False)
    assert elements.distinctes(a, b) == "non"                       # ancien système inchangé (même élément, équipes non lues)


def test_elements_differents_sans_equipe_ne_distinguent_pas():
    a, b = run("v", None, 5, "fire"), run("w", None, 4, "water")
    assert elements.distinctes(a, b) == "non"
    a, b = run("v", None, 5, "fire", refonte=False), run("w", None, 4, "water", refonte=False)
    assert elements.distinctes(a, b) == "oui"


def test_chasseur_commun_equipes_lues_ok_sinon_non():
    a, b = run("v", 1, 5, hunters=["x"]), run("v", 2, 4, hunters=["x"])
    assert elements.distinctes(a, b) == "oui"
    a, b = run("v", 1, 5, hunters=["x"]), run("w", None, 4, hunters=["x"])
    assert elements.distinctes(a, b) == "non"
    assert elements.distinctes(run("v", 1, 5), run("w", None, 4)) == "peut"


def test_pas_de_contradiction_titre_pour_le_poc_refonte():
    r = run("v", 1, 5)
    r["detail"]["hunter_ids"] = ["h"]
    runs = [r]
    elements.annoter(runs, {"v": "POC water team"}, CFG, {"h": "fire"})
    assert r["element"] == "fire" and not r.get("_contradiction") and not r["notes"]


def test_doublon_meme_score_equipes_differentes_gardes():
    a, b = run("v", 1, 17_000_000), run("v", 2, 17_000_000)
    gardees, doublons = C.dedoublonner([a, b], CFG)
    assert len(gardees) == 2 and not doublons
    c = run("w", 1, 17_000_000)        # même équipe, autre vidéo = la même run : doublon
    gardees, _ = C.dedoublonner([a, c], CFG)
    assert len(gardees) == 1


def test_note_chasseur_commun_poc_refonte():
    def b(i, week):
        return {"mode": "poc", "run_id": "L", "run_index": i, "week": week, "dossier": "poc", "notes": "", "confidence": "sur", "hunters": [{"id": "x"}]}
    nouveaux = [b(1, "2026-11-19"), b(2, "2026-11-19")]
    B.controler_chasseurs_communs(nouveaux)
    assert "règle actuelle non publiée" in nouveaux[0]["notes"] and nouveaux[0]["confidence"] == "sur"      # v40 : note seule
    anciens = [b(1, "2026-11-12"), b(2, "2026-11-12")]
    B.controler_chasseurs_communs(anciens)
    assert anciens[0]["notes"] == "chasseur commun aux 2 runs : x"
