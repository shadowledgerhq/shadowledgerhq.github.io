"""Répare les lectures GB fusionnées AVANT v23 dont les images ont été comptées deux fois (vidéo relue avec --refaire : la lecture
déjà fusionnée + les mêmes images relues = 2 × plus d'images ; RaidenShadow « 14 images » pour 7). Usage :
    python3 pipeline/reparer_images_doublees.py <semaine AAAA-MM-JJ> <video_id> [<video_id> …]
Ne touche qu'aux vidéos nommées, sans `detail.par_t`, dont TOUS les compteurs (images, votes) sont pairs : ils sont alors divisés
par 2 ; sinon la lecture est laissée telle quelle. Écrit le fichier `data/runs/<semaine>/_lectures.json` ; relancer ensuite
`python3 pipeline/classement.py <semaine>`. Les lectures refaites avec le code v23 n'en ont pas besoin."""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def reparer(lectures, videos):
    """Retourne la liste des (video_id, avant, apres) réparés ; modifie `lectures` sur place."""
    faits = []
    for l in lectures:
        d = l.get("detail") or {}
        if l.get("video_id") not in videos or d.get("par_t") or not d.get("votes"):
            continue
        n = d.get("n_images")
        compteurs = [x[1] for liste in d["votes"].values() for x in liste]
        if not n or n % 2 or any(c % 2 for c in compteurs):
            continue
        d["votes"] = {c: [[v, k // 2] for v, k in liste] for c, liste in d["votes"].items()}
        d["n_images"] = n // 2
        for cle in ("rc_images", "final_images"):
            if d.get(cle):
                d[cle] //= 2
        for champ, seq in (d.get("sequence") or {}).items():
            vus, uniq = set(), []
            for x in seq:
                if tuple(x) not in vus:
                    vus.add(tuple(x))
                    uniq.append(x)
            d["sequence"][champ] = uniq
        l["notes"] = [re.sub(r"lecture fusionnée \(\d+ images\)", f"lecture fusionnée ({d['n_images']} images)", x) for x in l.get("notes") or []]
        faits.append((l["video_id"], n, d["n_images"]))
    return faits


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    chemin = RACINE / "data" / "runs" / argv[0] / "_lectures.json"
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    lectures = brut if isinstance(brut, list) else brut["lectures"]
    faits = reparer(lectures, set(argv[1:]))
    for v, a, b in faits:
        print(f"{v} : {a} images -> {b}")
    if faits:
        tmp = chemin.with_suffix(".tmp")
        tmp.write_text(json.dumps(brut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(chemin)
    else:
        print("rien à réparer")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
