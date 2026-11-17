"""SPEC v30 : GB = runs filmées seulement ; éléments des runs (titre, chasseurs) ; distinction des groupes ; total GB / POC."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import elements
from classement import calculer
from test_classement import CONFIG, HORLOGE, T, W, lec, lire, preparer


def monde(lectures, titres=None, hunters=None):
    d = preparer(lectures)
    d.ecrire(f"runs/{W}/_videos.json", {v: {"video_id": v, "title": t} for v, t in (titres or {}).items()})
    if hunters:
        d.ecrire("db/hunters.json", [{"id": i, "element": e} for i, e in hunters.items()])
    return d


def test_elements_du_titre_multilingue():
    f = lambda t: elements.elements_du_titre(t, CONFIG)
    assert f("GUILD BOSS 156 RC - FIRE team") == ["fire"] and f("Giant Statue Light + Wind") == ["light", "wind"]
    assert f("Lightning build") == [] and f("Água / Fogo") == ["water", "fire"] and f("闇 のみ") == ["dark"] and f("闇属性") == []
    assert f("불 속성 파티") == ["fire"] and f("물을 사용") == [] and f("불가능") == []
    assert f("Luz Fuego") == ["light", "fire"] and f("Ténèbres vs Eau") == ["dark", "water"]


def test_v31_mots_d_un_caractere_isoles_seulement():
    f = lambda t: elements.elements_du_titre(t, CONFIG)
    assert f("水篠旬") == [] and f("괴물") == [] and f("화상 불꽃") == [] and f("旬水1") == []
    assert f("석상 불 160") == ["fire"] and f("Statue Light 162") == ["light"] and f("불, 물") == ["fire", "water"]
    assert f("GB 불160") == ["fire"] and f("闇") == ["dark"] and f("바람 암흑") == ["wind", "dark"]      # plus d'un caractère : règle inchangée


def test_deux_videos_un_element_chacune_sont_additionnees_et_sures():
    """Cas RaidenShadow : 156 (titre Fire) + 137 (titre Light), 1 run filmée par vidéo -> 293 sûr, team null."""
    d = monde([lec("v1", "UCR", "gb", 156, damage=7 * T), lec("v2", "UCR", "gb", 137, damage=3 * T, jour=14)],
              {"v1": "Giant Statue FIRE build", "v2": "Giant Statue Light team"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert (l["score"]["total"], l["score"]["runs"], l["confidence"], l["rank"]) == (293, [156, 137], "sur", 1)
    assert [(x["team"], x["element"], x["element_source"]) for x in l["runs_detail"]] == [(None, "fire", "titre"), (None, "light", "titre")]
    assert "groupes distingués par le titre (Fire / Light)" in l["notes"]


def test_meme_element_ou_titre_muet_la_2e_run_reste_en_note():
    d = monde([lec("v1", "UCR", "gb", 156), lec("v2", "UCR", "gb", 137, jour=14)], {"v1": "Fire run", "v2": "Fire again"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["score"]["total"] == 156 and "groupes inconnus : 2e run non additionnée (137, v2)" in l["notes"]
    d = monde([lec("v1", "UCR", "gb", 156), lec("v2", "UCR", "gb", 137, jour=14)], {"v1": "Giant Statue", "v2": "Giant Statue 2"})
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "gb")[0]["score"]["total"] == 156


def test_titre_a_deux_elements_et_deux_runs_une_lue_a_l_ecran():
    """Vidéo à 2 runs, titre « Light + Fire » : la run dont les chasseurs sont Fire reçoit Fire (écran), l'autre l'élément restant."""
    h = {"h1": "fire", "h2": "fire", "h3": "light"}
    d = monde([lec("v1", "UCA", "gb", 160, damage=5 * T, detail={"hunter_ids": ["h1", "h2"]}), lec("v1", "UCA", "gb", 140, damage=4 * T, t=90)],
              {"v1": "GB Light + Fire"}, h)
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["score"]["total"] == 300 and l["confidence"] == "sur"
    assert [(x["element"], x["element_source"]) for x in l["runs_detail"]] == [("fire", "titre+ecran"), ("light", "titre+ecran")]
    assert "élément associé titre + chasseurs" in l["notes"]
    # aucune run lue à l'écran : pas d'association
    d = monde([lec("v1", "UCA", "gb", 160), lec("v1", "UCA", "gb", 140, t=90)], {"v1": "GB Light + Fire"})
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "gb")[0]["score"]["total"] == 160


def test_chasseurs_a_l_ecran_distinguent_ou_confondent_les_groupes():
    h = {"a": "fire", "b": "fire", "c": "water", "d": "water", "e": "water"}
    d = monde([lec("v1", "UCA", "gb", 160, detail={"hunter_ids": ["a", "b"]}), lec("v2", "UCA", "gb", 150, jour=14, detail={"hunter_ids": ["c", "d"]})],
              {"v1": "x", "v2": "y"}, h)
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["score"]["total"] == 310 and "groupes distingués par les chasseurs" in l["notes"] and l["runs_detail"][0]["element_source"] == "ecran"
    # un chasseur commun vu à l'écran = même groupe, sans exception (même si les éléments majoritaires diffèrent)
    d = monde([lec("v1", "UCA", "gb", 160, detail={"hunter_ids": ["a", "b", "c"]}), lec("v2", "UCA", "gb", 150, jour=14, detail={"hunter_ids": ["c", "d", "e"]})],
              {"v1": "x", "v2": "y"}, h)
    calculer(W, d, CONFIG, HORLOGE)
    assert lire(d, "gb")[0]["score"]["total"] == 160


def test_ecran_contredit_le_titre_ligne_a_verifier():
    h = {"a": "water", "b": "water"}
    d = monde([lec("v1", "UCA", "gb", 160, detail={"hunter_ids": ["a", "b"]}), lec("v2", "UCA", "gb", 150, jour=14)],
              {"v1": "Fire build", "v2": "Light team"}, h)
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["confidence"] == "a_verifier" and "élément du titre contredit par l'écran" in l["notes"] and l["rank"] is None


def test_poc_equipe_lue_prime_et_total_par_element_sans_equipe():
    d = monde([lec("p1", "UCP", "poc", 100 * T, team=1), lec("p2", "UCP", "poc", 60 * T, team=2)], {"p1": "x", "p2": "y"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "poc")
    assert l["score"]["total"] == 160 * T and [x["team"] for x in l["runs_detail"]] == [1, 2]
    d = monde([lec("p1", "UCP", "poc", 100 * T), lec("p2", "UCP", "poc", 60 * T, jour=14)], {"p1": "POC Dark", "p2": "POC Water"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "poc")
    assert l["score"]["total"] == 160 * T and [x["element"] for x in l["runs_detail"]] == ["dark", "water"] and l["runs_detail"][0]["team"] is None


def test_un_rc_du_titre_reste_provisoire_et_ne_change_rien_au_total():
    d = monde([lec("v1", "UCA", "gb", 160), lec("v1", "UCA", "gb", 200, exact=False, confidence="a_verifier", score_source="titre", jour=13)],
              {"v1": "GB 200 RC Fire"})
    calculer(W, d, CONFIG, HORLOGE)
    (l,) = lire(d, "gb")
    assert l["score"]["total"] == 160 and l["confidence"] == "sur"        # la run provisoire du titre n'est jamais additionnée à une run exacte
