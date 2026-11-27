#!/usr/bin/env python3
"""SPEC_ETAPE1 v43 §9 point 10 : correction du POC d'une semaine GELÉE avec les règles de texte v43.

    python3 pipeline/corriger_poc_v43.py [AAAA-MM-JJ]        # défaut : 2026-11-19

Rejoue le texte (TITRES seulement : les descriptions ne sont pas rejouables hors ligne) des lectures POC `poc_texte` de la semaine,
recalcule `poc.json` et ne garde le résultat que si les lignes classées (`rank` non null) sont inchangées ; aucun autre fichier de la
semaine n'est modifié. Une vidéo dont le titre porte la marque d'un autre mode (ex. 1CvG1JEPGwo, Unstable Dungeon) -> `rejected`,
raison `hors_sujet`. Ligne « Correction POC v43 après gel » dans `_rapport.md`."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classement
import poc_palier
import tri1
from donnees import Donnees, ajouter_rejet, charger_config
from semaine import PARIS, iso_utc, maintenant

NOTES_TEXTE = (poc_palier.NOTE_PALIER_TITRE, poc_palier.NOTE_PALIER_CLEAR, poc_palier.NOTE_PALIER_POURCENT, poc_palier.NOTE_DEGATS_INFO)


def _vide(meta, mode):
    return {"video_id": meta.get("video_id"), "mode": mode, "notes": [], "detail": {}}


def corriger(week, d=None, config=None, instant=None):
    d, config, instant = d or Donnees(), config or charger_config(), instant or maintenant()
    jour = instant.astimezone(PARIS).date().isoformat()
    meta = d.meta(week)
    if not meta or not meta.get("frozen"):
        return f"{week} n'est pas une semaine gelée : rien à corriger (un recalcul normal suffit)"
    avant = {p.relative_to(d.data).as_posix(): p.read_bytes() for p in d.data.rglob("*") if p.is_file() and "icons" not in p.parts}
    lectures, videos, rejected, processed = d.lectures(week), d.videos(week), d.rejected(week), d.processed()
    poc_avant = d.lire(f"runs/{week}/poc.json", [])
    classes = [l for l in poc_avant if l.get("rank") is not None]
    modifiees, retirees, rejetees = [], [], []
    for lec in list(lectures):
        det = lec.get("detail") or {}
        if lec["mode"] != "poc" or not det.get("poc_texte") or lec.get("score_source") != "titre":
            continue
        vid = lec["video_id"]
        titre = (videos.get(vid) or {}).get("title", "")
        nouvelle = poc_palier.lecture_texte({**videos.get(vid, {}), "video_id": vid}, [("titre", titre)], config, _vide)
        if nouvelle is not None and nouvelle["score"] == lec["score"] and nouvelle["detail"] == det:
            continue
        if nouvelle is None or nouvelle["score"] == 0:
            lectures.remove(lec)
            retirees.append(vid)
            if nouvelle is None and poc_palier._MARQUE_AUTRE.search(titre) and not poc_palier._MARQUE_POC.search(titre):
                m = videos.get(vid, {})
                p = processed.get(vid, {})
                if ajouter_rejet(rejected, {"video_id": vid, "channel_id": lec.get("channel_id"), "title": titre,
                                            "published_at": m.get("published_at") or lec.get("published_at"), "mode_guess": "poc",
                                            "reason": "hors_sujet", "detail": "autre mode (SPEC v43)", "last_tri": 1, "date": jour}):
                    rejetees.append(vid)
                    if p:
                        p.update(status="rejete", updated_at=jour, pc_needed=False)
            continue
        lec["notes"] = [n for n in lec.get("notes", []) if n not in NOTES_TEXTE] + [n for n in nouvelle["notes"] if n not in lec.get("notes", [])]
        lec["score"], lec["detail"] = nouvelle["score"], nouvelle["detail"]
        modifiees.append(vid)
    # vidéo POC sans aucune lecture POC dont le titre en donne une avec les règles v43 (ex. « ROUND 17 (100%) … POC » : 9BrduWR4aSY)
    ajoutees = []
    for vid, m in videos.items():
        if "poc" in (m.get("mode_guess") or []) and vid not in {r["video_id"] for r in rejected} \
                and not any(l["video_id"] == vid and l["mode"] == "poc" for l in lectures):
            neuves, _ = tri1.lectures_texte(m, [("titre", m.get("title", ""))], config)
            for n in neuves:
                if n["mode"] == "poc" and (n.get("detail") or {}).get("poc_texte") and n["score"]:
                    lectures.append(n)
                    ajoutees.append(vid)
    if not (modifiees or retirees or ajoutees):
        return f"{week} : aucune lecture de texte POC à corriger"
    d.ecrire(f"runs/{week}/_lectures.json", lectures)
    d.ecrire(f"rejected/{week}.json", rejected)
    d.ecrire("processed.json", processed)
    meta_f = d.data / f"runs/{week}/_meta.json"
    texte_meta = meta_f.read_text(encoding="utf-8")
    d.ecrire(f"runs/{week}/_meta.json", {**meta, "frozen": False})      # le temps du recalcul seulement
    try:
        classement.calculer(week, d, config, instant)
    finally:
        meta_f.write_text(texte_meta, encoding="utf-8")
    poc_apres = d.lire(f"runs/{week}/poc.json", [])
    if [l for l in poc_apres if l.get("rank") is not None] != classes:
        raise SystemExit("ABANDON : une ligne classée aurait changé ; rien n'est restauré automatiquement, voir git diff")
    # seuls ces fichiers peuvent changer ; tout autre fichier de data/ (recalcul de classement.calculer : règles déduites, boss, chaînes…) est remis tel quel
    autorises = {f"runs/{week}/poc.json", f"runs/{week}/_lectures.json", f"rejected/{week}.json", "processed.json", f"runs/{week}/_rapport.md"}
    for rel, octets in avant.items():
        p = d.data / rel
        if rel not in autorises and (not p.exists() or p.read_bytes() != octets):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(octets)
    ligne = (f"- Correction POC v43 après gel ({iso_utc(instant)[:10]}) : {len(modifiees)} lecture(s) de titre corrigée(s) ({', '.join(modifiees) or '—'}), "
             f"{len(ajoutees)} ajoutée(s) ({', '.join(ajoutees) or '—'}), {len(retirees)} retirée(s) ({', '.join(retirees) or '—'}), {len(rejetees)} vidéo(s) rejetée(s) hors_sujet ({', '.join(rejetees) or '—'}) ; "
             "lignes classées inchangées ; descriptions non rejouées hors ligne.")
    f = d.data / f"runs/{week}/_rapport.md"
    f.write_text((f.read_text(encoding="utf-8").rstrip("\n") + "\n\n" if f.exists() else "") + ligne + "\n", encoding="utf-8")
    return ligne[2:]


if __name__ == "__main__":
    print(corriger(sys.argv[1] if len(sys.argv) > 1 else "2026-11-19"))
