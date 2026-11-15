"""SPEC_ETAPE1 v24 : `premiere_semaine` des boss, règles déduites des écrans, libellés inconnus."""
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import libelles_inconnus as LI
import regles_deduites as R
from classement import calculer
from donnees import Donnees, charger_config
from test_classement import HORLOGE, T, W, lec, lire, preparer


# --- premiere_semaine ---------------------------------------------------------------------------------------------------

def _hotm(vid, ch, stage="Porte du Feu"):
    return lec(vid, ch, "hotm", 100 * T, gate=1, stage=stage)


def test_premiere_semaine_du_boss():
    lectures = [_hotm("a", "UC1"), _hotm("b", "UC2"), _hotm("c", "UC3")]
    # semaine précédente : même boss, déjà vu depuis la semaine d'avant -> première semaine conservée
    d = preparer(lectures, boss_prec=[{"classement": "hotm-gate-1", "stage": "Porte du Feu", "premiere_semaine": "2026-10-29"}])
    calculer(W, d, charger_config(), HORLOGE)
    assert lire(d, "_boss")[0]["premiere_semaine"] == "2026-10-29"
    # boss absent de la semaine précédente : première semaine = cette semaine
    d = preparer(lectures, boss_prec=[{"classement": "hotm-gate-1", "stage": "Autre"}])
    calculer(W, d, charger_config(), HORLOGE)
    assert lire(d, "_boss")[0]["premiere_semaine"] == W
    # même boss mais fichier sans premiere_semaine (avant v24) : au plus tard la semaine précédente
    d = preparer(lectures, boss_prec=[{"classement": "hotm-gate-1", "stage": "Porte du Feu"}])
    calculer(W, d, charger_config(), HORLOGE)
    assert lire(d, "_boss")[0]["premiere_semaine"] == "2026-11-05"


# --- règles déduites -----------------------------------------------------------------------------------------------------

def _gb(vid, ch, successeur, sur=True):
    return lec(vid, ch, "gb", 150, score_source="debut-fin", confidence="sur" if sur else "a_verifier",
               detail={"player_score": 1000, "successeur_present": successeur, "hunter_ranks_lus": 6})


def test_regle_true_des_une_run_sure_false_apres_5_chaines():
    p = R.preuves_lectures([_gb("v1", "UC1", True)])
    assert R.valeurs(p)["gb"] == {"sjw": (True, ["v1"]), "successor": (True, ["v1"])}
    absentes = [_gb(f"v{i}", f"UC{i}", False) for i in range(5)]
    v = R.valeurs(R.preuves_lectures(absentes))
    assert v["gb"]["successor"][0] is False and len(v["gb"]["successor"][1]) == 5
    # 5 runs mais seulement 4 chaînes : inconnu
    quatre = absentes[:4] + [_gb("v9", "UC0", False)]
    assert "successor" not in R.valeurs(R.preuves_lectures(quatre)).get("gb", {})
    # jamais false sur une seule vidéo ; une preuve contraire (true) l'emporte ; run non sûre ignorée
    assert "gb" not in R.valeurs(R.preuves_lectures([_gb("v1", "UC1", False)])) or "successor" not in R.valeurs(R.preuves_lectures([_gb("v1", "UC1", False)]))["gb"]
    assert R.valeurs(R.preuves_lectures(absentes + [_gb("vz", "UCZ", True)]))["gb"]["successor"][0] is True
    assert R.valeurs(R.preuves_lectures([_gb("v1", "UC1", True, sur=False)])) == {}


def test_regles_poc_et_builds():
    poc = lec("p1", "UCP", "poc", 100 * T, detail={"sjw": 10, "successor": 5, "hunters": [1, 2, 3]})
    assert R.valeurs(R.preuves_lectures([poc]))["poc"]["sjw"][0] is True
    b = {"mode": "hotm", "status": "build_partiel", "video_id": "h1", "channel_id": "UCH", "hunter_mode": True, "sjw": {}}
    p = R.preuves_builds([{**b, "video_id": f"h{i}", "channel_id": f"UC{i}"} for i in range(5)])
    assert R.valeurs(p)["hotm"]["sjw"][0] is False                # 5 builds sans SJW de 5 chaînes
    bot = {"mode": "bot", "status": "build_partiel", "video_id": "b1", "channel_id": "UCB", "sjw": {"weapons": [{"id": "x"}], "artifacts": [], "cores": []}}
    assert R.valeurs(R.preuves_builds([bot]))["bot"]["sjw"] == (True, ["b1"])
    assert R.preuves_builds([{**bot, "status": "pas_de_build"}])["bot"]["sjw"]["vu"] == {}


def test_appliquer_ne_remplace_pas_une_valeur_connue_par_false_et_garde_la_source():
    regles = {"week": W, "modes": {"poc": None, "bot": {"sjw": True, "successor": None}, "gb": None, "hotm": None}, "sources": {"bot": "Alexis"}}
    assert R.appliquer(regles, {"bot": {"sjw": (False, ["a"] * 5), "successor": (False, list("abcde"))}}, "2026-11-15")
    assert regles["modes"]["bot"]["sjw"] is True                  # un false déduit ne contredit pas une valeur connue
    assert regles["modes"]["bot"]["successor"] is False and "déduit, à vérifier" in regles["modes"]["bot"]["notes_deduit"]
    assert regles["modes"]["bot"]["deduit"]["source"] == "écrans" and "source" not in regles["modes"]["bot"]
    assert regles["sources"] == {"bot": "Alexis"}
    # idempotent : même déduction, rien ne change (la date de calcul reste)
    avant = json.dumps(regles, sort_keys=True)
    assert not R.appliquer(regles, {"bot": {"successor": (False, list("abcde"))}}, "2026-11-20")
    assert json.dumps(regles, sort_keys=True) == avant
    # un true déduit remplace null
    assert R.appliquer(regles, {"gb": {"sjw": (True, ["v1"])}}, "2026-11-15")
    assert regles["modes"]["gb"]["sjw"] is True and regles["modes"]["gb"]["source"] == "écrans"
    assert regles["modes"]["gb"]["deduit"] == {"source": "écrans", "video_ids": ["v1"], "elements": {"sjw": True}, "date": "2026-11-15"}


def test_migration_bot_season_et_challenge():
    r = {"week": "2026-11-12", "modes": {"poc": None, "bot_season": {"sjw": True}, "bot_challenge": None, "gb": None, "hotm": None}}
    assert R.migrer(r) and r["modes"]["bot"] == {"sjw": True} and "bot_season" not in r["modes"] and list(r["modes"]) == ["poc", "bot", "gb", "hotm"]
    r = {"week": "2026-11-05", "modes": {"poc": None, "bot_season": None, "bot_challenge": {"sjw": False}, "gb": None, "hotm": None}}
    R.migrer(r)
    assert r["modes"]["bot"]["sjw"] is False and "relevé du 05/11 rangé en challenge" in r["modes"]["bot"]["notes"]
    assert not R.migrer(r)                                       # idempotent


def test_classement_ecrit_les_regles_deduites_sans_fichier_inutile():
    d = preparer([lec("g1", "UCG", "gb", 150, score_source="debut-fin",
                      detail={"player_score": 1, "successeur_present": True, "hunter_ranks_lus": 6})])
    calculer(W, d, charger_config(), HORLOGE)
    regles = json.loads((d.data / "rules" / f"{W}.json").read_text(encoding="utf-8"))
    assert regles["modes"]["gb"]["sjw"] is True and regles["modes"]["gb"]["successor"] is True
    avant = (d.data / "rules" / f"{W}.json").read_text(encoding="utf-8")
    calculer(W, d, charger_config(), datetime(2026, 11, 16, 19, 0, tzinfo=timezone.utc))
    assert (d.data / "rules" / f"{W}.json").read_text(encoding="utf-8") == avant      # relancé un autre jour : fichier identique
    d = preparer([lec("x", "UCX", "poc", 5 * T, score_source="titre", exact=False, confidence="a_verifier")])
    calculer(W, d, charger_config(), HORLOGE)
    assert not (d.data / "rules" / f"{W}.json").exists()           # aucune preuve : pas de fichier


# --- libellés inconnus ---------------------------------------------------------------------------------------------------

TEXTE_JA = "結果\nスコア 1,234,567,890\nランク1 123,456,789\nランク2 98,765,432\n時間 03:00\n"


def test_ressemble_a_un_ecran_de_score():
    assert LI.ressemble_score(TEXTE_JA)
    assert LI.ressemble_score("プレイ時間 02:57.123")                 # chrono mm:ss.mmm
    assert not LI.ressemble_score("1,234,567,890 seul sur une ligne\n et du texte")
    assert not LI.ressemble_score("")
    assert not LI.a_garder(TEXTE_JA, "gb_results", [])               # libellé reconnu : rien à collecter


def test_garder_quota_espacement_et_fichiers():
    with tempfile.TemporaryDirectory() as tmp:
        from PIL import Image
        png = Path(tmp) / "x.png"
        Image.new("RGB", (1920, 1080), (10, 20, 30)).save(png)
        deja = []
        for t in (10, 11, 14, 20, 30):
            if LI.a_garder(TEXTE_JA, None, deja) and LI.espace(t, deja):
                LI.garder(tmp, "vidJA", t, TEXTE_JA, png)
                deja.append(t)
        assert deja == [10, 14, 20]                                  # 11 trop proche, 30 au-delà de 3 images
        d = Path(tmp) / "docs" / "essais" / "ocr" / "libelles_inconnus"
        assert sorted(p.name for p in d.iterdir()) == ["vidJA_10.jpg", "vidJA_10.txt", "vidJA_14.jpg", "vidJA_14.txt", "vidJA_20.jpg", "vidJA_20.txt"]
        assert (d / "vidJA_10.txt").read_text(encoding="utf-8") == TEXTE_JA
        assert Image.open(d / "vidJA_10.jpg").size[0] <= 1600


def test_pousser_ajoute_le_dossier_des_libelles_inconnus():
    import pc
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as depot:
        run = lambda *a, cwd=tmp: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)
        run("init", "--bare", "-b", "main", cwd=depot)
        run("init", "-b", "main")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        run("remote", "add", "origin", depot)
        (Path(tmp) / "data").mkdir()
        (Path(tmp) / "data" / "a.json").write_text("{}", encoding="utf-8")
        run("add", "-A")
        run("commit", "-m", "init")
        run("push", "-u", "origin", "main")
        LI.garder(tmp, "vidJA", 10, TEXTE_JA, Path(tmp) / "absent.png")        # image absente : le texte est gardé quand même
        assert pc.Git(tmp).pousser("test") is True
        vus = run("ls-tree", "-r", "--name-only", "HEAD").stdout.split()
        assert "docs/essais/ocr/libelles_inconnus/vidJA_10.txt" in vus


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
    print("ok")


# --- v25 ------------------------------------------------------------------------------------------------------------------

def test_v25_elements_de_sjw_par_les_builds_found():
    b = {"mode": "bot", "status": "build_partiel", "video_id": "b1", "channel_id": "UCB", "sjw": {},
         "found": {"sjw_skills": True, "blessings": False, "shadows": True}}
    v = R.valeurs(R.preuves_builds([b]))
    assert v["bot"]["sjw_skills"] == (True, ["b1"]) and v["bot"]["shadows"] == (True, ["b1"]) and "blessings" not in v["bot"]
    assert R.valeurs(R.preuves_builds([{**b, "status": "pas_de_build"}])) == {}


def test_v25_sjw_false_entraine_skills_et_blessings_mais_pas_l_inverse():
    regles = {"week": W, "modes": {"poc": None, "bot": {"sjw": False, "shadows": True}, "gb": None, "hotm": {"sjw": True}}}
    assert R.appliquer(regles, {}, "2026-11-15")
    bot = regles["modes"]["bot"]
    assert bot["sjw_skills"] is False and bot["blessings"] is False and bot["shadows"] is True
    assert "déduit de sjw: false" in bot["notes_deduit"] and bot["deduit"]["elements"] == {"sjw_skills": False, "blessings": False}
    assert "sjw_skills" not in regles["modes"]["hotm"]                      # sjw true n'implique rien
    assert not R.appliquer(regles, {}, "2026-11-20")                        # idempotent
    # une valeur déjà connue n'est pas écrasée
    regles = {"week": W, "modes": {"bot": {"sjw": False, "blessings": True}}}
    R.appliquer(regles, {}, "2026-11-15")
    assert regles["modes"]["bot"]["blessings"] is True and regles["modes"]["bot"]["sjw_skills"] is False


def test_v25_absence_de_sjw_au_bot_seulement_par_la_zone_vide():
    bot = lambda i, vide: lec(f"b{i}", f"UC{i}", "bot", 5 * T, detail={"armes_sjw_vides": vide})
    cinq = [bot(i, True) for i in range(5)]
    assert R.valeurs(R.preuves_lectures(cinq))["bot"]["sjw"][0] is False
    assert "bot" not in R.valeurs(R.preuves_lectures(cinq[:4]))              # 4 chaînes : inconnu
    assert R.valeurs(R.preuves_lectures(cinq + [bot(9, False)]))["bot"]["sjw"][0] is True   # une icône vue l'emporte
    assert R.valeurs(R.preuves_lectures([lec("x", "UCX", "bot", 5 * T)])) == {}            # zone non lue : rien


def test_v25_zone_vide():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 200), (30, 40, 90))
    assert R.zone_vide(im, [0.1, 0.1, 0.5, 0.5]) is True
    ImageDraw.Draw(im).rectangle([60, 40, 120, 90], fill=(240, 220, 50))        # une icône dans la zone
    assert R.zone_vide(im, [0.1, 0.1, 0.5, 0.5]) is False
    assert R.zone_vide(im, None) is None and R.zone_vide(None, [0, 0, 1, 1]) is None
    assert R.zone_vide(im, [0.1, 0.1, 0.1, 0.1]) is None                        # zone minuscule : inconnu
