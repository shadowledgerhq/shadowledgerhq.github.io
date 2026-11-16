"""Poussée des données du passage GitHub (daily.yml / weekly.yml) vers main, avec résolution automatique des conflits avec le PC.

Sens inverse de `pc.Git._resoudre_conflit` : ici la version du passage GitHub (commit local) l'emporte, sauf pour les fichiers
écrits par le PC (`fusion_pc.PROPRES_PC` : `_rapport_pc.md`, builds, cartes apprises) qui restent ceux de `main`, et pour
`processed.json`, `_lectures.json` et `rejected/` qui sont fusionnés vidéo par vidéo (`fusion_pc.fusionner`).
Usage : python3 pipeline/pousser_github.py   (après `git commit`). Code de sortie 1 si la poussée échoue (rien n'est perdu)."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fusion_pc

RACINE = Path(__file__).resolve().parents[1]


def git(racine, *args, ok=False):
    r = subprocess.run(["git", *args], cwd=racine, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0 and not ok:
        raise RuntimeError(f"git {args[0]} : {(r.stderr or r.stdout)[-300:].strip()}")
    return r.stdout


def _json(racine, ref, chemin):
    try:
        return json.loads(git(racine, "show", f"{ref}:{chemin}"))
    except (RuntimeError, ValueError):
        return None


def resoudre(racine):
    """Fusion de origin/main dans la branche courante (commit GitHub = `locale`). Retourne la liste des fichiers fusionnés."""
    locale = git(racine, "rev-parse", "HEAD").strip()
    base = git(racine, "merge-base", locale, "origin/main").strip()
    changes_pc = [c for c in git(racine, "diff", "--name-only", base, "origin/main").splitlines() if c.strip()]
    try:
        git(racine, "merge", "-X", "ours", "--no-edit", "-m", "données: conflit git résolu automatiquement (GitHub)", "origin/main")
    except RuntimeError:
        git(racine, "merge", "--abort", ok=True)
        raise
    traites = []
    for chemin in changes_pc:
        if fusion_pc.est_propre_pc(chemin):
            git(racine, "checkout", "origin/main", "--", chemin)
            traites.append(chemin)
        elif fusion_pc.fusion_json(chemin):
            pc_version = _json(racine, "origin/main", chemin)
            github = _json(racine, locale, chemin)
            if pc_version is None:
                continue
            fusion = fusion_pc.fusionner(chemin, github, pc_version)
            if fusion is not None:
                (Path(racine) / chemin).write_text(json.dumps(fusion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                traites.append(chemin)
    for f in sorted((Path(racine) / "data").rglob("*.json")):
        json.loads(f.read_text(encoding="utf-8"))            # JSON abîmé : on n'enregistre rien
    git(racine, "add", "data")
    if git(racine, "status", "--porcelain").strip():
        git(racine, "commit", "-m", "données: conflit git résolu automatiquement (GitHub)")
    return traites


def pousser(racine=RACINE, tentatives=3):
    derniere = None
    for i in range(tentatives):
        try:
            git(racine, "fetch", "origin", "main")
            try:
                git(racine, "pull", "--rebase", "origin", "main")
            except RuntimeError:
                git(racine, "rebase", "--abort", ok=True)
                traites = resoudre(racine)
                print("Conflit git résolu automatiquement :", ", ".join(traites) or "(aucun fichier à fusionner)")
            git(racine, "push", "origin", "HEAD:main")
            return True
        except RuntimeError as e:
            derniere = e
            print(f"Tentative {i + 1}/{tentatives} échouée : {e}", file=sys.stderr)
            time.sleep(2 * (i + 1))
    print(f"ÉCHEC de la poussée : {derniere}", file=sys.stderr)
    return False


if __name__ == "__main__":
    sys.exit(0 if pousser() else 1)
