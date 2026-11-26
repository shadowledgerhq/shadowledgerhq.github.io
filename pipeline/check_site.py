"""Contrôle « rien de public avant le lancement » (CONTEXTE §2, décision d'Alexis du 26/11/2026).

Hors lancement : toute page HTML de site/ porte <meta name="robots" content="noindex"> et site/robots.txt contient « Disallow: / ».
Usage : python3 pipeline/check_site.py [--lancement]   (--lancement : contrôle sauté, à n'utiliser qu'avec le feu vert d'Alexis)
Code de sortie 1 s'il manque quelque chose."""
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
NOINDEX = re.compile(r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', re.I)


def verifier(racine=RACINE):
    erreurs = []
    site = Path(racine) / "site"
    robots = site / "robots.txt"
    if not robots.exists() or not re.search(r"^Disallow:\s*/\s*$", robots.read_text(encoding="utf-8"), re.M):
        erreurs.append("site/robots.txt absent ou sans « Disallow: / »")
    for page in sorted(site.rglob("*.html")):
        if not NOINDEX.search(page.read_text(encoding="utf-8", errors="replace")):
            erreurs.append(f"{page.relative_to(racine)} : <meta name=\"robots\" content=\"noindex\"> absent")
    return erreurs


if __name__ == "__main__":
    if "--lancement" in sys.argv:
        print("Mode lancement : contrôle sauté.")
        sys.exit(0)
    e = verifier()
    print("\n".join(e) if e else "Site privé : noindex et robots.txt en place.")
    sys.exit(1 if e else 0)
