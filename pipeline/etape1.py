"""Passages GitHub Actions de l'étape 1 (docs/SPEC_ETAPE1.md §6).

  python3 pipeline/etape1.py daily  [--force] [--maintenant ISO]   recherche + tri 1 + classement + rapport
  python3 pipeline/etape1.py weekly [--force] [--maintenant ISO]   dernière recherche de la semaine écoulée
  python3 pipeline/etape1.py classement [--semaine AAAA-MM-JJ]     recalcul seul + rapport

Hors créneau (heure de Paris) ou passage du jour déjà fait : sort sans rien faire (sauf --force).
Tri 2 (miniatures) : recadrages OCR [EN ATTENTE], les vidéos restent en_cours avec pc_needed.
Le commit est fait par le workflow, pas par ce script.
"""
import argparse
import os

import classement
from donnees import Donnees, ajouter_rejet, charger_config
from semaine import (PARIS, bornes, dans_creneau, id_semaine, iso_utc, maintenant, parse_iso,
                     semaine_precedente)
from tri1 import lectures_texte, remplacer_lectures
from youtube import ApiYouTube, recherche

JEUDI = 3


def ouvrir_semaine(d, week):
    meta = d.meta(week)
    if meta is None:
        debut, fin = bornes(week)
        meta = {"week": week, "start_utc": iso_utc(debut), "end_utc": iso_utc(fin),
                "frozen": False, "frozen_at": None, "passages": {}}
        d.ecrire(f"runs/{week}/_meta.json", meta)
    return meta


def passage_recherche(d, config, week, debut, fin, gelee, instant):
    resume = {"units": 0, "nouvelles": 0, "rejetees": 0, "provisoires": 0, "arret_quota": None,
              "erreurs": [], "non_geres": set()}
    cle = os.environ.get("YOUTUBE_API_KEY")
    if not cle:
        resume["erreurs"].append("YOUTUBE_API_KEY absente : recherche non faite")
        return resume
    processed = d.processed()
    api = ApiYouTube(cle, config["quota_max_units"])
    r = recherche(api, debut, fin, config, d.channels(), set(processed) | d.tous_rejetes())
    resume.update(units=api.units, arret_quota=r["arret_quota"], erreurs=r["erreurs"])

    jour = instant.astimezone(PARIS).date().isoformat()
    videos, lectures, rejected = d.videos(week), d.lectures(week), d.rejected(week)
    rejets = list(r["rejets"])
    if gelee:
        rejets += [{"meta": m, "reason": "semaine_gelee", "detail": ""} for m in r["videos"].values()]
    for x in rejets:
        m = x["meta"]
        ajouter_rejet(rejected, {"video_id": m["video_id"], "channel_id": m["channel_id"],
                                 "title": m["title"], "published_at": m["published_at"],
                                 "mode_guess": "/".join(m["mode_guess"]) or None,
                                 "reason": x["reason"], "detail": x["detail"], "last_tri": 0,
                                 "date": jour})
        processed[m["video_id"]] = {"week": week, "channel_id": m["channel_id"],
                                    "published_at": m["published_at"], "first_seen": jour,
                                    "updated_at": jour, "last_tri": 0, "status": "rejete",
                                    "modes": m["mode_guess"], "pc_needed": False}
        resume["rejetees"] += 1
    if not gelee:
        for vid, m in r["videos"].items():
            nouvelles, non_geres = lectures_texte(
                m, [("titre", m["title"]), ("description", m["description"])], config)
            lectures = remplacer_lectures(lectures, vid, nouvelles, ("titre", "description"))
            resume["non_geres"] |= set(non_geres)
            resume["provisoires"] += len(nouvelles)
            videos[vid] = {k: v for k, v in m.items() if k != "description"}
            processed[vid] = {"week": week, "channel_id": m["channel_id"],
                              "published_at": m["published_at"], "first_seen": jour,
                              "updated_at": jour, "last_tri": 1, "status": "en_cours",
                              "modes": m["mode_guess"], "pc_needed": True}
            resume["nouvelles"] += 1
    d.ecrire(f"runs/{week}/_videos.json", videos)
    d.ecrire(f"runs/{week}/_lectures.json", lectures)
    d.ecrire(f"rejected/{week}.json", rejected)
    d.ecrire("processed.json", processed)
    return resume


def ecrire_rapport(d, week, passage, instant, resume, res, alertes):
    proc = [p for p in d.processed().values() if p.get("week") == week]
    compte = {s: sum(1 for p in proc if p["status"] == s) for s in ("en_cours", "termine", "rejete")}
    pc = sum(1 for p in proc if p["status"] == "en_cours" and p.get("pc_needed"))
    l = [f"# Rapport — semaine {week} — passage {passage} — "
         f"{instant.astimezone(PARIS).strftime('%Y-%m-%d %H:%M')} (Paris)", ""]
    if resume:
        l.append(f"- Quota : {resume['units']} unités"
                 + (f" (arrêt : {resume['arret_quota']})" if resume["arret_quota"] else ""))
        l.append(f"- Ce passage : {resume['nouvelles']} vidéo(s) nouvelle(s), "
                 f"{resume['rejetees']} rejetée(s), {resume['provisoires']} score(s) provisoire(s)")
        if resume["non_geres"]:
            l.append(f"- Modes non gérés [EN ATTENTE] : {', '.join(sorted(resume['non_geres']))}")
    l.append(f"- Semaine : {compte['en_cours']} en cours (dont {pc} pour le PC), "
             f"{compte['termine']} terminée(s), {compte['rejete']} rejetée(s)")
    if res.get("gelee"):
        l.append("- Semaine gelée : classement non recalculé.")
    else:
        l.append("- Classements : " + (", ".join(f"{c} {n}" for c, n in sorted(res["fichiers"].items()))
                                       or "aucun"))
        av = res["a_verifier"]
        l += ["", f"## À vérifier ({len(av)})"]
        for cle, x in av[:50]:
            l.append(f"- {cle} · {x['channel']} · {x['score']['total']} · {x['video_id']} · {x['notes']}")
        if len(av) > 50:
            l.append(f"- … et {len(av) - 50} autre(s)")
        l += ["", "## Alertes boss"] + [f"- {a}" for a in res["alertes_boss"] or ["rien"]]
    erreurs = (resume["erreurs"] if resume else []) + alertes
    l += ["", "## Erreurs et alertes"] + [f"- {e}" for e in erreurs or ["rien"]]
    d.ecrire(f"runs/{week}/_rapport.md", "\n".join(l) + "\n")


def lancer(passage, instant, force=False, semaine=None, d=None, config=None):
    d, config = d or Donnees(), config or charger_config()
    alertes, resume = [], None
    if passage in ("daily", "weekly"):
        cr = config["creneaux"][passage]
        jour = JEUDI if passage == "weekly" else None
        if not force and not dans_creneau(instant, cr["debut"], cr["fin"], jour):
            print(f"{passage} : hors créneau, rien à faire.")
            return
        courante = id_semaine(instant)
        week = courante if passage == "daily" else semaine_precedente(courante)
        meta = ouvrir_semaine(d, week)
        aujourd_hui = instant.astimezone(PARIS).date().isoformat()
        if not force and meta.get("passages", {}).get(passage) == aujourd_hui:
            print(f"{passage} : déjà fait aujourd'hui.")
            return
        debut, fin_semaine = bornes(week)
        fin = instant if passage == "daily" else fin_semaine
        resume = passage_recherche(d, config, week, debut, fin, meta.get("frozen"), instant)
        if passage == "daily":
            prec = d.meta(semaine_precedente(week))
            if prec and not prec.get("frozen"):
                alertes.append(f"semaine {prec['week']} en attente de gel (passage PC hebdomadaire)")
        meta = d.meta(week)
        meta.setdefault("passages", {})[passage] = aujourd_hui
        d.ecrire(f"runs/{week}/_meta.json", meta)
    else:
        week = semaine or id_semaine(instant)
    res = classement.calculer(week, d, config, instant)
    ecrire_rapport(d, week, passage, instant, resume, res, alertes)
    print((d.data / "runs" / week / "_rapport.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("passage", choices=["daily", "weekly", "classement"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--maintenant", help="instant simulé, ISO 8601 (tests)")
    ap.add_argument("--semaine")
    a = ap.parse_args()
    lancer(a.passage, parse_iso(a.maintenant) if a.maintenant else maintenant(), a.force, a.semaine)
