"""v17 : repli sur le contrôle sans Hunter Rank (6 rangs lus mais somme fausse / Player's Score illisible) ; plausibilité des Points HUD ko/pt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_ecrans
import pc
from test_gb import meta as meta_gb
from test_tri34 import CONFIG
from test_tri34 import SEM
from test_v15 import RESULTS_PT, Z_PT, HUD_KO_REEL, HUD_PT, RESULTS_KO, Z_KO, VIDE


def _un(zones, ts=(231, 232), hud=None):
    m = {**meta_gb("v"), "lang": "ko", "mode_guess": ["gb"]}
    ls = [ocr_ecrans.lectures_depuis_texte(RESULTS_KO, m, CONFIG, "video-complete", t, zones)[0] for t in ts] + (hud or [])
    (res,) = [l for l in pc.fusionner_ecrans([], "v", ls, CONFIG) if l["score"] is not None]
    return res


def test_repli_somme_fausse():
    # un Hunter Rank mal lu mais toujours décroissant : somme ≠ Final, 2 images identiques -> repli, sûr
    res = _un({**Z_KO, "rang_3": "302,730,549,500"})
    assert res["confidence"] == "sur" and "contrôle sans Hunter Rank" in res["notes"] and res["detail"]["hunter_ranks_lus"] == 6
    # rangs non décroissants : le repli échoue aussi, les deux contrôles sont notés
    bad = _un({**Z_KO, "rang_3": "902,730,549,500"})
    assert bad["confidence"] == "a_verifier" and any(n.startswith("contrôle GB") for n in bad["notes"])
    assert "contrôle sans Hunter Rank : Hunter Rank lus non décroissants" in bad["notes"]
    # une seule image : Rage Count lu une fois -> a_verifier
    une = _un({**Z_KO, "rang_3": "302,730,549,500"}, ts=(231,))
    assert une["confidence"] == "a_verifier"


def test_repli_player_score_illisible():
    # sans HUD : Player's Score illisible reste bloquant ; la somme ne peut pas être faite
    sans = _un({**Z_KO, "joueur": ""})
    assert sans["confidence"] == "a_verifier" and "contrôle sans Hunter Rank : Player's Score illisible" in sans["notes"]
    # avec HUD confirmant le Final Score (Points ≤ Final ≤ ×1,02) : accepté
    m = {**meta_gb("v"), "lang": "ko", "mode_guess": ["gb"]}
    hud = ocr_ecrans.lectures_depuis_texte(HUD_KO_REEL.replace("10.375,798,058,160", "10,661,000,000,000"), m, CONFIG, "video-complete", 200,
                                           {**VIDE, "hud_chrono": "3.18", "hud_points": "10,661,000,000,000", "hud_rage": "125"})
    hud = ocr_ecrans.regrouper_hud(hud, CONFIG)
    ok = _un({**Z_KO, "joueur": ""}, hud=hud)
    assert ok["confidence"] == "sur" and "contrôle sans Hunter Rank" in ok["notes"]


def test_points_plausibles():
    p = ocr_ecrans.points_plausibles
    assert p("10.375.798.058.160", "ko", CONFIG)[0] and p("7.884.144.289.064", "pt", CONFIG)[0]
    ok, raison = p("10375790058", "ko", CONFIG)               # cas MJ2iz5TFmvM : groupes perdus
    assert not ok and "groupes" in raison
    assert not p("7288064", "pt", CONFIG)[0]                   # sous 1e9
    assert p("1,000,000,000,000,000", "ko", CONFIG)[0] and not p("10,000,000,000,000,000", "ko", CONFIG)[0]     # plafond 1e15
    assert not p("1593669209", "en", CONFIG)[0] and p("1593,669,209", "en", CONFIG)[0]    # v18 : groupes exigés aussi en anglais
    assert not p("10,37,579,0058", "ko", CONFIG)[0]            # groupes ≠ 3 chiffres


def test_hud_points_rejetes_ko_pt():
    m = {**meta_gb("mj"), "mode_guess": ["gb"]}
    lu = ocr_ecrans.lire_gb_combat(HUD_PT.replace("7.884.144.289.064", "10375790058"), CONFIG)       # groupes perdus
    assert lu["langue"] == "pt" and lu["points"] is None and "groupes" in lu["points_rejet"]
    assert ocr_ecrans.lire_gb_combat(HUD_PT, CONFIG)["points"] == 7884144289064
    # zone du HUD coréen : Points sans groupes rejetés, jamais des dégâts provisoires
    ecran = {"langue": "ko", "chrono": None}
    ocr_ecrans._appliquer_zones_hud(ecran, {**VIDE, "hud_chrono": "3.18", "hud_points": "10375790058", "hud_rage": "125"}, CONFIG)
    assert ecran.get("points") is None and "groupes" in ecran["points_rejet"] and ecran["chrono"] == 3.18
    (l2,) = ocr_ecrans.lectures_depuis_texte(HUD_PT, m, CONFIG, "video-complete", 213)
    assert l2["detail"]["hud_points"] == 7884144289064


def test_v18_boss_alias_et_ecart_titre_ecran():
    import classement
    ids = {classement.boss_id(n, CONFIG) for n in ("Giant Statue", "Estátua Gigante", "Estatua de Pedra  Gigante", "거대 석상")}
    assert ids == {"giant_statue"} and classement.boss_id("Autre", CONFIG) == "Autre"
    m = {**meta_gb("v"), "lang": "ko", "mode_guess": ["gb"]}
    ls = [ocr_ecrans.lectures_depuis_texte(RESULTS_KO, m, CONFIG, "video-complete", t, Z_KO)[0] for t in (231, 232)]
    titre = {**ls[0], "score": 159, "score_source": "titre", "damage": None, "notes": [], "detail": {}}
    sortie = pc.fusionner_ecrans([titre], "v", ls, CONFIG)
    (res,) = [l for l in sortie if l["score"] is not None]
    assert res["score"] == 160 and res["confidence"] == "sur" and "écart titre/écran : titre 159" in res["notes"]
    ok = pc.fusionner_ecrans([{**titre, "score": 160}], "v", ls, CONFIG)
    assert not any("écart titre/écran" in n for l in ok for n in l["notes"])


def test_v18_record_leve_alerte_reset_de_la_video():
    import classement
    from datetime import timedelta
    from semaine import bornes
    _, fin = bornes(SEM)
    pub = "2026-11-12T03:00:00Z"
    note = "publiée juste après le reset : semaine précédente ?"
    base = {"video_id": "awb", "published_at": pub, "notes": [note], "confidence": "sur"}
    rec = {**base, "score_source": "record", "detail": {"time_left": "6d 22h"}, "notes": [note]}
    res = {**base, "score_source": "debut-fin", "detail": {}, "notes": [note]}
    autre = {**base, "video_id": "zzz", "score_source": "debut-fin", "detail": {}, "notes": [note]}
    gardees, prec = classement.controler_saison_record([rec, res, autre], SEM, CONFIG)
    assert not prec and rec["notes"] == [] and res["notes"] == [] and autre["notes"] == [note]


def test_v19_repli_assoupli_hud():
    import ecrans
    base = {"stage": "Estátua Gigante", "damage": 3096765357626, "score": 137,
            "detail": {"play_time": "03:00", "rc_images": 5, "final_images": 3, "player_score": 1688587202020, "successor_score": 0,
                       "hunter_ranks": [545355914947, 459719757408, 160594165676, 924330651491, 95702114632, 25475511452],
                       "votes": {"rage_count": [[137, 5]]}}}
    hud = {"damage": 3094382613814}
    infos = []
    ok, pb = ecrans.controle_results_sans_hunter_rank(base, hud, CONFIG, joueur_optionnel=True, infos=infos)
    assert ok and infos == ["Hunter Rank incohérents ignorés (HUD)"]                       # cas Oj_-5x6700s
    # sans HUD : condition 4 obligatoire
    ok, pb = ecrans.controle_results_sans_hunter_rank(base, None, CONFIG, joueur_optionnel=True, infos=[])
    assert not ok and any("non décroissants" in p for p in pb)
    # RC lu sur 2 images seulement, ou lecture discordante : non assoupli
    deux = {**base, "detail": {**base["detail"], "rc_images": 2}}
    assert not ecrans.controle_results_sans_hunter_rank(deux, hud, CONFIG, infos=[])[0]
    disc = {**base, "detail": {**base["detail"], "votes": {"rage_count": [[137, 5], [13, 1]]}}}
    assert not ecrans.controle_results_sans_hunter_rank(disc, hud, CONFIG, infos=[])[0]
    # HUD qui ne confirme pas le Final Score (> 2 %) : non assoupli
    assert not ecrans.controle_results_sans_hunter_rank(base, {"damage": 2000000000000}, CONFIG, infos=[])[0]
    # condition 1 en défaut (boss illisible) : non assoupli
    assert not ecrans.controle_results_sans_hunter_rank({**base, "stage": None}, hud, CONFIG, infos=[])[0]


def test_v20_chrono_hud_deduit():
    """SPEC v19 : Points d'un HUD au chrono illisible (≤ 2 s après un HUD au chrono ≤ 5 s) = dernier Points ; cas T5dR6iJAn-Y."""
    m = {**meta_gb("t5"), "lang": "pt", "mode_guess": ["gb"]}
    ref = "(®) 0.80\nPontos 7288064\nNúmero de Fúrias do Chefão 120 WARNING\n"
    def sc(pts): return f"Pontos {pts}\nNúmero de Fúrias do Chefão 120 WARNING\n"
    def run(sans, t_ref=213, t_sc=214, ts=(229, 231, 233), extra=()):
        ls = ocr_ecrans.lectures_depuis_texte(ref, m, CONFIG, "video-complete", t_ref)
        ls += ocr_ecrans.lectures_depuis_texte(sc(sans), m, CONFIG, "video-complete", t_sc) if sans else []
        ls += [ocr_ecrans.lectures_depuis_texte(RESULTS_PT, m, CONFIG, "video-complete", t, {**Z_PT, "joueur": ""})[0] for t in ts]
        res = [l for l in pc.fusionner_ecrans([], "t5", ls + list(extra), CONFIG) if l["score"] is not None]
        assert len(res) == 1
        return res[0], ls
    ok, ls = run("7,905,911007,261")                                             # séparateur perdu, toléré
    assert ls[1]["detail"]["ecran"] == "combat_sans_chrono" and ls[1]["detail"]["hud_points"] == 7905911007261
    assert ok["score"] == 156 and ok["confidence"] == "sur" and "chrono HUD déduit (t=214)" in ok["notes"] and "contrôle sans Hunter Rank" in ok["notes"]
    # Points hors de la fenêtre du Final Score (> Final) : ignorés
    assert run("9,905,911,007,261")[0]["confidence"] == "a_verifier"
    # trop tard (> 2 s après le HUD de référence) : ignoré
    assert run("7,905,911,007,261", t_sc=216)[0]["confidence"] == "a_verifier"
    # l'écran Results précède le HUD sans chrono : ignoré
    assert run("7,905,911,007,261", t_sc=214, ts=(212, 213, 233))[0]["confidence"] == "a_verifier"
    # Points non plausibles (sans séparateurs) : ignorés
    assert run("7905911007261")[0]["confidence"] == "a_verifier"
    # idempotent : refusionner les lectures déjà fusionnées garde la note une seule fois
    res, ls = run("7,905,911,007,261")
    deux = [l for l in pc.fusionner_ecrans([], "t5", pc.fusionner_ecrans([], "t5", ls + [], CONFIG), CONFIG) if l["score"] is not None][0]
    assert deux["confidence"] == "sur" and deux["notes"].count("chrono HUD déduit (t=214)") == 1


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
