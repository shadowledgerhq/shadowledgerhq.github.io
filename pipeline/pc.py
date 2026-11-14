"""Passages du PC d'Alexis — docs/SPEC_ETAPE1.md §6 et §2.1.

  python3 pipeline/pc.py daily  [--no-git] [--whisper] [--max N] [--garder-ocr]   (planificateur, 20:30)
  python3 pipeline/pc.py weekly [--no-git] [--whisper] [--max N]   (planificateur, jeudi 01:15)

Chaque passage : git pull --rebase -> sous-titres (yt-dlp) [+ Whisper] sur les vidéos `en_cours`
et `pc_needed` -> tris 3-4 (images : yt-dlp + ffmpeg + tesseract, OCR sur l'image entière, recadrages
[EN ATTENTE]) -> classement -> rapport -> git push. `weekly` travaille sur la semaine écoulée, puis la gèle si `pc.geler` est vrai
(faux tant que l'OCR n'est pas codé), et ouvre la nouvelle semaine.
PC éteint : rien n'est perdu, le passage suivant reprend ce qui est `en_cours`.
Outils externes : git, yt-dlp (obligatoires), ffmpeg + tesseract (tris 3-4), whisper (facultatif). Python >= 3.9, `pip install tzdata` sous Windows.
"""
import argparse
import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import classement
from donnees import RACINE, Donnees, ajouter_rejet, charger_config
from etape1 import ecrire_rapport, ouvrir_semaine
from semaine import PARIS, id_semaine, iso_utc, maintenant, parse_iso, semaine_precedente
import ocr_ecrans
from tri1 import lectures_texte


class OutilAbsent(Exception):
    pass


class GitErreur(Exception):
    pass


class OcrTropLent(Exception):
    """tesseract a dépassé son délai sur une image : l'image est ignorée, le passage continue."""


def est_429(e):
    return "429" in str(e) or "too many requests" in str(e).lower()


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

    def _lancer(self, cmd, timeout, env=None):
        if shutil.which(cmd[0]) is None and self.executer is subprocess.run:
            raise OutilAbsent(f"{cmd[0]} introuvable (à installer, voir pipeline/pc.py)")
        # UTF-8 explicite : sous Windows, text=True seul décode en cp1252 et abîme le coréen lu par tesseract
        r = self.executer(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, **({"env": env} if env else {}))
        if r.returncode != 0:
            raise RuntimeError(f"{cmd[0]} code {r.returncode} : {(r.stderr or '')[-200:].strip()}")
        return r.stdout

    def sous_titres(self, video_id, dossier):
        """Texte de tous les sous-titres trouvés (ko, ja, en, fr, zh), '' s'il n'y en a pas."""
        self._lancer([self.cfg["yt_dlp"], *self.cfg.get("yt_dlp_options", []), "--sleep-requests", "1",
                      "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", self.cfg["sous_titres_langues"], "--sub-format", "vtt",
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


    # --- tris 3-4 : images ---
    def telecharger(self, video_id, dossier):
        """Télécharge la vidéo (basse résolution, sans audio) dans `dossier` ; retourne le chemin du fichier."""
        cfg = self.cfg["images"]
        self._lancer([self.cfg["yt_dlp"], *self.cfg.get("yt_dlp_options", []), "-f", cfg["format_video"], "-o", f"{dossier}/{video_id}.%(ext)s",
                      f"https://www.youtube.com/watch?v={video_id}"], 1800)
        fichiers = [f for f in Path(dossier).glob(f"{video_id}.*") if f.suffix not in (".vtt", ".part", ".txt", ".mp3")]
        if not fichiers:
            raise RuntimeError("vidéo non téléchargée")
        return fichiers[0]

    def images(self, chemin, segments, dossier):
        """Images PNG des segments (début, durée, pas) en secondes ; retourne [(t, chemin_png)]."""
        trouvees = []
        for k, (debut, duree, pas) in enumerate(segments):
            self._lancer([self.cfg["images"]["ffmpeg"], "-v", "error", "-ss", str(debut), "-t", str(duree), "-i", str(chemin),
                          "-vf", f"fps=1/{pas}", "-q:v", "2", f"{dossier}/f{k}_%04d.png"], 900)
            trouvees += [(debut + i * pas, f) for i, f in enumerate(sorted(Path(dossier).glob(f"f{k}_*.png")))]
        return trouvees

    def reduire(self, png, largeur):
        """Copie réduite de l'image (largeur en pixels) pour le passage OCR rapide."""
        sortie = Path(png).with_name(Path(png).stem + "_p.png")
        self._lancer([self.cfg["images"]["ffmpeg"], "-v", "error", "-y", "-i", str(png),
                      "-vf", f"scale={int(largeur)}:-2", str(sortie)], 60)
        return sortie

    def empreinte(self, png):
        return hashlib.md5(Path(png).read_bytes()).hexdigest()

    def ocr(self, png, langues=None, psm=6, timeout=120):
        """Texte de l'image entière (tesseract). OMP_THREAD_LIMIT=1 : sous Windows, le multithread d'OpenMP ralentit
        beaucoup tesseract. Les recadrages par zone sont [EN ATTENTE]."""
        cfg = self.cfg["images"]
        try:
            return self._lancer([cfg["tesseract"], str(png), "stdout", "-l", langues or cfg["ocr_langues"],
                                 "--psm", str(psm)], timeout, env={**os.environ, "OMP_THREAD_LIMIT": "1"}) or ""
        except subprocess.TimeoutExpired:
            raise OcrTropLent(f"tesseract > {timeout} s")


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
            if est_429(e):  # YouTube limite le débit : vidéo reportée au prochain passage (rien n'est marqué)
                return lectures, "reporte", f"{vid} : 429 Too Many Requests, reportée au prochain passage"
            return lectures, "erreur", f"{vid} : {e}"
    if texte.strip():
        nouvelles, _ = lectures_texte(meta, [("sous-titres", texte)], config)
        lectures = fusionner_lectures(lectures, nouvelles)
    return lectures, etat, None


SOURCES_ECRAN = ("miniature", "debut-fin", "video-complete", "record")
SOURCES_TEXTE = ("titre", "description", "sous-titres")


def segments_tri(tri, duree_s, cfg):
    """SPEC §3 : tri 3 = 10 premières secondes + 30 dernières, 1 image / 2 s ; tri 4 = vidéo entière, 1 image / 10 s.
    Retourne [(début, durée, pas)] en secondes (fusionnés si les deux segments du tri 3 se touchent)."""
    if tri == 4:
        return [(0, int(duree_s), cfg["tri4_pas_s"])]
    debut, fin, pas = cfg["tri3_debut_s"], cfg["tri3_fin_s"], cfg["tri3_pas_s"]
    if duree_s <= debut + fin:
        return [(0, int(duree_s), pas)]
    return [(0, debut, pas), (int(duree_s - fin), fin, pas)]


def fusionner_ecrans(lectures, vid, nouvelles):
    """Les lectures d'écran de la vidéo remplacent ses lectures de texte pour les mêmes modes (le score lu à
    l'écran vaut mieux que celui du titre) ; une même image lue plusieurs fois ne compte qu'une fois."""
    modes = {l["mode"] for l in nouvelles}
    reste = [l for l in lectures if not (l["video_id"] == vid and l["mode"] in modes and l["score_source"] in SOURCES_TEXTE)]
    ecran = [l for l in reste + nouvelles if l["video_id"] == vid and l["score_source"] in SOURCES_ECRAN]
    autres = [l for l in reste if not (l["video_id"] == vid and l["score_source"] in SOURCES_ECRAN)]
    return autres + ocr_ecrans.dedoublonner_lectures(ecran)


def suffisant(lectures, vid, modes):
    """Le tri 3 suffit : BOT et HOTM = 1 lecture sûre ; POC et GB = 2 runs sûres (2 groupes / équipes)."""
    sures = [l for l in lectures if l["video_id"] == vid and l["confidence"] == "sur"]
    if not modes:
        return False
    return all(len([l for l in sures if l["mode"] == m]) >= (2 if m in ("poc", "gb") else 1) for m in modes)


MARQUEURS_ECRAN = ("results", "phase 1", "play time", "rage count", "personal record", "final score", "hunter rank",
                   "합산", "증명", "클리어", "이번", "플레이어 스코어", "계승자")


def langues_ocr(meta, cfg):
    """Langues tesseract selon les modes de la vidéo (`images.ocr_langues_mode`) : BOT et GB = client anglais,
    POC et HOTM = coréen (SPEC §3.1). Mode inconnu : `images.ocr_langues`. Moins de langues = OCR plus rapide."""
    par_mode, langs = cfg.get("ocr_langues_mode", {}), []
    for m in meta.get("mode_guess", []):
        for l in par_mode.get(m, cfg["ocr_langues"]).split("+"):
            if l not in langs:
                langs.append(l)
    return "+".join(langs) or cfg["ocr_langues"]


def ressemble_ecran(texte):
    bas = (texte or "").lower()
    return any(m in bas for m in MARQUEURS_ECRAN)


def traiter_images(vid, meta, outils, config, lectures, pc, jour, journal=lambda m: None, ocr_debug=None,
                   horloge=time.monotonic):
    """Tri 3, puis tri 4 si le tri 3 ne suffit pas. Retourne (lectures, avertissement | None, reporte).
    Par image : doublon exact ignoré ; OCR rapide (image réduite, `psm` clairsemé) puis OCR complet seulement si le
    texte ressemble à un écran RESULT ; image trop lente = ignorée. Budget de temps par vidéo (`budget_video_min`) :
    dépassé, la vidéo reste « partielle » et est reprise au passage suivant (`essais_max` fois, puis considérée faite)."""
    cfg = config["pc"]["images"]
    minutes = duree_minutes(meta.get("duration"))
    if minutes is None or minutes > cfg["max_minutes"]:
        return lectures, f"{vid} : durée {meta.get('duration')} hors limite ({cfg['max_minutes']} min), images non traitées", False
    langs = langues_ocr(meta, cfg)
    fin = horloge() + cfg.get("budget_video_min", 15) * 60
    with tempfile.TemporaryDirectory() as tmp:
        try:
            journal("  téléchargement…")
            chemin = outils.telecharger(vid, tmp)
            for tri in (3, 4):
                if pc.get(f"tri{tri}") == "fait":
                    continue
                nouvelles, st, complet, vus = [], {"images": 0, "doublons": 0, "candidates": 0, "lentes": 0}, True, {}
                t0 = horloge()
                for t, png in outils.images(chemin, segments_tri(tri, minutes * 60, cfg), tmp):
                    if horloge() > fin:
                        complet = False
                        break
                    st["images"] += 1
                    h = outils.empreinte(png)
                    if h in vus:
                        st["doublons"] += 1
                        texte = vus[h]
                    else:
                        texte = vus[h] = _ocr_image(outils, png, langs, cfg, st)
                    if ocr_debug and texte:  # texte lu + image d'origine (pour voir l'écran réel)
                        Path(ocr_debug).mkdir(parents=True, exist_ok=True)
                        (Path(ocr_debug) / f"{vid}_tri{tri}_{t}.txt").write_text(texte, encoding="utf-8")
                        try:
                            shutil.copyfile(png, Path(ocr_debug) / f"{vid}_tri{tri}_{t}.png")
                        except OSError:
                            pass
                    nouvelles += ocr_ecrans.lectures_depuis_texte(texte, meta, config,
                                                                  "debut-fin" if tri == 3 else "video-complete", t)
                    Path(png).unlink(missing_ok=True)
                lectures = fusionner_ecrans(lectures, vid, nouvelles)
                journal(f"  tri {tri} : {st['images']} image(s), {st['candidates']} candidate(s) à l'OCR complet, "
                        f"{len(nouvelles)} écran(s) lu(s), {st['lentes']} trop lente(s), {st['doublons']} doublon(s), "
                        f"{int(horloge() - t0)} s" + ("" if complet else " — BUDGET DÉPASSÉ"))
                if not complet:
                    pc["date"] = jour
                    pc["essais"] = pc.get("essais", 0) + 1
                    if pc["essais"] < cfg.get("essais_max", 2):
                        pc[f"tri{tri}"] = "partiel"
                        return lectures, f"{vid} : images tri {tri} partielles (budget {cfg.get('budget_video_min', 15)} min), reprises au prochain passage", False
                    pc[f"tri{tri}"] = "fait"
                    return lectures, f"{vid} : images tri {tri} abandonnées après {pc['essais']} essais (budget dépassé)", False
                pc[f"tri{tri}"], pc["date"] = "fait", jour
                if tri == 3 and suffisant(lectures, vid, set(meta.get("mode_guess", []))):
                    pc["tri4"] = "inutile"
                    break
        except OutilAbsent:
            raise
        except Exception as e:
            if est_429(e):
                return lectures, f"{vid} : 429 Too Many Requests (téléchargement), reportée au prochain passage", True
            return lectures, f"{vid} : images : {e}", False
    return lectures, None, False


def _ocr_image(outils, png, langs, cfg, st):
    """Texte d'une image ; "" si elle ne ressemble pas à un écran RESULT ou si tesseract est trop lent."""
    try:
        if cfg.get("ocr_rapide", True):
            petit = outils.reduire(png, cfg.get("ocr_largeur_rapide", 960))
            rapide = outils.ocr(petit, langs, cfg.get("ocr_psm_rapide", 11), cfg.get("ocr_timeout_rapide_s", 40))
            Path(petit).unlink(missing_ok=True)
            if not ressemble_ecran(rapide):
                return ""
        st["candidates"] += 1
        return outils.ocr(png, langs, 6, cfg.get("ocr_timeout_s", 90))
    except OcrTropLent:
        st["lentes"] += 1
        return ""


def rejeter_sans_score(d, week, jour):
    """Au gel (SPEC §6) : vidéo sans aucun score après le tri 4 -> rejected `pas_de_score`."""
    processed, lectures, rejected, titres = d.processed(), d.lectures(week), d.rejected(week), d.videos(week)
    avec_score = {l["video_id"] for l in lectures if l.get("score") is not None}
    n = 0
    for vid, p in processed.items():
        if p.get("week") == week and p["status"] == "en_cours" and (p.get("pc") or {}).get("tri4") == "fait" and vid not in avec_score:
            m = titres.get(vid, {})
            ajouter_rejet(rejected, {"video_id": vid, "channel_id": p["channel_id"], "title": m.get("title", ""),
                                     "published_at": p["published_at"], "mode_guess": "/".join(p.get("modes", [])) or None,
                                     "reason": "pas_de_score", "detail": "", "last_tri": 4, "date": jour})
            p.update(status="rejete", updated_at=jour, pc_needed=False)
            n += 1
    if n:
        d.ecrire(f"rejected/{week}.json", rejected)
        d.ecrire("processed.json", processed)
    return n


def annoter_non_verifies(d, week):
    """Au gel : les lignes seulement provisoires restent archivées, rank null, mention « non vérifié »."""
    dossier = d.data / "runs" / week
    for f in sorted(dossier.glob("*.json")):
        if f.stem.startswith("_"):
            continue
        lignes = d.lire(f"runs/{week}/{f.name}", [])
        for l in lignes:
            if l.get("confidence") != "sur" and "non vérifié" not in l.get("notes", ""):
                l["notes"] = (l["notes"] + "; " if l.get("notes") else "") + "non vérifié"
        d.ecrire(f"runs/{week}/{f.name}", lignes)


def lancer(passage, instant, d=None, config=None, outils=None, git=None, whisper=False, maximum=None, images=None,
           journal=None, dormir=None, horloge=time.monotonic, ocr_debug=None, seulement=None):
    """`journal(ligne)` : progression (print en production) ; `dormir(s)` : pause entre vidéos (time.sleep en
    production). Les deux sont inertes par défaut (tests). `_lectures.json` et `processed.json` sont écrits après
    chaque vidéo : un arrêt (PC éteint, Ctrl+C) ne perd que la vidéo en cours."""
    d, config = d or Donnees(), config or charger_config()
    outils = outils or Outils(config["pc"])
    journal, dormir = journal or (lambda m: None), dormir or (lambda s: None)
    alertes, jour = [], instant.astimezone(PARIS).date().isoformat()
    if git:
        git.tirer()
    courante = id_semaine(instant)
    week = courante if passage == "daily" else semaine_precedente(courante)
    meta = ouvrir_semaine(d, week)
    if passage == "weekly":
        ouvrir_semaine(d, courante)
    pc_cfg = config["pc"]
    debut_passage = horloge()
    fin_passage = debut_passage + pc_cfg.get("budget_minutes", 180) * 60
    pause = pc_cfg.get("pause_s", 5)
    journal(f"Passage PC {passage} — semaine {week}")

    traitees = 0
    if meta.get("frozen"):
        alertes.append(f"semaine {week} déjà gelée : rien à traiter")
    else:
        processed, videos, lectures = d.processed(), d.videos(week), d.lectures(week)

        def sauver():
            d.ecrire(f"runs/{week}/_lectures.json", lectures)
            d.ecrire("processed.json", processed)

        def titre(vid):
            return (videos.get(vid, {}).get("title") or "")[:50]

        a_faire = [v for v, p in processed.items() if p.get("week") == week and p["status"] == "en_cours"
                   and (not seulement or v in seulement) and p.get("pc_needed") and (p.get("pc") or {}).get("sous_titres") not in ("fait", "absent")]
        limite = maximum or pc_cfg["max_videos"]
        if len(a_faire) > limite:
            alertes.append(f"{len(a_faire) - limite} vidéo(s) reportée(s) au prochain passage (limite {limite})")
        lot = a_faire[:limite]
        journal(f"Sous-titres : {len(lot)} vidéo(s)")
        try:
            for n, vid in enumerate(lot, 1):
                if horloge() > fin_passage:
                    alertes.append(f"budget de temps du passage atteint ({pc_cfg.get('budget_minutes', 180)} min) : "
                                   f"{len(lot) - n + 1} vidéo(s) de sous-titres reportée(s)")
                    break
                journal(f"[{n}/{len(lot)}] {vid} « {titre(vid)} » : sous-titres…")
                if vid not in videos:
                    alertes.append(f"{vid} : métadonnées absentes de _videos.json")
                    continue
                t0 = horloge()
                lectures, etat, avert = traiter_video(vid, videos[vid], outils, config, lectures, whisper, jour)
                journal(f"  → {etat} ({int(horloge() - t0)} s)")
                if avert:
                    alertes.append(avert)
                if etat == "reporte":  # 429 : on s'arrête, YouTube limite le débit de cette adresse
                    alertes.append("429 : sous-titres arrêtés pour ce passage, les vidéos restantes sont reportées")
                    break
                processed[vid].setdefault("pc", {}).update(sous_titres=etat, date=jour)
                processed[vid]["updated_at"] = jour
                processed[vid]["last_tri"] = max(processed[vid].get("last_tri", 0), 1)
                traitees += 1
                sauver()
                if n < len(lot):
                    dormir(pause)
        except OutilAbsent as e:
            alertes.append(str(e))
        cfg_img = pc_cfg["images"]
        if cfg_img["actif"] if images is None else images:
            a_images = [v for v, p in processed.items() if p.get("week") == week and p["status"] == "en_cours" and p.get("pc_needed")
                        and (not seulement or v in seulement) and v in videos and (p.get("pc") or {}).get("tri4") not in ("fait", "inutile")]
            lim_img = min(maximum, cfg_img["max_videos"]) if maximum else cfg_img["max_videos"]  # --max limite aussi les images
            if len(a_images) > lim_img:
                alertes.append(f"{len(a_images) - lim_img} vidéo(s) reportée(s) pour les images (limite {lim_img})")
            lot = a_images[:lim_img]
            journal(f"Images (tris 3-4) : {len(lot)} vidéo(s)")
            try:
                for n, vid in enumerate(lot, 1):
                    if horloge() > fin_passage:
                        alertes.append(f"budget de temps du passage atteint ({pc_cfg.get('budget_minutes', 180)} min) : "
                                       f"{len(lot) - n + 1} vidéo(s) d'images reportée(s)")
                        break
                    journal(f"[{n}/{len(lot)}] {vid} « {titre(vid)} » : images ({', '.join(videos[vid].get('mode_guess', []))})")
                    etat = dict(processed[vid].get("pc") or {})
                    t0 = horloge()
                    lectures, avert, reporte = traiter_images(vid, videos[vid], outils, config, lectures, etat, jour,
                                                              journal, ocr_debug, horloge)
                    journal(f"  → {int(horloge() - t0)} s" + (f" — {avert}" if avert else ""))
                    if avert:
                        alertes.append(avert)
                    if etat:
                        processed[vid]["pc"] = etat
                        processed[vid]["updated_at"] = jour
                    if etat.get("tri3") == "fait":
                        processed[vid]["last_tri"] = max(processed[vid].get("last_tri", 0), 3)
                    if etat.get("tri4") in ("fait", "inutile"):
                        processed[vid]["last_tri"] = 4 if etat["tri4"] == "fait" else processed[vid]["last_tri"]
                        processed[vid]["pc_needed"] = False
                        if any(l["video_id"] == vid and l.get("score") is not None for l in lectures):
                            processed[vid]["status"] = "termine"
                    sauver()
                    if reporte:
                        alertes.append("429 : images arrêtées pour ce passage, les vidéos restantes sont reportées")
                        break
                    if n < len(lot):
                        dormir(pause)
            except OutilAbsent as e:
                alertes.append(str(e))
        sauver()
        restantes = sum(1 for p in processed.values() if p.get("week") == week and p["status"] == "en_cours")
        if restantes:
            alertes.append(f"{restantes} vidéo(s) restent en_cours (tris 3-4 : OCR sur l'image entière, recadrages [EN ATTENTE])")
        journal(f"Terminé en {int((horloge() - debut_passage) // 60)} min : {traitees} vidéo(s) de sous-titres, {restantes} en_cours")

    res = classement.calculer(week, d, config, instant)
    if passage == "weekly" and not meta.get("frozen"):
        lignes, provisoires = sum(res["fichiers"].values()), len(res["a_verifier"]) if not res.get("gelee") else 0
        if not config["pc"].get("geler"):
            alertes.append(f"semaine {week} NON gelée (pc.geler = false : tris 3-4 non gérés)")
        elif lignes and provisoires == lignes:
            alertes.append(f"semaine {week} NON gelée : toutes les lignes sont provisoires (SPEC §6)")
        else:
            n = rejeter_sans_score(d, week, jour)
            annoter_non_verifies(d, week)
            meta["frozen"], meta["frozen_at"] = True, iso_utc(instant)
            d.ecrire(f"runs/{week}/_meta.json", meta)
            alertes.append(f"semaine {week} gelée ({n} vidéo(s) rejetée(s) pas_de_score)")
    ecrire_rapport(d, week, f"pc-{passage}", instant, None, res, alertes)
    if git:
        git.pousser(f"données: passage PC {passage} {jour}")
    return {"week": week, "traitees": traitees, "alertes": alertes}


if __name__ == "__main__":
    for flux in (sys.stdout, sys.stderr):  # titres coréens / japonais : la console Windows (cp1252) planterait sinon
        flux.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("passage", choices=["daily", "weekly"])
    ap.add_argument("--no-git", action="store_true", help="pas de pull/push (essai local)")
    ap.add_argument("--whisper", action="store_true", help="active Whisper (config pc.whisper_cmd requis)")
    ap.add_argument("--max", type=int, help="limite les vidéos traitées, sous-titres ET images")
    ap.add_argument("--video", action="append", help="ne traite que cette vidéo (identifiant YouTube ; répétable)")
    ap.add_argument("--garder-ocr", action="store_true", help="écrit le texte lu par tesseract et l'image dans logs/ocr/ (diagnostic)")
    ap.add_argument("--maintenant", help="instant simulé ISO 8601 (tests)")
    a = ap.parse_args()
    try:
        r = lancer(a.passage, parse_iso(a.maintenant) if a.maintenant else maintenant(),
                   git=None if a.no_git else Git(), whisper=a.whisper, maximum=a.max, seulement=set(a.video or []),
                   journal=lambda m: print(m, flush=True), dormir=time.sleep,
                   ocr_debug=(RACINE / "logs" / "ocr") if a.garder_ocr else None)
    except GitErreur as e:
        print(f"ERREUR git : {e}\nPassage interrompu (conflit ou réseau) : relancer plus tard.", file=sys.stderr)
        sys.exit(1)
    print(f"Semaine {r['week']} : {r['traitees']} vidéo(s) traitée(s).")
    for x in r["alertes"]:
        print("-", x)
