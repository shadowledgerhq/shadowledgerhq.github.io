"""27/11 : des sous-titres refusés (429) n'empêchent plus le passage des images ; un 429 au téléchargement arrête les images."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pc
from donnees import charger_config
from test_pc import INSTANT, SEM, monde
from test_tri34 import GB_RECORD, OutilsImages


class Outils429(OutilsImages):
    def __init__(self, textes, telechargement_429=False):
        super().__init__(textes)
        self.dl429 = telechargement_429

    def sous_titres(self, vid, dossier):
        self.appels.append(("st", vid))
        raise RuntimeError("HTTP Error 429: Too Many Requests")

    def telecharger(self, vid, dossier):
        if self.dl429:
            self.appels.append(("dl429", vid))
            raise RuntimeError("HTTP Error 429: Too Many Requests")
        return super().telecharger(vid, dossier)


def _monde(tmp):
    d = monde(tmp)
    videos = d.videos(SEM)
    for v in videos:
        videos[v]["mode_guess"] = ["gb"]
    d.ecrire(f"runs/{SEM}/_videos.json", videos)
    return d


def test_sous_titres_429_puis_images_traitees():
    config = charger_config()
    config["pc"]["regle_sous_titres"] = False
    with tempfile.TemporaryDirectory() as tmp:
        d = _monde(tmp)
        o = Outils429({"a": {0: GB_RECORD, 2: GB_RECORD, 4: GB_RECORD}})
        r = pc.lancer("daily", INSTANT, d, config, o, journal=lambda x: None, dormir=lambda x: None)
        assert [a for a in o.appels if a[0] == "st"] == [("st", o.appels[[a[0] for a in o.appels].index("st")][1])]     # un seul essai de sous-titres
        assert any(a[0] == "dl" for a in o.appels)                                                                   # les images sont tentées quand même
        assert any("429" in a and "images continuent" in a for a in r["alertes"])
        assert any("anti-bot" in a for a in r["alertes"])                                                            # le passage reste signalé incomplet


def test_telechargement_429_arrete_les_images():
    config = charger_config()
    config["pc"]["regle_sous_titres"] = False
    with tempfile.TemporaryDirectory() as tmp:
        d = _monde(tmp)
        o = Outils429({}, telechargement_429=True)
        r = pc.lancer("daily", INSTANT, d, config, o, journal=lambda x: None, dormir=lambda x: None)
        assert len([a for a in o.appels if a[0] == "dl429"]) == 1                                                    # arrêt au premier 429 de téléchargement
        assert any("images arrêtées" in a for a in r["alertes"])


if __name__ == "__main__":
    test_sous_titres_429_puis_images_traitees()
    test_telechargement_429_arrete_les_images()
    print("OK")
