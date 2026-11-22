"""Diagnostic des zones du Results GB (v37) : pour une image, lit chaque zone sous chaque prétraitement de `gb.zones_ocr.variantes`
et sous plusieurs modes tesseract (psm 7 = ligne, 8 = mot, 13 = ligne brute ; avec/sans liste de chiffres), et affiche le texte lu.
Les recadrages sont gardés dans `logs/diag_zones/`. Usage (sur le PC) :
  py -3 pipeline\\diag_zones.py docs\\essais\\ocr\\XVzx3w07JPo_recherche_221_gb_results_partiel.jpg [zone ...]
Zones par défaut : rage final. Ne modifie aucune donnée."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_ecrans                          # noqa: E402
import pc                                   # noqa: E402
from donnees import charger_config          # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    image, zones = Path(argv[0]), argv[1:] or ["rage", "final"]
    config = charger_config()
    gb = config.get("gb") or {}
    outils = pc.Outils(config["pc"])
    sortie = RACINE / "logs" / "diag_zones"
    sortie.mkdir(parents=True, exist_ok=True)
    chiffres = ["-c", "tessedit_char_whitelist=0123456789,.:"]
    for nom in zones:
        zone = (gb.get("zones") or {}).get(nom)
        if not zone:
            print(f"zone inconnue : {nom}")
            continue
        print(f"\n== zone {nom} {zone}")
        for i, v in enumerate(((gb.get("zones_ocr") or {}).get("variantes_compteurs") if nom in ocr_ecrans.ZONES_COMPTEURS else None) or (gb.get("zones_ocr") or {}).get("variantes") or [{"echelle": 3, "seuil": None}]):
            petit = outils.recadrer(image, zone, v.get("echelle", 3), v.get("seuil"))
            copie = sortie / f"{image.stem}_{nom}_v{i}.png"
            shutil.copyfile(petit, copie)
            lus = []
            for psm in (7, 8, 13):
                for extra in (chiffres, None):
                    try:
                        t = outils.ocr(petit, "eng", psm, 40, extra).strip().replace("\n", " ")
                    except Exception as e:          # noqa: BLE001
                        t = f"erreur {e}"
                    lus.append(f"psm{psm}{'+chiffres' if extra else ''}={t!r}")
            Path(petit).unlink(missing_ok=True)
            print(f"  variante {i} {v} -> {copie.name}\n    " + "\n    ".join(lus))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
