"""SPEC_ETAPE1 v34 §3 : relecture automatique des vidéos BOT / GB du top 10 provisoire par le PC.

Une vidéo des 10 premières lignes de `bot.json` / `gb.json` (lignes non `sûres`), déjà `termine`, sans écran Results lu (`pc.results_lus`
vide) et lue avec une version des règles du tri 1 plus ancienne que `config.tri1_version`, est remise `en_cours` (`pc_needed`, tris 3 et 4 à
refaire) : le PC la relit avec les règles actuelles. UN SEUL passage par vidéo et par version : `processed[vid].relecture_auto` = version
(pas de boucle si la relecture ne trouve rien). `processed[vid].relecture` = date (jeton : la fusion GitHub / PC garde l'état de la
relecture, `fusion_pc.fusionner_processed`)."""
import json
from pathlib import Path

TOP = 10
MODES = ("bot", "gb")


def candidates(d, week, config, processed):
    """[(video_id, mode)] à relire (sans rien modifier). Ordre : mode, rang dans le fichier."""
    version = config.get("tri1_version") or 0
    sortie, vus = [], set()
    for mode in MODES:
        f = Path(d.data) / "runs" / week / f"{mode}.json"
        try:
            lignes = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for ligne in (lignes if isinstance(lignes, list) else [])[:TOP]:
            if not isinstance(ligne, dict) or ligne.get("confidence") == "sur":
                continue
            for vid in ligne.get("video_ids") or [ligne.get("video_id")]:
                p = processed.get(vid)
                if (vid in vus or not p or p.get("week") != week or p.get("status") != "termine"
                        or (p.get("pc") or {}).get("results_lus") or (p.get("regles") or 0) >= version
                        or p.get("relecture_auto") == version):
                    continue
                vus.add(vid)
                sortie.append((vid, mode))
    return sortie


def poser(d, week, config, processed, jour):
    """Pose la relecture des `candidates` dans `processed` (modifié en place). Retourne [(video_id, mode)]."""
    version = config.get("tri1_version") or 0
    posees = candidates(d, week, config, processed)
    for vid, _ in posees:
        p = processed[vid]
        p.update(status="en_cours", pc_needed=True, relecture=jour, relecture_auto=version, updated_at=jour)
        pc = p.setdefault("pc", {})
        pc.update(tri3="a_faire", tri4="a_faire", results_lus=[])
    return posees


def lignes_rapport(posees):
    """Lignes du bloc `_rapport_pc.md` : « Relectures posées (règles) : … » ou rien."""
    if not posees:
        return []
    return ["- Relectures posées (règles plus anciennes, top 10 provisoire sans Results lu) : "
            + ", ".join(f"{vid} ({mode})" for vid, mode in posees)]
