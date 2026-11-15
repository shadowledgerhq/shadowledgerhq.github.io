"""Reprise d'un commit local de passage PC non poussé (ex. incident du 15/11) SANS perte de résultats.
Usage (après `git branch sauvegarde 78e1780` et `git reset --hard origin/main`) :
    py -3 pipeline\\fusion_locale.py sauvegarde
Lit `data/processed.json` et `data/runs/*/_lectures.json` de la branche donnée, les fusionne dans l'arbre de travail
(l'état d'origin/main est la base ; les entrées locales plus avancées ou absentes y sont ajoutées). Ne touche ni aux
rapports (`_rapport.md`, régénérés au prochain passage) ni à git : le commit se fait ensuite à la main."""
import json
import subprocess
import sys
from pathlib import Path

from donnees import RACINE, Donnees, lire_json

FAIT = ("fait", "absent", "inutile")


def avance(p):
    """Degré d'avancement d'une entrée de processed.json (plus grand = plus avancé)."""
    pc = p.get("pc") or {}
    return (10 if p.get("status") in ("termine", "rejete") else 0) + sum(1 for k in ("sous_titres", "tri3", "tri4") if pc.get(k) in FAIT)


def fusionner_processed(base, local):
    """Retourne (fusion, nb ajoutées, nb remplacées par la version locale plus avancée)."""
    out, ajout, rempl = dict(base), 0, 0
    for vid, p in local.items():
        if vid not in out:
            out[vid] = p
            ajout += 1
        elif avance(p) > avance(out[vid]):
            out[vid] = p
            rempl += 1
    return out, ajout, rempl


def cle_lecture(l):
    return (l["video_id"], l["mode"], l.get("score_source"), l.get("score"), l.get("t"))


def fusionner_lectures_locales(base, local):
    vus = {cle_lecture(l) for l in base}
    ajout = [l for l in local if cle_lecture(l) not in vus]
    return base + ajout, len(ajout)


def git(racine, *a):
    r = subprocess.run(["git", *a], cwd=racine, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.stdout if r.returncode == 0 else None


def main(branche, racine=RACINE):
    d = Donnees(racine)
    texte = git(racine, "show", f"{branche}:data/processed.json")
    if texte is None:
        print(f"Branche ou fichier introuvable : {branche}", file=sys.stderr)
        return 1
    fus, a, r = fusionner_processed(d.processed(), json.loads(texte))
    d.ecrire("processed.json", fus)
    print(f"processed.json : {a} vidéo(s) ajoutée(s), {r} remplacée(s) par la version locale plus avancée")
    for chemin in (git(racine, "ls-tree", "-r", "--name-only", branche, "data/runs") or "").splitlines():
        if not chemin.endswith("/_lectures.json"):
            continue
        rel = chemin[len("data/"):]
        loc = json.loads(git(racine, "show", f"{branche}:{chemin}"))
        res, n = fusionner_lectures_locales(d.lire(rel, []), loc)
        d.ecrire(rel, res)
        print(f"{chemin} : {n} lecture(s) ajoutée(s) ({len(res)} au total)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "sauvegarde"))
