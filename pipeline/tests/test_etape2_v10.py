"""SPEC_ETAPE2 v10 : zones POC des images auto (test 23), équipe de la composition (tests 23-24), image de fondu écartée."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageFilter

import builds
import composition as C

RACINE = Path(__file__).resolve().parents[2]
CFG = builds.charger_config()
AUTO = RACINE / "docs" / "essais" / "composition" / "auto" / "poc"


def _rects(z):
    if isinstance(z, dict):
        for v in z.values():
            yield from _rects(v)
    elif z and isinstance(z[0], (int, float)):
        yield z
    else:
        for v in z:
            yield from _rects(v)


def test_spec_version_10_et_zone_equipe_sur_les_5_onglets():
    assert CFG["spec_version"] == 10
    for o in C.ONGLETS:
        assert CFG["zones"]["poc"][o]["equipe"]["label"] == [0.35, 0.90, 0.44, 0.96], o


def test_zones_poc_recadrent_un_objet_sur_les_images_auto():
    """Test 23 (géométrie) : aucune zone de `zones.poc` ne tombe sur une case vide (écart-type des niveaux de gris)."""
    vues = 0
    for f in sorted(AUTO.glob("*.png")):
        onglet = f.stem.rsplit("_", 2)[1]
        im = Image.open(f).convert("L")
        w, h = im.size
        assert (w, h) == (1920, 1080), f.name
        for nom, z in CFG["zones"]["poc"][onglet].items():
            if nom == "equipe":
                continue
            for x0, y0, x1, y1 in _rects(z):
                a = np.asarray(im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))).astype(float)
                assert a.std() > 8, (f.name, nom, (x0, y0, x1, y1), a.std())
                vues += 1
    assert vues > 40


def test_numero_equipe():
    for texte, n in (("Team 1", 1), ("Team 2\n", 2), ("1팀", 1), ("パーティ2", 2), ("2팀", 2), ("TEAM 2", 2), (" 1 ", 1)):
        assert C.numero_equipe(texte) == n, texte
    for texte in ("", "Team", "Team 3", "12", "1 2", None):
        assert C.numero_equipe(texte) is None, texte


def test_equipe_label_lu_sur_les_images_auto():
    """Test 23 (OCR, seulement si tesseract est installé) : 1 sur zFsAGI_xyOQ (1팀), 1 et 2 sur 2AJljDc_nN4."""
    if not shutil.which("tesseract"):
        return

    class Outils:
        def recadrer(self, png, zone, echelle=3, seuil=None):
            im = Image.open(png).convert("L")
            w, h = im.size
            c = im.crop((int(zone[0] * w), int(zone[1] * h), int(zone[2] * w), int(zone[3] * h)))
            c = c.resize((c.width * echelle, c.height * echelle))
            if seuil:
                c = c.point(lambda v: 0 if v > seuil else 255)
            sortie = Path(png).with_name("z.png")
            c.save(sortie)
            return sortie

        def ocr(self, png, langues=None, psm=6, timeout=20):
            import subprocess
            return subprocess.run(["tesseract", str(png), "stdout", "-l", langues or "eng", "--psm", str(psm)],
                                  capture_output=True, text=True).stdout
    o = Outils()
    lu = lambda nom: C.lire_equipe(o, Image.open(AUTO / nom), CFG, nom.rsplit("_", 2)[1])
    assert lu("zFsAGI_xyOQ_personnages_240.png") == 1
    assert lu("2AJljDc_nN4_artefacts_232.png") == 1
    assert lu("2AJljDc_nN4_competences_232.png") == 1
    assert lu("2AJljDc_nN4_noyaux_232.png") == 2


class OutilsFaux:
    """OCR simulé : lit le libellé écrit dans la couleur du coin de l'image (rouge = équipe 1, vert = équipe 2, bleu = illisible)."""
    def recadrer(self, png, zone, echelle=3, seuil=None):
        return png

    def ocr(self, png, langues=None, psm=6, timeout=20):
        r, g, b = Image.open(png).convert("RGB").getpixel((0, 0))
        return {"r": "Team 1", "g": "Team 2", "b": "?"}["rgb"[(r, g, b).index(255)]]


def _img(c):
    return Image.new("RGB", (64, 36), {"r": (255, 0, 0), "g": (0, 255, 0), "b": (0, 0, 255)}[c])


def test_lire_equipe_par_ocr_simule():
    o = OutilsFaux()
    assert [C.lire_equipe(o, _img(c), CFG, "artefacts") for c in "rgb"] == [1, 2, None]


def test_une_image_n_est_lue_que_pour_son_equipe():
    """Test 24 : run `team: 1`, images d'onglets en équipe 1 et 2 -> seules les images équipe 1 ; pas de note."""
    ims = {"artefacts": [_img("r"), _img("g")], "noyaux": [_img("g"), _img("r")]}
    eq = {"artefacts": [1, 2], "noyaux": [2, 1]}
    sortie, notes = C.filtrer_par_equipe(ims, eq, 1)
    assert [i.getpixel((0, 0)) for i in sortie["artefacts"]] == [(255, 0, 0)] and [i.getpixel((0, 0)) for i in sortie["noyaux"]] == [(255, 0, 0)]
    assert notes == []
    sortie, _ = C.filtrer_par_equipe(ims, eq, 2)
    assert [i.getpixel((0, 0)) for i in sortie["artefacts"]] == [(0, 255, 0)]


def test_equipe_illisible_et_run_sans_equipe():
    ims = {"artefacts": [_img("b"), _img("r")], "noyaux": [_img("b")]}
    sortie, notes = C.filtrer_par_equipe(ims, {"artefacts": [None, 1], "noyaux": [None]}, 1)
    assert len(sortie["artefacts"]) == 1 and sortie["noyaux"] == [] and notes == ["équipe de la composition non lue"]
    sortie, notes = C.filtrer_par_equipe(ims, {"artefacts": [None, None], "noyaux": [None]}, 1)       # rien de lisible : tout est gardé
    assert len(sortie["artefacts"]) == 2 and notes == ["équipe de la composition non lue"]
    sortie, notes = C.filtrer_par_equipe(ims, {"artefacts": [1, 2], "noyaux": [2]}, None)
    assert len(sortie["artefacts"]) == 2 and notes == ["équipe de la run inconnue"]


def test_image_de_fondu_ecartee():
    """Image nette de l'onglet et même image en fondu (floue, contraste réduit) : le fondu est écarté."""
    nette = Image.open(AUTO / "2AJljDc_nN4_artefacts_232.png").convert("RGB")
    flou = nette.filter(ImageFilter.GaussianBlur(6))
    assert C.nettete(flou) < 0.5 * C.nettete(nette)
    sortie = C.ecarter_fondus({"artefacts": [flou, nette], "noyaux": [flou]}, CFG)
    assert sortie["artefacts"] == [nette] and sortie["noyaux"] == [flou]


def test_notes_du_fournisseur_dans_le_build():
    """`calculer` reprend `extra['notes']` dans les notes du build."""
    src = (RACINE / "pipeline" / "builds.py").read_text(encoding="utf-8")
    assert 'extra.get("notes")' in src


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
    print("OK")
