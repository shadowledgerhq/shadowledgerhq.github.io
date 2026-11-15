"""Cherche les fichiers data/**/*.json illisibles, dans l'arbre de travail ET dans le dernier commit local (HEAD).
Usage : py -3 pipeline\verifier_json.py   (lecture seule, ne modifie rien). Code de sortie 1 si un fichier est abîmé."""
import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def git(*a):
    r = subprocess.run(["git", *a], cwd=RACINE, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.stdout if r.returncode == 0 else ""


def erreur(texte):
    try:
        json.loads(texte)
        return None
    except json.JSONDecodeError as e:
        marq = any(l.startswith(("<<<<<<<", ">>>>>>>")) for l in texte.splitlines())
        return f"ligne {e.lineno}, {e.msg}" + (" — marqueurs de conflit git" if marq else "")


def main():
    mauvais = 0
    for f in sorted((RACINE / "data").rglob("*.json")):
        e = erreur(f.read_text(encoding="utf-8", errors="replace"))
        if e:
            mauvais += 1
            print(f"ARBRE DE TRAVAIL  {f.relative_to(RACINE).as_posix()} : {e}")
    for chemin in git("ls-tree", "-r", "--name-only", "HEAD", "data").splitlines():
        if chemin.endswith(".json"):
            e = erreur(git("show", f"HEAD:{chemin}"))
            if e:
                mauvais += 1
                print(f"DERNIER COMMIT    {chemin} : {e}")
    print("Tous les JSON de data/ sont lisibles." if not mauvais else f"{mauvais} fichier(s) abîmé(s).")
    return 1 if mauvais else 0


if __name__ == "__main__":
    sys.exit(main())
