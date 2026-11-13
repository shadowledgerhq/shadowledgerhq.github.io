"""Passages du PC d'Alexis — docs/SPEC_ETAPE1.md §6 et §2.1.

  python3 pipeline/pc.py daily  [--no-git] [--whisper] [--max N]   (planificateur, 20:30)
  python3 pipeline/pc.py weekly [--no-git] [--whisper] [--max N]   (planificateur, jeudi 01:15)

Chaque passage : git pull --rebase -> sous-titres (yt-dlp) [+ Whisper] sur les vidéos `en_cours`
et `pc_needed` -> tris 3-4 (OCR : [EN ATTENTE], les vidéos restent en_cours) -> classement ->
rapport -> git push. `weekly` travaille sur la semaine écoulée, puis la gèle si `pc.geler` est vrai
(faux tant que l'OCR n'est pas codé), et ouvre la nouvelle semaine.
PC éteint : rien n'est perdu, le passage suivant reprend ce qui est `en_cours`.
Outils externes : git, yt-dlp (obligatoires), ffmpeg + whisper (facultatifs). Python >= 3.9, `pip install tzdata` sous Windows.
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import classement
from donnees import RACINE, Donnees, charger_config
from etape1 import ecrire_rapport, ouvrir_semaine
from semaine import PARIS, id_semaine, iso_utc, maintenant, parse_iso, semaine_precedente
from tri1 import lectures_texte


class OutilAbsent(Exception):
    pass


class GitErreur(Exception):
    pass


# --- texte des sous-titres ------------------------------------------------------------------

def vtt_vers_texte(vtt):
    """Texte brut d'un fichier .vtt : sans en-tête, horodatages ni balises, sans lignes répétées
    (les sous-titres automatiques répètent chaque ligne)."""
    lignes = []
    for l in vtt.splitlines():
        l = l.strip()
        if not l or l.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or "-->" in l or l.isdigit():
            continue
        l = html.unescape(re.sub(r"<[^>]+>", "", l)).strip()
        if l and (not lignes or lignes[-1] != l):
            lignes.append(l)
    return "\n".join(lignes)


def duree_minutes(iso):
    """'PT1H2M3S' -> minutes (flottant) ; None si illisible."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 60 + mi + s / 60


class Outils:
    """Programmes externes. `executer` est injectable pour les tests."""

    def __init__(self, config_pc, executer=subprocess.run):
        self.cfg, self.executer = config_pc, executer

    def _lancer(self, cmd, timeout):
        if shutil.which(cmd[0]) is None and self.executer is subprocess.run:
            raise OutilAbsent(f"{cmd[0]} introuvable (à installer, voir pipeline/pc.py)")
        r = self.executer(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"{cmd[0]} code {r.returncode} : {(r.stderr or '')[-200:].strip()}")

    def sous_titres(self, video_id, dossier):
        """Texte de tous les sous-titres trouvés (ko, ja, en, fr, zh), '' s'il n'y en a pas."""
        self._lancer([self.cfg["yt_dlp"], "--skip-download", "--write-subs", "--write-auto-subs",
                      "--sub-langs", self.cfg["sous_titres_langues"], "--sub-format", "vtt",
                      "-o", f"{dossier}/{video_id}.%(ext)s", f"https://www.youtube.com/watch?v={video_id}"], 300)
        return "\n".join(vtt_vers_texte(f.read_text(encoding="utf-8", errors="replace"))
                         for f in sorted(Path(dossier).glob(f"{video_id}.*.vtt")))

    def whisper(self, video_id, dossier):
        """Transcription locale (coûteuse) ; None si Whisper n'est pas configuré."""
        if not self.cfg.get("whisper_cmd"):
            return None
        audio = f"{dossier}/{video_id}.mp3"
        self._lancer([self.cfg["yt_dlp"], "-x", "--audio-format", "mp3", "-o", f"{dossier}/{video_id}.%(ext)s",
                      f"https://www.youtube.com/watch?v={video_id}"], 900)
        self._lancer([self.cfg["whisper_cmd"], audio, "--model", self.cfg.get("whisper_model", "small"),
                      "--output_format", "txt", "--output_dir", str(dossier)], 3600)
        txt = Path(dossier) / f"{video_id}.txt"
        return txt.read_text(encoding="utf-8", errors="replace") if txt.exists() else ""


# --- git ------------------------------------------------------------------------------------

class Git:
    def __init__(self, racine=RACINE):
        self.racine = racine

    def _run(self, *args):
        r = subprocess.run(["git", *args], cwd=self.racine, capture_output=True, text=True)
        if r.returncode != 0:
            raise GitErreur(f"git {args[0]} : {(r.stderr or r.stdout)[-300:].strip()}")
        return r.stdout

    def tirer(self):
        self._run("pull", "--rebase", "origin", "main")

    def pousser(self, message):
        self._run("add", "data")
        if not self._run("status", "--porcelain", "data").strip():
            return False
        self._run("commit", "-m", message)
        self._run("pull", "--rebase", "origin", "main")  # une seule tentative ; conflit -> GitErreur
        self._run("push", "origin", "HEAD:main")
        return True


# --- traitement -----------------------------------------------------------------------------

def fusionner_lectures(lectures, nouvelles):
    """Ajoute les lectures issues des sous-titres sans doubler une lecture existante de la même
    vidéo et du même mode : l'écart est alors noté (idempotent)."""
    for n in nouvelles:
        exist = next((l for l in lectures if l["video_id"] == n["video_id"] and l["mode"] == n["mode"]), None)
        if exist is None:
            lectures.append(n)
        elif exist["score"] != n["score"]:
            note = f"sous-titres : {n['notes'][0].split(' : ', 1)[-1]}"
            if note not in exist["notes"]:
                exist["notes"].append(note)
    return lectures


def traiter_video(vid, meta, outils, config, lectures, whisper_actif, jour):
    """Sous-titres puis (si rien) Whisper. Retourne (lectures, état, avertissement|None)."""
    cfg = config["pc"]
    with tempfile.TemporaryDirectory() as tmp:
        try:
            texte = outils.sous_titres(vid, tmp)
            etat = "fait" if texte.strip() else "absent"
            if etat == "absent" and whisper_actif and not any(l["video_id"] == vid and l["score"] is not None for l in lectures):
                minutes = duree_minutes(meta.get("duration"))
                if minutes is not None and minutes <= cfg["whisper_max_minutes"]:
                    texte = outils.whisper(vid, tmp) or ""
                    etat = "fait" if texte.strip() else "absent"
        except OutilAbsent:
            raise
        except Exception as e:  # une vidéo en erreur ne bloque pas les autres
            return lectures, "erreur", f"{vid} : {e}"
    if texte.strip():
        nouvelles, _ = lectures_texte(meta, [("sous-titres", texte)], config)
        lectures = fusionner_lectures(lectures, nouvelles)
    return lectures, etat, None


def lancer(passage, instant, d=None, config=None, outils=None, git=None, whisper=False, maximum=None):
    d, config = d or Donnees(), config or charger_config()
    outils = outils or Outils(config["pc"])
    alertes, jour = [], instant.astimezone(PARIS).date().isoformat()
    if git:
        git.tirer()
    courante = id_semaine(instant)
    week = courante if passage == "daily" else semaine_precedente(courante)
    meta = ouvrir_semaine(d, week)
    if passage == "weekly":
        ouvrir_semaine(d, courante)

    traitees = 0
    if meta.get("frozen"):
        alertes.append(f"semaine {week} déjà gelée : rien à traiter")
    else:
        processed, videos, lectures = d.processed(), d.videos(week), d.lectures(week)
        a_faire = [v for v, p in processed.items() if p.get("week") == week and p["status"] == "en_cours"
                   and p.get("pc_needed") and (p.get("pc") or {}).get("sous_titres") not in ("fait", "absent")]
        limite = maximum or config["pc"]["max_videos"]
        if len(a_faire) > limite:
            alertes.append(f"{len(a_faire) - limite} vidéo(s) reportée(s) au prochain passage (limite {limite})")
        try:
            for vid in a_faire[:limite]:
                if vid not in videos:
                    alertes.append(f"{vid} : métadonnées absentes de _videos.json")
                    continue
                lectures, etat, avert = traiter_video(vid, videos[vid], outils, config, lectures, whisper, jour)
                if avert:
                    alertes.append(avert)
                processed[vid]["pc"] = {"sous_titres": etat, "date": jour}
                processed[vid]["updated_at"] = jour
                processed[vid]["last_tri"] = max(processed[vid].get("last_tri", 0), 1)
                traitees += 1
        except OutilAbsent as e:
            alertes.append(str(e))
        d.ecrire(f"runs/{week}/_lectures.json", lectures)
        d.ecrire("processed.json", processed)
        restantes = sum(1 for p in processed.values() if p.get("week") == week and p["status"] == "en_cours")
        if restantes:
            alertes.append(f"tris 3-4 (OCR) : non gérés [EN ATTENTE] : {restantes} vidéo(s) restent en_cours")

    res = classement.calculer(week, d, config, instant)
    if passage == "weekly" and not meta.get("frozen"):
        lignes, provisoires = sum(res["fichiers"].values()), len(res["a_verifier"]) if not res.get("gelee") else 0
        if not config["pc"].get("geler"):
            alertes.append(f"semaine {week} NON gelée (pc.geler = false : tris 3-4 non gérés)")
        elif lignes and provisoires == lignes:
            alertes.append(f"semaine {week} NON gelée : toutes les lignes sont provisoires (SPEC §6)")
        else:
            meta["frozen"], meta["frozen_at"] = True, iso_utc(instant)
            d.ecrire(f"runs/{week}/_meta.json", meta)
            alertes.append(f"semaine {week} gelée")
    ecrire_rapport(d, week, f"pc-{passage}", instant, None, res, alertes)
    if git:
        git.pousser(f"données: passage PC {passage} {jour}")
    return {"week": week, "traitees": traitees, "alertes": alertes}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("passage", choices=["daily", "weekly"])
    ap.add_argument("--no-git", action="store_true", help="pas de pull/push (essai local)")
    ap.add_argument("--whisper", action="store_true", help="active Whisper (config pc.whisper_cmd requis)")
    ap.add_argument("--max", type=int)
    ap.add_argument("--maintenant", help="instant simulé ISO 8601 (tests)")
    a = ap.parse_args()
    try:
        r = lancer(a.passage, parse_iso(a.maintenant) if a.maintenant else maintenant(),
                   git=None if a.no_git else Git(), whisper=a.whisper, maximum=a.max)
    except GitErreur as e:
        print(f"ERREUR git : {e}\nPassage interrompu (conflit ou réseau) : relancer plus tard.", file=sys.stderr)
        sys.exit(1)
    print(f"Semaine {r['week']} : {r['traitees']} vidéo(s) traitée(s).")
    for x in r["alertes"]:
        print("-", x)
