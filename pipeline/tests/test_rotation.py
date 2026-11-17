"""SPEC_ROTATION v1 : détection prêt / en recharge, doublons, t_run, jauge, portrait, confiance, bornes, passage d'une vidéo, branchement PC."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest

pytest.importorskip("numpy")
from PIL import Image

import rotation as R

CFG = dict(R.charger_config(), detection="luminance", planche=False)   # les tests de luminance restent ; l'OCR a ses tests ci-dessous
Z = {"skill_1": [0.70, 0.80, 0.78, 0.95], "skill_2": [0.80, 0.80, 0.88, 0.95], "ultimate": [0.90, 0.60, 0.98, 0.75],
     "sjw_skill_1": [0.05, 0.80, 0.12, 0.95], "core": [0.45, 0.02, 0.55, 0.05], "portrait": [0.02, 0.30, 0.10, 0.50], "qte": [0.4, 0.4, 0.6, 0.5]}
HUNTER_DB = {"hunters": {"h1": {"skills": [{"type": "skill_1", "cooldown": 8.0}, {"type": "skill_2", "cooldown": 16.0}, {"type": "ultimate", "cooldown": 45.0}]}},
             "sjw_skills": {"double-slash": {"cooldown": 10.0}}}


def image(boutons=None, jauge=0.0, portrait=120, qte=0, taille=(640, 360)):
    """Image synthétique 16:9 : fond noir, boutons de luminance donnée, jauge (part remplie), portrait uni."""
    im = Image.new("L", taille, 0)
    w, h = taille
    for nom, lum in (boutons or {}).items():
        x0, y0, x1, y1 = Z[nom]
        im.paste(lum, (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    x0, y0, x1, y1 = Z["core"]
    im.paste(255, (round(x0 * w), round(y0 * h), round(x0 * w + jauge * (x1 - x0) * w), round(y1 * h)))
    x0, y0, x1, y1 = Z["portrait"]
    im.paste(portrait, (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    x0, y0, x1, y1 = Z["qte"]
    im.paste(qte, (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    return im.convert("RGB")


def serie(f, duree=6.0, fps=10):
    return [(round(i / fps, 3), f(i / fps)) for i in range(int(duree * fps))]


# --- boutons prêt / en recharge ----------------------------------------------------------------------------------------------

def test_bouton_pret_puis_en_recharge_date_a_la_premiere_image_en_recharge():
    s = [(t, 60.0 if 1.0 <= t < 3.0 or 4.0 <= t < 5.5 else 200.0) for t, _ in serie(lambda t: 0)]
    assert R.transitions_recharge(R.etats_bouton(s, CFG)) == [1.0, 4.0]


def test_une_image_sombre_isolee_n_est_pas_une_utilisation():
    s = [(t, 60.0 if abs(t - 2.0) < 1e-6 else 200.0) for t, _ in serie(lambda t: 0)]
    assert R.transitions_recharge(R.etats_bouton(s, CFG)) == []


def test_bouton_qui_ne_varie_pas_n_est_jamais_releve():
    assert R.transitions_recharge(R.etats_bouton([(t, 200.0) for t, _ in serie(lambda t: 0)], CFG)) == []
    assert R.transitions_recharge(R.etats_bouton([], CFG)) == []


def test_luminance_et_remplissage_sur_images_synthetiques():
    assert R.luminance(image({"skill_1": 200}), Z["skill_1"]) == 200 and R.luminance(image({"skill_1": 60}), Z["skill_1"]) == 60
    assert R.remplissage(image(jauge=1.0), Z["core"]) > 0.95 and R.remplissage(image(jauge=0.0), Z["core"]) < 0.05


# --- doublons, t_run -------------------------------------------------------------------------------------------------------

def test_deux_detections_a_moins_de_0_5_s_sont_un_seul_evenement():
    e = lambda t, slot="skill_1": {"t": t, "slot": slot, "hunter": "h1"}
    assert [x["t"] for x in R.fusionner_doublons([e(2.0), e(2.3), e(2.0, "skill_2"), e(3.0)])] == [2.0, 2.0, 3.0]
    assert [x["t"] for x in R.fusionner_doublons([e(2.0), e(2.5)])] == [2.0, 2.5]          # 0,5 s exactement : deux événements


def test_t_run_et_duree():
    run = R.construire_run(1, 4.0, 23.9, [{"t": 6.5, "hunter": "sjw", "slot": "sjw_skill_1", "source": "hud-recharge", "confidence": "sur"},
                                          {"t": 9.0, "hunter": "h1", "slot": "tag", "trigger": "qte", "source": "portrait"}], ["bornes-incertaines"])
    assert (run["run_start_t"], run["run_end_t"], run["duration_s"]) == (4.0, 23.9, 19.9)
    assert [(e["t"], e["t_run"], e["trigger"]) for e in run["events"]] == [(6.5, 2.5, None), (9.0, 5.0, "qte")]
    assert run["events"][0]["skill_id"] is None and run["limites"] == ["bornes-incertaines"]


# --- relevé d'une run -----------------------------------------------------------------------------------------------------

def _frames():
    def f(t):
        return image({"skill_1": 60 if 1.0 <= t < 3.0 else 200, "skill_2": 200, "sjw_skill_1": 60 if 2.0 <= t < 4.0 else 200},
                     jauge=1.0 if t < 3.5 else 0.0, portrait=120 if t < 3.0 else 40)
    return serie(f)


def test_releve_complet_sur_images_synthetiques():
    ev, lim = R.releves_run(_frames(), Z, CFG, HUNTER_DB, skills_sjw={"sjw_skill_1": "double-slash"})
    par = {(e["slot"], e["hunter"]): e for e in ev}
    assert ("skill_1", "inconnu") in par and par[("skill_1", "inconnu")]["t"] == 1.0           # aucun chasseur identifié sans carte de référence
    assert par[("sjw_skill_1", "sjw")]["t"] == 2.0 and par[("sjw_skill_1", "sjw")]["skill_id"] == "double-slash"
    assert any(e["slot"] == "tag" and e["t"] == 3.0 and e["trigger"] == "inconnu" for e in ev)
    assert any(e["slot"] == "core" and e["t"] == 3.5 for e in ev)
    assert "chasseurs-inconnus" in lim
    assert not any(e["slot"] == "skill_2" for e in ev)


def test_bannière_qte_donne_trigger_qte():
    def f(t):
        return image({"skill_1": 200}, portrait=120 if t < 3.0 else 40, qte=200 if t >= 3.0 else 0)
    ev, _ = R.releves_run(serie(f), Z, CFG, HUNTER_DB)
    assert [e["trigger"] for e in ev if e["slot"] == "tag"] == ["qte"]


def test_cooldown_read_et_ocr():
    assert R.lire_recharge("7.3") == 7.3 and R.lire_recharge("12") == 12.0 and R.lire_recharge("x") is None
    ev, _ = R.releves_run(_frames(), Z, CFG, HUNTER_DB, ocr=lambda im: "8.2")
    assert next(e for e in ev if e["slot"] == "skill_1")["cooldown_read"] == 8.2


# --- confiance ----------------------------------------------------------------------------------------------------------------

def _e(t, lu=None, hunter="h1", slot="skill_1", skill_id=None):
    return {"t": t, "hunter": hunter, "slot": slot, "skill_id": skill_id, "cooldown_read": lu, "source": "hud-recharge"}


def test_confiance_par_la_recharge_de_la_base():
    ev = R.evaluer_confiance([_e(1, 8.4), _e(20, 12.0), _e(40, None), _e(41.0, None, hunter="inconnu")], HUNTER_DB)
    assert [e["confidence"] for e in ev] == ["sur", "a_verifier", "sur", "a_verifier"]


def test_recharge_relancee_trop_tot_est_a_verifier():
    ev = R.evaluer_confiance([_e(1.0), _e(5.0)], HUNTER_DB)                 # recharge 8 s : 2e utilisation à 4 s d'écart
    assert [e["confidence"] for e in ev] == ["sur", "a_verifier"]
    ev = R.evaluer_confiance([_e(1.0), _e(8.5)], HUNTER_DB)                  # 7,5 s ≥ 8 − 1 : respectée
    assert ev[1]["confidence"] == "sur"


def test_sjw_confiance_par_skill_id_et_base_absente():
    ev = R.evaluer_confiance([_e(1, 10.5, hunter="sjw", slot="sjw_skill_1", skill_id="double-slash"), _e(2, 3.0, hunter="sjw", slot="sjw_qte")], HUNTER_DB)
    assert [e["confidence"] for e in ev] == ["sur", "a_verifier"]


# --- critères d'acceptation BOT ------------------------------------------------------------------------------------------------

def test_controles_bot():
    run = R.construire_run(1, 4.0, 23.9, [{"t": 6.0, "hunter": "sjw", "slot": "sjw_skill_1", "source": "hud-recharge", "confidence": "sur"},
                                           {"t": 7.0, "hunter": "h1", "slot": "skill_1", "source": "hud-recharge", "confidence": "sur"},
                                           {"t": 9.0, "hunter": "h1", "slot": "tag", "source": "portrait", "trigger": "inconnu"}], [])
    c = {n: ok for n, ok, _ in R.controles_bot(R.fichier({"video_id": "v", "week": "w", "mode": "bot"}, [run]), 19.926, 38.0, (9.281, 14.986), HUNTER_DB)}
    assert all(v is True for v in c.values()), c
    c = {n: ok for n, ok, _ in R.controles_bot(R.fichier({"video_id": "v", "week": "w", "mode": "bot"}, [run]), 25.0, 20.0, (9.281, 30.0), HUNTER_DB)}
    assert c["durée = chrono ± 0,5 s"] is False and c["fin avant la composition"] is False and c["phases du Results entre les bornes"] is False
    assert R.controles_bot({"runs": [R.construire_run(1, None, None, [], ["hud-non-trouve"])]})[0][1] is None


# --- passage d'une vidéo (faux outils : images synthétiques) ---------------------------------------------------------------------

class Outils:
    def __init__(self, f, taille=(640, 360)):
        self.f, self.taille, self.appels = f, taille, []

    def images(self, chemin, segments, dossier, prefixe="f", hauteur=None):
        sortie = []
        for k, (debut, duree, pas) in enumerate(segments):
            self.appels.append((debut, duree, pas, hauteur))
            n = int(round(duree / pas))
            for i in range(n):
                t = round(debut + i * pas, 3)
                p = Path(dossier) / f"{prefixe}{k}_{i:05d}.png"
                self.f(t, self.taille).save(p)
                sortie.append((t, p))
        return sortie


def _ctx(**kw):
    return {"video_id": "wJ9CwjKwyco", "week": "2026-11-12", "mode": "bot", "gate": None, "run_id": "bot-2026-11-12-wJ9CwjKwyco", "ligne": {},
            "t_result": 12.0, "chrono_s": 8.0, "t_composition": 30.0, "phases": [3.0, 6.0], **kw}


def _hud(t, taille):
    return image({"skill_1": 60 if 4.0 <= t < 6.0 else 200, "sjw_skill_1": 60 if 6.0 <= t < 8.0 else 200} if t >= 2.0 else {}, portrait=120, taille=taille)


def test_passage_video_ecrit_le_fichier_de_la_spec(tmp_path):
    cfg = {**CFG, "zones": Z, "fps": 10, "scan_pas_s": 0.5}
    o = Outils(_hud)
    with tempfile.TemporaryDirectory() as tmp:
        etat = R.passage_video(o, "v.mp4", _ctx(), cfg, HUNTER_DB, tmp, racine=tmp_path)
    assert etat == "fait" and o.appels[0][3] == 720 and o.appels[1][2] == pytest.approx(0.1)             # balayage puis 10 images/s en 720p
    d = json.loads((tmp_path / "data/rotations/2026-11-12/bot/wJ9CwjKwyco.json").read_text(encoding="utf-8"))
    assert set(d) == {"spec", "video_id", "week", "mode", "gate", "run_id", "runs"} and d["spec"] == 1
    r = d["runs"][0]
    assert (r["run_start_t"], r["run_end_t"]) == (2.0, 12.0) and r["duration_s"] == 10.0
    assert [(e["slot"], e["t"], e["t_run"]) for e in r["events"] if e["slot"] != "tag"] == [("skill_1", 4.0, 2.0), ("sjw_skill_1", 6.0, 4.0)]
    rap = (tmp_path / "data/rotations/2026-11-12/_rapport.md").read_text(encoding="utf-8")
    assert "bot · wJ9CwjKwyco · run 1" in rap and "ÉCHEC : durée = chrono ± 0,5 s" in rap and "OK : phases du Results entre les bornes" in rap


def test_hud_non_calibre_limite_et_recadrages_de_calibration(tmp_path):
    with tempfile.TemporaryDirectory() as tmp:
        non_calibre = dict(CFG, zones={k: None for k in CFG["zones"]})                                  # la config réelle est calibrée (v2)
        etat = R.passage_video(Outils(_hud), "v.mp4", _ctx(), non_calibre, HUNTER_DB, tmp, racine=tmp_path)
    assert etat == "absent"
    r = json.loads((tmp_path / "data/rotations/2026-11-12/bot/wJ9CwjKwyco.json").read_text(encoding="utf-8"))["runs"][0]
    assert r["limites"] == ["hud-non-trouve"] and r["events"] == []
    crops = list((tmp_path / "data/rotations/2026-11-12/bot/_crops").glob("*.jpg"))
    assert crops and all(Image.open(c).size[0] <= 960 for c in crops)                                      # jamais l'image entière


def test_format_non_16_9(tmp_path):
    with tempfile.TemporaryDirectory() as tmp:
        etat = R.passage_video(Outils(_hud, (640, 480)), "v.mp4", _ctx(), {**CFG, "zones": Z}, HUNTER_DB, tmp, racine=tmp_path)
    assert etat == "absent"
    d = json.loads((tmp_path / "data/rotations/2026-11-12/bot/wJ9CwjKwyco.json").read_text(encoding="utf-8"))
    assert d["runs"][0]["limites"] == ["format"] and d["runs"][0]["events"] == []


def test_bornes_incertaines_sans_results_lu(tmp_path):
    with tempfile.TemporaryDirectory() as tmp:
        R.passage_video(Outils(lambda t, tl: _hud(t, tl) if t < 9.0 else image(taille=tl)), "v.mp4", _ctx(t_result=None), {**CFG, "zones": Z}, HUNTER_DB, tmp,
                        racine=tmp_path, duree_s=14)
    r = json.loads((tmp_path / "data/rotations/2026-11-12/bot/wJ9CwjKwyco.json").read_text(encoding="utf-8"))["runs"][0]
    assert "bornes-incertaines" in r["limites"] and r["run_end_t"] is not None


# --- sélection et branchement PC -------------------------------------------------------------------------------------------------

def test_selection_top3_bot_et_etat_pc_rotation():
    sem = "2026-11-12"
    assert R.a_traiter(sem, {}) == ["a-923ClD9Rc", "Lt84IhMjBvM", "wJ9CwjKwyco"]      # v34 : ordre du fichier (X SLA 19.926 3e)
    fait = {"wJ9CwjKwyco": {"pc": {"rotation": "fait", "rotation_version": CFG["version"]}}, "a-923ClD9Rc": {"pc": {"rotation": "erreur", "rotation_version": CFG["version"]}}}
    assert R.a_traiter(sem, fait) == ["Lt84IhMjBvM"]
    ancienne = {"wJ9CwjKwyco": {"pc": {"rotation": "absent", "rotation_version": 0}}}                   # version de la calibration augmentée : refait
    assert "wJ9CwjKwyco" in R.a_traiter(sem, ancienne)
    assert R.a_traiter(sem, {}, cfg={**CFG, "budget_par_mode": 2}) == ["a-923ClD9Rc", "Lt84IhMjBvM"]
    assert R.a_traiter(sem, {}, cfg={**CFG, "modes": ["poc"], "top": 3}) != []                           # un autre mode se branche par la configuration


def test_traiter_images_appelle_apres_sur_la_video_deja_telechargee():
    import pc
    from test_tri34 import OutilsImages
    config = pc.charger_config()
    o = OutilsImages({})
    vu = []
    etat = {"tri3": "fait", "tri4": "fait"}
    pc.traiter_images("wJ9CwjKwyco", {"duration": "PT49S", "mode_guess": ["bot"], "lang": "en"}, o, config, [], etat, "2026-11-17",
                      apres=lambda chemin, tmp: vu.append((Path(chemin).name, Path(tmp).exists())))
    assert vu == [("wJ9CwjKwyco", True)] and [a for a in o.appels if a[0] == "dl"] == [("dl", "wJ9CwjKwyco")]          # un seul téléchargement
    assert not any(a[0] == "img" for a in o.appels)                                                         # tris déjà faits : aucune image relue


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


def test_ocr_recharge_lit_un_chiffre_avec_le_vrai_tesseract(tmp_path):
    import shutil
    import subprocess
    if not shutil.which("tesseract"):
        import pytest
        pytest.skip("tesseract absent")
    from PIL import Image, ImageDraw, ImageFont

    class Outils:
        def ocr(self, png, langues=None, psm=6, timeout=120, extra=None):
            return subprocess.run(["tesseract", str(png), "stdout", "-l", langues, "--psm", str(psm), *(extra or [])],
                                  capture_output=True, text=True, timeout=timeout).stdout

    for texte, attendu in (("5", 5.0), ("9", 9.0), ("12", 12.0), ("60", 60.0)):                       # bouton de 46 x 50 px, chiffre blanc au centre (HUD 720p)
        im = Image.new("RGB", (46, 50), (60, 70, 80))
        ImageDraw.Draw(im).text((23, 25), texte, fill=(255, 255, 255), font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16), anchor="mm")
        lu = R.ocr_recharge(Outils(), tmp_path)(im)
        assert R.lire_recharge(lu) == attendu, (texte, lu)
    assert not list(tmp_path.glob("_recharge_*.png"))


def test_ocr_recharge_ne_leve_jamais(tmp_path):
    from PIL import Image

    class Casse:
        def ocr(self, *a, **k):
            raise RuntimeError("tesseract")
    assert R.ocr_recharge(Casse(), tmp_path)(Image.new("RGB", (10, 10))) == ""


def test_planche_zones_ecrit_planche_et_series(tmp_path):
    imgs = {t: Image.new("RGB", (1280, 720), (40 + int(t) * 10,) * 3) for t in (0.0, 0.5, 1.0)}
    cfg = dict(CFG, planche=True)
    f = R.planche_zones(_ctx(), imgs, {"skill_1": [0.8, 0.8, 0.9, 0.9]}, cfg, racine=tmp_path)
    assert f.exists() and Image.open(f).size == (46 * 3, 14 + 50)
    s = json.loads((f.parent / "wJ9CwjKwyco_series.json").read_text(encoding="utf-8"))
    assert s["lignes"] == ["skill_1"] and len(s["luminance"]["skill_1"]) == 3
    assert R.planche_zones(_ctx(), imgs, {"skill_1": [0.8, 0.8, 0.9, 0.9]}, dict(CFG, planche=False), racine=tmp_path) is None


def test_hud_present_separe_hud_et_cinematique():
    import numpy as np
    rng = np.random.default_rng(1)
    icone = rng.random((16, 16)) * 200
    vig = [(0.0, icone), (0.5, icone + 3), (1.0, rng.random((16, 16)) * 200), (1.5, icone + 1), (2.0, icone)]
    assert R.hud_present(vig) == {0.0: True, 0.5: True, 1.0: False, 1.5: True, 2.0: True}


def test_etats_par_chiffres_ignore_hors_hud_et_pont_un_chiffre_manque():
    lect = [(0.0, None), (0.5, 15), (1.0, 15), (1.5, None), (2.0, 14), (2.5, "hors"), (3.0, "hors"), (3.5, None), (4.0, None), (4.5, None)]
    etats = R.etats_par_chiffres(lect)
    assert [e for _, e in etats] == ["pret", "recharge", "recharge", "recharge", "recharge", "pret", "pret", "pret"]
    assert [t for t, _ in etats][:5] == [0.0, 0.5, 1.0, 1.5, 2.0]


def test_transitions_chiffres_lance_avec_valeur_et_ignore_recharge_initiale():
    deja = [(0.0, 9), (0.5, 8), (1.0, None), (1.5, None), (2.0, 15), (2.5, 15), (3.0, 14), (3.5, 14)]
    assert R.transitions_chiffres(deja) == [(2.0, 15)]                     # le chiffre 9 de la 1re image : lancement inconnu, aucun événement
    assert R.transitions_chiffres([(0.0, 5), (0.5, 4), (1.0, 3)]) == []
    assert R.transitions_chiffres([]) == []


def test_releves_run_par_chiffres_pas_de_bruit_de_luminance():
    zones = {"skill_1": [0.0, 0.0, 0.1, 0.1], "ancre": [0.9, 0.9, 1.0, 1.0]}
    cfg = dict(CFG, detection="ocr", ocr_pas_s=0.5)
    frames = []
    for k in range(40):                                                        # 4 s à 10 images/s ; la luminance du bouton saute sans raison
        im = Image.new("RGB", (160, 90), (30, 30, 30))
        im.paste((255, 255, 255), (150, 82, 160, 90))
        im.paste(((k * 37) % 255,) * 3, (0, 0, 16, 9))
        frames.append((k / 10, im))
    lectures = iter([""] * 2 + ["15", "15", "14", "14", "13", "13"])
    ev, lim = R.releves_run(frames, zones, cfg, ocr=lambda im: next(lectures, "12"))
    lancers = [(e["slot"], e["t"], e["cooldown_read"]) for e in ev if e["slot"] == "skill_1"]
    assert lancers == [("skill_1", 1.0, 15.0)]


def test_purger_constantes_et_mediane_des_premieres_lectures():
    icone = [(k / 2, 4) for k in range(12)]                                    # icône lue « 4 » pendant 6 s : pas un compte à rebours
    assert all(v is None for _, v in R.purger_constantes(icone))
    assert R.purger_constantes([(0.0, 15), (0.5, 15), (1.0, 14)]) == [(0.0, 15), (0.5, 15), (1.0, 14)]
    lect = [(0.0, None), (0.5, None), (1.0, 4), (1.5, 14), (2.0, 14), (2.5, 13), (3.0, 13)]       # 1re lecture « 4 » pour 14
    assert R.transitions_chiffres(lect) == [(1.0, 14)]
    assert R.transitions_chiffres(icone + [(7.0, None), (7.5, None), (8.0, 9), (8.5, 9), (9.0, 8)]) == [(8.0, 9)]


def test_chiffres_manques_ne_font_pas_un_nouveau_lancement():
    lect = [(0.0, None), (0.5, None), (1.0, 14), (1.5, 14), (2.0, 13), (2.5, None), (3.0, None), (3.5, None), (4.0, None),
            (4.5, 10), (5.0, 10), (5.5, 9), (6.0, 9)]                           # 13 -> 10 : le compteur continue, aucun nouveau lancement
    assert R.transitions_chiffres(lect) == [(1.0, 14)]
    relance = lect[:5] + [(2.5 + k / 2, None) for k in range(1, 20)] + [(14.0, 14), (14.5, 14), (15.0, 13)]       # 10 s plus tard : nouveau lancement
    assert R.transitions_chiffres(relance) == [(1.0, 14), (14.0, 14)]
    hors = lect[:5] + [(2.5 + k / 2, "hors") for k in range(1, 40)] + [(22.5, 13), (23.0, 13), (23.5, 12)]       # cinématique : le chrono ne court pas
    assert R.transitions_chiffres(hors) == [(1.0, 14)]
