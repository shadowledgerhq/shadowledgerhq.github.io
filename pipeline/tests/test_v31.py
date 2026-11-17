"""SPEC v31 : élément lu sur les losanges du HUD, priorité hunter_ids > elements_hud > titre, identité par portraits du Results."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import elements
import elements_hud
import hunters_results
from classement import calculer
from test_classement import CONFIG, HORLOGE, W, lec, lire
from test_v30 import monde

OCR = Path(__file__).resolve().parents[2] / "docs" / "essais" / "ocr"
CFG = CONFIG["elements_hud"]


def test_losanges_du_hud_sur_les_captures_reelles():
    lire_ = lambda nom: elements_hud.lire_losanges(OCR / nom, CFG)
    assert lire_("MJ2iz5TFmvM_recherche_202_gb_combat.jpg") == ["fire"] * 3              # 1080p, rouge
    assert lire_("T5dR6iJAn-Y_recherche_214_gb_combat_incertain.jpg") == ["fire"] * 3
    assert lire_("Oj_-5x6700s_recherche_214_gb_combat_incertain.jpg") == ["light"] * 3  # jaune
    assert lire_("nh2D7xZ7dOQ_tri4_240_gb_combat.jpg") == ["light"] * 3                 # 720p
    assert lire_("lGDbzyIJcjY_recherche_238_gb_combat.jpg") == ["wind"] * 3             # vert, 720p
    assert lire_("Oj_-5x6700s_suite_hud_216.jpg") == [None] * 3                          # pas de panneau d'équipe : ambigu, jamais inventé
    assert elements_hud.lire_losanges("fichier_absent.png", CFG) == [None] * 3          # illisible : jamais d'exception
    from PIL import Image
    assert elements_hud.lire_losanges(Image.new("RGB", (1000, 1000)), CFG) == [None] * 3   # pas 16:9


def test_element_de_la_run_majoritaire_2_losanges_sur_2_images():
    f = elements_hud.element_de_la_run
    assert f([["fire", "fire", "fire"], ["fire", None, "fire"]]) == "fire"
    assert f([["fire", "fire", "fire"]]) is None                                   # une seule image
    assert f([["fire", None, None], [None, "fire", None]]) == "fire"                  # 2 losanges concordants sur 2 images
    assert f([["fire", "light", None], ["fire", "light", None]]) is None            # égalité : pas strictement majoritaire
    assert f([["fire", None, None], [None, None, None]]) is None                      # un seul losange : insuffisant
    assert f([[None, None, None], [None, None, None]]) is None and f([]) is None


def test_priorite_ids_puis_hud_puis_titre_et_contradiction():
    hud = {"elements_hud_images": [["fire"] * 3, ["fire"] * 3]}
    # HUD fire + titre Fire : élément `titre+ecran`, deux runs de vidéos différentes distinguées par l'écran / le titre
    d = monde([lec("v1", "UCA", "gb", 160, detail=dict(hud)), lec("v2", "UCA", "gb", 150, jour=14)], {"v1": "GB Fire 160", "v2": "GB Light 150"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["confidence"] == "sur" and l["score"]["total"] == 310
    assert [(x["element"], x["element_source"]) for x in l["runs_detail"]] == [("fire", "titre+ecran"), ("light", "titre")]
    assert "élément associé titre + chasseurs" in l["notes"]
    # HUD fire contre titre Light : contradiction, ligne a_verifier (règle v30)
    d = monde([lec("v1", "UCA", "gb", 160, detail=dict(hud)), lec("v2", "UCA", "gb", 150, jour=14)], {"v1": "GB Light 160", "v2": "GB Water 150"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["confidence"] == "a_verifier" and "élément du titre contredit par l'écran" in l["notes"]
    # hunter_ids (water) prime sur le HUD (fire)
    d = monde([lec("v1", "UCA", "gb", 160, detail={**hud, "hunter_ids": ["a", "b"]})], {"v1": "x"}, {"a": "water", "b": "water"})
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "gb")[0]["runs_detail"][0]["element"] == "water"


def test_build_sur_donne_hunter_ids():
    import json
    d = monde([lec("v1", "UCA", "gb", 160, t=100), lec("v2", "UCA", "gb", 150, jour=14, t=100)], {"v1": "x", "v2": "y"}, {"a": "fire", "b": "fire", "c": "water", "e": "water"})
    for vid, ids in (("v1", ["a", "b"]), ("v2", ["c", "e"])):
        d.ecrire(f"builds/{W}/gb/gb-{W}-{vid}-1.json", {"mode": "gb", "video_id": vid, "t_result": 100, "confidence": "sur", "status": "build_complet",
                                                         "hunters": [{"position": i, "id": h} for i, h in enumerate(ids)]})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert [x["element"] for x in l["runs_detail"]] == ["fire", "water"] and "groupes distingués par les chasseurs" in l["notes"]
    # build non sûr : ignoré
    assert elements.charger_builds(d.data, W) and not elements.ids_du_build([], {"mode": "gb", "video_id": "v1", "t": 1})


def test_hud_rattaches_a_la_run_sans_autre_results_entre_eux():
    import pc
    from tri1 import lecture_vide
    meta = {"video_id": "v", "channel_id": "UC", "channel_title": "J", "published_at": "2026-11-13T12:00:00Z", "lang": "en", "mode_guess": ["gb"]}

    def hud(t, els, chrono):
        l = lecture_vide(meta, "gb")
        l.update(score=None, score_source=None, t=t, detail={"ecran": "combat", "hud_points": None, "chrono_hud": chrono, "separateur_perdu": False,
                                                              "hud_rage_count": 3, "elements_hud": els})
        return l

    def res(t, rc):
        l = lecture_vide(meta, "gb")
        l.update(score=rc, score_source="debut-fin", t=t, confidence="a_verifier", exact=False, damage=10 ** 12, stage="Giant Statue",
                 detail={"player_score": None, "hunter_ranks": [None] * 6, "play_time": "03:00", "ecran": None}, notes=[])
        return l
    # HUD fire (t=20, 40) -> Results RC 100 (t=100) ; HUD water (t=130, 150) -> Results RC 90 (t=200)
    lectures = [hud(20, ["fire"] * 3, 100), hud(40, ["fire"] * 3, 80), res(100, 100), hud(130, ["water"] * 3, 100), hud(150, ["water"] * 3, 80), res(200, 90)]
    out = pc.fusionner_ecrans([], "v", lectures, CONFIG)
    r = sorted((l for l in out if l.get("score") is not None), key=lambda l: l["t"])
    assert [l["detail"]["elements_hud_images"] for l in r] == [[["fire"] * 3, ["fire"] * 3], [["water"] * 3, ["water"] * 3]]
    assert elements_hud.element_de_la_run(r[0]["detail"]["elements_hud_images"]) == "fire"
    assert elements_hud.element_de_la_run(r[1]["detail"]["elements_hud_images"]) == "water"


def test_portraits_du_results_banque_vide_puis_apprise():
    from PIL import Image
    img = Image.open(OCR / "MJ2iz5TFmvM_recherche_223_gb_results_partiel.jpg").convert("RGB")
    with tempfile.TemporaryDirectory() as tmp:
        assert hunters_results.lire(img, CONFIG, tmp, True) == (None, 0)                       # banque vide : rien, sans erreur
        crops = hunters_results.decouper(img, hunters_results.zones_portraits(CONFIG, True))
        assert len(crops) == 6
        # apprentissage : le build sûr donne les identités ; la carte du chasseur (illustration agrandie) apparie la ligne
        cartes = {"hunter-a": crops[0].resize((crops[0].width * 2, crops[0].height * 2)), "hunter-b": crops[1].resize((crops[1].width * 2, crops[1].height * 2))}
        assert hunters_results.apprendre(tmp, ["hunter-a", "hunter-b"], crops, cartes, CONFIG) == 2
        assert sorted(p.name for p in hunters_results.dossier(tmp).glob("*.png")) == ["hunter-a-1.png", "hunter-b-1.png"]
        assert hunters_results.apprendre(tmp, ["hunter-a", "hunter-b"], crops, cartes, CONFIG) == 2        # 2e passage : -2 (max 4 par chasseur)
        ids, n = hunters_results.lire(img, CONFIG, tmp, True)
        assert ids[0] == "hunter-a" and ids[1] == "hunter-b" and n == 2 and ids[2:] == [None] * 4
