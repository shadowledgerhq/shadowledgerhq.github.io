"""Détection de l'écran de composition, choix des images, fournisseur PC et chaîne complète sur les captures BOT JA."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image

import builds as B
import composition as C
import icones

RACINE = B.RACINE
CFG = B.charger_config()
D = RACINE / "docs" / "essais" / "composition"
TABS = ("personnages", "artefacts", "competences", "benedictions", "noyaux")


def capture(t):
    return Image.open(D / f"bot_{t}_ja.png").convert("RGB")


def autre_ecran():
    jpg = sorted((RACINE / "docs" / "essais" / "ocr").glob("*gb_combat.jpg"))
    return Image.open(jpg[0]).convert("RGB") if jpg else Image.new("RGB", (1158, 651), (30, 30, 60))


def test_onglet_actif_et_ecran():
    for t in TABS:
        assert C.bouton_present(capture(t), CFG) and C.onglet_actif(capture(t), CFG) == t, t
    assert C.analyser_image(autre_ecran(), CFG) is None
    assert C.analyser_image(Image.new("RGB", (1158, 651), (255, 200, 40)), CFG) is None      # tout jaune : pas d'onglet actif
    assert C.analyser_image(capture("noyaux").resize((1920, 1080)), CFG) == "noyaux"          # indépendant de la résolution


def test_choisir_images():
    suite = [(0, autre_ecran()), (2, capture("noyaux")), (4, capture("noyaux")), (6, capture("noyaux")), (8, capture("noyaux")),
             (10, capture("artefacts")), (12, autre_ecran())]
    images, t = C.choisir_images(suite, CFG)
    assert set(images) == {"noyaux", "artefacts"} and len(images["noyaux"]) <= CFG["extraction"]["max_par_onglet"] and t == [2, 10]
    assert C.choisir_images([(0, autre_ecran())], CFG) == ({}, None)


class FauxOutils:
    """Vidéo simulée : une image toutes les 2 s (autre écran, puis les onglets des captures)."""
    def __init__(self, sequence):
        self.sequence, self.appels = sequence, []

    def telecharger(self, vid, dossier):
        self.appels.append(vid)
        return Path(dossier) / f"{vid}.mp4"

    def images(self, chemin, segments, dossier, prefixe="f", hauteur=None):
        sortie = []
        for k, (debut, duree, pas) in enumerate(segments):
            for i, nom in enumerate(self.sequence):
                if i * pas > duree:
                    break
                png = Path(dossier) / f"{prefixe}{k}_{i:04d}.png"
                (capture(nom) if nom != "autre" else autre_ecran()).save(png)
                sortie.append((debut + i * pas, png))
        return sortie


def test_chaine_complete_sur_captures():
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "data" / "runs" / "2026-11-19").mkdir(parents=True)
        (t / "data" / "db").mkdir(parents=True)
        for f in (RACINE / "data" / "db").glob("*.json"):
            (t / "data" / "db" / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        for dossier in ("rules", "icons"):
            (t / "data" / dossier).mkdir()
        for f in (RACINE / "data" / "icons").rglob("*.png"):
            dest = t / "data" / "icons" / f.parent.name / f.name
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(f.read_bytes())
        (t / "data" / "rules" / "2026-11-19.json").write_text(json.dumps({"week": "2026-11-19", "modes": {"bot_season": {
            "sjw": True, "sjw_skills": True, "blessings": True, "shadows": True, "successor": True}}}), encoding="utf-8")
        ligne = {"run_id": "bot-x-001", "week": "2026-11-19", "mode": "bot", "channel_id": "UC1", "player": "P", "video_id": "VIDEOBOT001",
                 "rank": 1, "score": {"total": 19.5, "runs": [19.5], "unit": "seconds"},
                 "runs_detail": [{"video_id": "VIDEOBOT001", "t": 40, "team": None}]}
        (t / "data" / "runs" / "2026-11-19" / "bot.json").write_text(json.dumps([ligne]), encoding="utf-8")
        outils = FauxOutils(["autre", "noyaux", "noyaux", "personnages", "autre"])
        res = B.calculer("2026-11-19", t, CFG, banque=icones.Banque(t), fournisseur=C.fournisseur_pc(outils, CFG))
        assert outils.appels == ["VIDEOBOT001"] and len(res) == 1
        b = res[0]
        assert b["t_composition"] == [2, 6] and b["status"] == "build_partiel", (b["status"], b["notes"])
        assert [c["id"] for c in b["sjw"]["cores"]][0] == "ancient-wraiths-obession"
        assert b["hunters"][0]["cores"][0]["id"] == "ferocious-protectors-desire" and b["counts"]["cores"] == "6/9"
        assert b["confidence"] == "a_verifier" and "reconnaissance faible" in b["notes"]      # portrait du chasseur 2 : bande de doute
        # vidéo sans écran de composition : pas_de_build, raison notée ; erreur de téléchargement : idem, sans planter
        vide = C.fournisseur_pc(FauxOutils(["autre", "autre"]), CFG)(ligne | {"t_result": 10})
        assert vide[0] == {} and vide[1]["t_composition"] is None
        class Casse(FauxOutils):
            def telecharger(self, vid, dossier):
                raise RuntimeError("HTTP Error 429")
        r = C.fournisseur_pc(Casse([]), CFG)({"video_id": "X", "t_result": 10})
        assert r[0] == {} and "429" in r[1]["erreur"]


def test_pas_de_telechargement_sans_zones_et_build_essai():
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "data" / "runs" / "2026-11-19").mkdir(parents=True)
        (t / "data" / "db").mkdir(parents=True)
        for f in (RACINE / "data" / "db").glob("*.json"):
            (t / "data" / "db" / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        ligne = {"run_id": "gb-x-001", "week": "2026-11-19", "mode": "gb", "channel_id": "UC1", "player": "P", "video_id": "VIDEOGB0001", "rank": 1,
                 "score": {"total": 100, "runs": [100], "unit": "rage_count"}, "runs_detail": [{"video_id": "VIDEOGB0001", "t": 40, "team": 1}]}
        (t / "data" / "runs" / "2026-11-19" / "gb.json").write_text(json.dumps([ligne]), encoding="utf-8")
        outils = FauxOutils(["noyaux"])
        res = B.calculer("2026-11-19", t, CFG, banque=icones.Banque(t), fournisseur=C.fournisseur_pc(outils, CFG))
        assert outils.appels == [] and res[0]["status"] == "pas_de_build" and "composition GB non décrite" in res[0]["notes"]
    b = B.build_essai("VID", "bot", fournisseur=C.fournisseur_pc(FauxOutils(["autre", "noyaux"]), CFG))
    assert b["rank"] is None and b["status"] == "build_partiel" and b["counts"]["cores"] == "6/9"


def test_debut_de_visite_ignore():
    """Les icônes n'apparaissent qu'après le changement d'onglet : la 1re image de chaque visite est écartée (sauf visite d'une image)."""
    l = [(0, "a"), (2, "b"), (4, "c"), (20, "d"), (22, "e"), (40, "f")]
    assert [x for _, x in C._sans_debut_de_visite(l, 1, 3)] == ["b", "c", "e", "f"]
    assert C._sans_debut_de_visite(l, 0, 3) == l


def test_choisir_stables_ecarte_le_fondu():
    """Changement d'onglet en fondu (0,5 s) : l'image mélangée n'est pas gardée, une image stable de l'onglet l'est."""
    a = capture("personnages")
    b = capture("artefacts").resize(a.size)
    fondu = [Image.blend(a, b, k) for k in (0.3, 0.6, 0.9)]
    suite = [a, a, a, *fondu, b, b, b]
    images_t = [(i * 0.5, im) for i, im in enumerate(suite)]
    inst = C.instabilites([im for _, im in images_t])
    assert inst[1] < 0.5 and inst[4] > inst[7]                     # l'image au milieu du fondu est la moins stable
    choix = C.choisir_stables(images_t, CFG)
    assert set(choix) <= {"personnages", "artefacts"}
    assert all(i >= 6 for i in choix.get("artefacts", [6]))        # jamais une image du fondu
    assert choix.get("artefacts") and choix.get("personnages")


def test_affiner_onglet_trouve_le_plateau():
    """Onglet vu seulement en fondu à 0,5 s : la passe à 0,1 s retrouve une image stable (pas une image mélangée)."""
    import tempfile
    a = capture("personnages")
    b = capture("artefacts").resize(a.size)
    suite = [a, Image.blend(a, b, 0.3), Image.blend(a, b, 0.6), Image.blend(a, b, 0.9), b, b, b, b]

    class O:
        def images(self, chemin, segments, dossier, prefixe="f", hauteur=None):
            sortie = []
            for k, im in enumerate(suite):
                f = Path(dossier) / f"{prefixe}_{k}.png"
                im.save(f)
                sortie.append((1 + k * 0.1, f))
            return sortie
    cfg = {**CFG, "extraction": {**CFG["extraction"], "pas_tres_fin_s": 0.1}}
    with tempfile.TemporaryDirectory() as tmp:
        ims = C._affiner_onglet(O(), cfg, "v.mp4", "artefacts", [1.2], tmp)
    assert ims and all(float(abs(C._gris(im) - C._gris(b)).mean()) < 1 for im in ims)


if __name__ == "__main__":
    for nom, f in sorted(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
