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
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import classement
from donnees import RACINE, Donnees, JsonAbime, ajouter_rejet, charger_config, lire_json
from etape1 import ecrire_rapport, ouvrir_semaine
from semaine import PARIS, id_semaine, iso_utc, maintenant, parse_iso, semaine_precedente
import libelles_inconnus
import miniature
import chrono_bot
import ocr_ecrans
import rotation
import elements
import elements_hud
import hunters_results
import ordre_pc
import rapport_pc
import relectures
from tri1 import lectures_texte


def pid_vivant(pid):
    """Un processus d'identifiant `pid` tourne-t-il ? (Sous Windows `os.kill(pid, 0)` TUERAIT le processus : OpenProcess à la place.)"""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Verrou:
    """Un seul passage PC à la fois (daily, weekly, builds, essais) : fichier `logs/pc.lock` (PID, passage, début), créé de
    façon atomique. Verrou périmé (processus mort ou plus de `max_h` heures) : repris. `prendre()` -> (ok, texte du détenteur)."""

    def __init__(self, chemin, max_h=12):
        self.chemin, self.max_h, self.pris = Path(chemin), max_h, False
        self.perime = None          # v26 : détenteur d'un verrou périmé repris (passage interrompu : PC éteint, fenêtre fermée)

    def _detenteur(self):
        try:
            d = json.loads(self.chemin.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def prendre(self, nom, maintenant_ts=None):
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        ts = time.time() if maintenant_ts is None else maintenant_ts
        for _ in range(2):
            try:
                fd = os.open(str(self.chemin), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                d = self._detenteur()
                age_h = (ts - d.get("debut", 0)) / 3600
                if d.get("pid") and pid_vivant(int(d["pid"])) and age_h < self.max_h:
                    return False, f"{d.get('passage', '?')} (PID {d['pid']}, depuis {age_h * 60:.0f} min)"
                self.perime = d or None
                try:
                    self.chemin.unlink()                    # périmé : processus mort, ou trop ancien
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "passage": nom, "debut": ts}, f)
            self.pris = True
            return True, ""
        return False, "verrou illisible"

    def liberer(self):
        if self.pris:
            self.pris = False
            try:
                if self._detenteur().get("pid") == os.getpid():
                    self.chemin.unlink()
            except OSError:
                pass


class OutilAbsent(Exception):
    pass


class GitErreur(Exception):
    pass


class OcrTropLent(Exception):
    """tesseract a dépassé son délai sur une image : l'image est ignorée, le passage continue."""


def est_429(e):
    """YouTube limite ou bloque cette adresse : HTTP 429, ou anti-bot (« Sign in to confirm you're not a bot »,
    `-do-i-pass-cookies-to-yt-dlp`). Le lot s'arrête et les vidéos restantes sont reportées (rien n'est marqué)."""
    t = str(e).lower()
    return "429" in t or "too many requests" in t or "not a bot" in t or "pass-cookies" in t or "sign in to confirm" in t


# --- essai des réglages yt-dlp (anti-bot) ----------------------------------------------------

def strategies_ytdlp(avec_node=False):
    """Réglages yt-dlp essayés dans l'ordre. `--js-runtimes node` si Node.js est installé et pas Deno (YouTube exige
    un moteur JavaScript). Cookies : Firefox d'abord (Chrome/Edge récents chiffrent leurs cookies, lecture souvent impossible)."""
    base = ["--js-runtimes", "node"] if avec_node else []
    imp = ["--impersonate", "chrome"]
    out = [("réglages par défaut", base), ("imitation de Chrome", base + imp)]
    for nav in ("firefox", "edge", "chrome", "brave"):
        out.append((f"cookies de {nav}", base + imp + ["--cookies-from-browser", nav]))
    return out


def a_format_video(sortie):
    """Vrai si `yt-dlp -F` liste un vrai format vidéo (pas seulement les vignettes « mhtml »)."""
    return any(("video only" in l or re.search(r"\b(mp4|webm)\b", l)) and "mhtml" not in l and re.search(r"\b\d{3,4}x\d{3,4}\b", l)
               for l in sortie.splitlines())


def options_js():
    """YouTube exige un moteur JavaScript : Deno (pris par défaut), sinon Node.js ; [] si Deno présent. None si aucun des deux."""
    if shutil.which("deno"):
        return []
    return ["--js-runtimes", "node"] if shutil.which("node") else None


def tester_ytdlp(cfg_pc, video_id, executer=subprocess.run, journal=print):
    """Teste chaque réglage avec `yt-dlp -F` (aucun téléchargement) sur une vidéo ; retourne la liste d'options qui marche
    (ou None). S'arrête au premier succès."""
    avec_node = shutil.which("deno") is None and shutil.which("node") is not None
    for nom, opts in strategies_ytdlp(avec_node):
        o = Outils({**cfg_pc, "yt_dlp_options": opts}, executer)
        try:
            sortie = o._lancer([cfg_pc["yt_dlp"], *opts, "-F", f"https://www.youtube.com/watch?v={video_id}"], 120)
        except (RuntimeError, subprocess.TimeoutExpired, OutilAbsent) as e:
            journal(f"  ÉCHEC  {nom} : {str(e)[:150]}")
            continue
        if a_format_video(sortie):
            journal(f"  RÉUSSI {nom}")
            return opts
        journal(f"  ÉCHEC  {nom} : aucun format vidéo listé")
    return None


def profils_chrome(local_state=None):
    """Profils Chrome du PC : [(dossier, nom, adresse Google)], lus dans « Local State » (Windows)."""
    ls = Path(local_state or Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Local State")
    try:
        info = json.loads(ls.read_text(encoding="utf-8")).get("profile", {}).get("info_cache", {})
    except (OSError, ValueError):
        return []
    return [(d, v.get("name", ""), v.get("user_name", "")) for d, v in sorted(info.items())]


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
        r = self.executer(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
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
        self._lancer([self.cfg["yt_dlp"], *self.cfg.get("yt_dlp_options", []), "-x", "--audio-format", "mp3", "-o", f"{dossier}/{video_id}.%(ext)s",
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

    def images(self, chemin, segments, dossier, prefixe="f", hauteur=None):
        """Images PNG des segments (début, durée, pas) en secondes ; retourne [(t, chemin_png)]. `hauteur` : réduit les
        images à cette hauteur (tri 4 en 720p, SPEC v15) ; sinon résolution du fichier téléchargé (≤ 1080p)."""
        trouvees = []
        delai = self.cfg["images"].get("ffmpeg_delai_s", 300)
        for k, (debut, duree, pas) in enumerate(segments):
            cmd = [self.cfg["images"]["ffmpeg"], "-nostdin", "-v", "error", "-ss", str(debut), "-t", str(duree), "-i", str(chemin),
                   "-vf", (f"fps=1/{pas}" if float(pas).is_integer() and pas == int(pas) else f"fps={1 / pas:g}") + (f",scale=-2:{int(hauteur)}" if hauteur else ""), "-q:v", "2", f"{dossier}/{prefixe}{k}_%04d.png"]
            try:
                self._lancer(cmd, delai)
            except subprocess.TimeoutExpired:      # essai du 14/11 : ffmpeg bloqué 900 s sur une vidéo ; une seule nouvelle tentative
                for f in Path(dossier).glob(f"{prefixe}{k}_*.png"):
                    f.unlink(missing_ok=True)
                self._lancer(cmd, delai)
            trouvees += [(debut + i * pas, f) for i, f in enumerate(sorted(Path(dossier).glob(f"{prefixe}{k}_*.png")))]
        return trouvees

    def hauteurs(self, video_id):
        """Hauteurs (en pixels) des formats vidéo proposés par YouTube (`yt-dlp -F`), triées ; [] si illisible."""
        sortie = self._lancer([self.cfg["yt_dlp"], *self.cfg.get("yt_dlp_options", []), "-F",
                               f"https://www.youtube.com/watch?v={video_id}"], 120)
        return sorted({int(h) for _, h in re.findall(r"\b(\d{3,4})x(\d{3,4})\b", sortie)}, key=int)

    def reduire(self, png, largeur):
        """Copie réduite de l'image (largeur en pixels) pour le passage OCR rapide."""
        sortie = Path(png).with_name(Path(png).stem + "_p.png")
        self._lancer([self.cfg["images"]["ffmpeg"], "-nostdin", "-v", "error", "-y", "-i", str(png),
                      "-vf", f"scale={int(largeur)}:-2", str(sortie)], 60)
        return sortie

    def recadrer(self, png, zone, echelle=3, seuil=None):
        """Zone de l'image (x, y, largeur, hauteur en fractions), agrandie et en gris ; avec `seuil` (0-255) : noir et blanc
        puis inversé (texte sombre sur fond clair), ce qui aide tesseract sur les chiffres clairs des écrans de jeu."""
        x, y, l, h = zone
        sortie = Path(png).with_name(Path(png).stem + "_z.png")
        filtre = f"crop=iw*{l}:ih*{h}:iw*{x}:ih*{y},scale=iw*{echelle}:-1,format=gray"
        if seuil:
            filtre += f",lutyuv=y='if(gt(val,{int(seuil)}),255,0)',negate"
        self._lancer([self.cfg["images"]["ffmpeg"], "-nostdin", "-v", "error", "-y", "-i", str(png), "-vf", filtre,
                      "-frames:v", "1", str(sortie)], 60)
        return sortie

    def empreinte(self, png):
        return hashlib.md5(Path(png).read_bytes()).hexdigest()

    def dimensions(self, png):
        """(largeur, hauteur) d'une image PNG lue dans son en-tête ; None si illisible."""
        try:
            tete = Path(png).read_bytes()[:24]
            return struct.unpack(">II", tete[16:24]) if tete[:8] == b"\x89PNG\r\n\x1a\n" else None
        except (OSError, struct.error):
            return None

    def ocr(self, png, langues=None, psm=6, timeout=120, extra=None):
        """Texte de l'image entière (tesseract). OMP_THREAD_LIMIT=1 : sous Windows, le multithread d'OpenMP ralentit
        beaucoup tesseract. Les recadrages par zone sont [EN ATTENTE]."""
        cfg = self.cfg["images"]
        try:
            return self._lancer([cfg["tesseract"], str(png), "stdout", "-l", langues or cfg["ocr_langues"],
                                 "--psm", str(psm), *(extra or [])], timeout, env={**os.environ, "OMP_THREAD_LIMIT": "1"}) or ""
        except subprocess.TimeoutExpired:
            raise OcrTropLent(f"tesseract > {timeout} s")


# --- git ------------------------------------------------------------------------------------

class Git:
    """git avec délai maximal (jamais de fenêtre bloquée) et sans question au clavier. Les fichiers JSON de data/ sont
    vérifiés avant tout commit : un fichier abîmé (marqueurs de conflit, coupure) n'entre jamais dans l'historique."""
    DELAI_S = 180
    ATTENTES_RESEAU_S = (30, 90, 180)       # v28 : réseau coupé au `pull` -> 3 nouvelles tentatives (30 s, 90 s, 3 min) avant d'abandonner

    def __init__(self, racine=RACINE, delai_s=None, dormir=time.sleep):
        self.racine = racine
        self.delai_s = delai_s or self.DELAI_S
        self.dormir = dormir

    def _run(self, *args):
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"}
        try:
            r = subprocess.run(["git", *args], cwd=self.racine, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                               timeout=self.delai_s, env=env)
        except subprocess.TimeoutExpired:
            raise GitErreur(f"git {args[0]} : sans réponse après {self.delai_s} s (réseau ?)") from None
        if r.returncode != 0:
            raise GitErreur(f"git {args[0]} : {(r.stderr or r.stdout)[-300:].strip()}")
        return r.stdout

    def verifier_json(self):
        """Lève GitErreur en nommant les fichiers data/**/*.json illisibles de l'arbre de travail."""
        mauvais = []
        for f in sorted((Path(self.racine) / "data").rglob("*.json")):
            try:
                lire_json(f)
            except JsonAbime as e:
                mauvais.append(str(e))
            except OSError:
                pass
        if mauvais:
            raise GitErreur("JSON abîmé, rien n'est commité : " + " | ".join(mauvais[:5]))

    conflit_resolu = False          # v26 : un conflit sur data/ a été résolu automatiquement pendant ce passage (noté dans le rapport)

    exports_deplaces = ()           # v33 : fichiers d'`exports/` du PC mis de côté dans `exports/_local/` pendant ce passage

    def _liberer_exports(self):
        """v33 : fichiers NON suivis de `exports/` (Excel / PowerPoint régénérables) que `origin/main` contient aussi : DÉPLACÉS dans
        `exports/_local/` (ignoré par git) avant le pull / la fusion, sinon git refuse (« untracked working tree files would be
        overwritten », passage du 17/11). Rien n'est supprimé. Noté dans le bloc du passage (`exports_deplaces`). Retourne les
        fichiers déplacés (chemins d'origine)."""
        try:
            self._run("fetch", "origin", "main")
            locaux = [f for f in self._run("ls-files", "--others", "--exclude-standard", "exports").splitlines() if f.strip()]
            distants = set(self._run("ls-tree", "-r", "--name-only", "origin/main", "--", "exports").splitlines())
        except GitErreur:
            return []                                   # réseau coupé : le pull échouera de lui-même
        racine, deplaces = Path(self.racine), []
        if any(f in distants for f in locaux):
            try:        # ignoré par git même avant que le `.gitignore` du dépôt n'arrive sur le PC
                excl = racine / ".git/info/exclude"
                if "exports/_local/" not in (excl.read_text(encoding="utf-8") if excl.exists() else ""):
                    excl.parent.mkdir(parents=True, exist_ok=True)
                    with excl.open("a", encoding="utf-8") as fh:
                        fh.write("\nexports/_local/\n")
            except OSError:
                pass
        for f in locaux:
            if f in distants and not f.startswith("exports/_local/"):
                cible = racine / "exports/_local" / Path(f).relative_to("exports")
                if cible.exists():
                    cible = cible.with_name(f"{cible.stem}.{int(time.time())}{cible.suffix}")
                cible.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(racine / f), str(cible))
                deplaces.append(f)
        self.exports_deplaces = tuple(self.exports_deplaces) + tuple(deplaces)
        return deplaces

    def _rebase(self):
        """pull --rebase ; en cas d'échec, le rebase est abandonné (pas d'état « rebase en cours » qui bloque la suite), puis
        le conflit sur data/ est résolu automatiquement (`_resoudre_conflit`) : version distante pour les fichiers du passage
        GitHub, version du PC pour les tris 3-4. Une seule tentative ; si elle échoue, GitErreur."""
        self._liberer_exports()
        essai = 0
        while True:
            try:
                self._run("pull", "--rebase", "origin", "main")
                return
            except GitErreur as e:
                try:
                    self._run("rebase", "--abort")
                except GitErreur:
                    pass
                if not self._est_reseau(e):
                    self._resoudre_conflit(e)
                    return
                if essai >= len(self.ATTENTES_RESEAU_S):
                    raise                                      # pas un conflit : réseau toujours coupé
                self.dormir(self.ATTENTES_RESEAU_S[essai])
                essai += 1

    @staticmethod
    def _est_reseau(e):
        t = str(e).lower()
        return "network" in t or "resolve host" in t or "sans réponse" in t or "unable to access" in t

    def _resoudre_conflit(self, erreur):
        """Fusion (pas de rebase) avec `-X theirs` (= la version distante l'emporte sur les conflits de texte), puis, pour les
        fichiers modifiés par le PC : tris 3-4 (`PROPRES_PC`) = version du PC ; `processed.json` et `_lectures.json` = fusion
        par vidéo (`fusion_pc`) ; le reste (classements, vidéos, rapport GitHub…) reste distant : le passage le recalcule."""
        import fusion_pc
        locale = self._run("rev-parse", "HEAD").strip()
        try:
            self._run("fetch", "origin", "main")
            self._liberer_exports()
            base = self._run("merge-base", locale, "origin/main").strip()
            changes = [c for c in self._run("diff", "--name-only", base, locale).splitlines() if c.strip()]
            self._run("merge", "-X", "theirs", "--no-edit", "-m", "données: conflit git résolu automatiquement (PC)", "origin/main")
        except GitErreur as e2:
            try:
                self._run("merge", "--abort")
            except GitErreur:
                pass
            raise GitErreur(f"conflit git non résolu : {str(erreur)[:200]} | {e2}") from e2
        racine = Path(self.racine)
        for chemin in changes:
            cible = racine / chemin
            if fusion_pc.est_propre_pc(chemin):
                self._run("checkout", locale, "--", chemin)
            elif fusion_pc.fusion_json(chemin):
                try:
                    distant = json.loads(self._run("show", f"origin/main:{chemin}"))
                except (GitErreur, ValueError):
                    distant = None
                try:
                    local = json.loads(self._run("show", f"{locale}:{chemin}"))
                except (GitErreur, ValueError):
                    continue
                fusion = fusion_pc.fusionner(chemin, distant, local)
                if fusion is not None:
                    cible.write_text(json.dumps(fusion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.verifier_json()
        self._run("add", "data")
        if self._run("status", "--porcelain").strip():
            self._run("commit", "-m", "données: conflit git résolu automatiquement (PC)")
        self.conflit_resolu = True

    def tirer(self):
        # Reprise après un arrêt du PC / un plantage : les lectures du passage interrompu sont dans data/ (écrites après
        # chaque vidéo) mais pas encore commitées ; on les commite d'abord, sinon `pull --rebase` refuserait de tourner.
        self.verifier_json()
        self._run("add", "data")
        if self._run("status", "--porcelain", "data").strip():
            self._run("commit", "-m", "données: reprise après interruption du passage PC")
        try:
            self._rebase()
        except GitErreur as e:
            if "overwritten" in str(e) or "unstaged" in str(e) or "uncommitted" in str(e):
                raise GitErreur(f"{e}\nModifications locales dans data/ (essais avec --no-git ?) : lancer « git checkout -- data » "
                                "puis relancer.") from e
            raise

    def pousser_chemin(self, message, chemin):
        """Diagnostic (docs/essais/ocr) : commit d'un seul chemin, poussé sur une branche `claude/essai-pc-<horodatage>` (le
        workflow de fusion automatique la verse dans `main`), puis commit défait localement et fichiers retirés de l'arbre
        de travail. Aucun `pull` ni `rebase` : les résultats d'essai (`data/` modifié par `--no-git`) ne créent jamais de
        conflit. Le contenu arrive dans `main` ; le prochain `git pull` le récupère."""
        self._run("add", chemin)
        if not self._run("status", "--porcelain", chemin).strip():
            return False
        self._run("commit", "-m", message, "--", chemin)
        branche = "claude/essai-pc-" + maintenant().strftime("%Y%m%d-%H%M%S")
        try:
            self._run("push", "origin", f"HEAD:refs/heads/{branche}")
        finally:                                    # le commit local est défait quoi qu'il arrive
            self._run("reset", "--mixed", "HEAD~1")
            self._run("clean", "-fdq", "--", chemin)
            try:
                self._run("checkout", "--", chemin)
            except GitErreur:                       # chemin nouveau (absent de HEAD) : rien à restaurer
                pass
        return True

    def pousser(self, message):
        self.verifier_json()
        chemins = ["data"]
        if (Path(self.racine) / "docs" / "essais" / "ocr" / "libelles_inconnus").exists():
            chemins.append("docs/essais/ocr/libelles_inconnus")          # v24 : écrans de score à libellés inconnus
        if (Path(self.racine) / "docs" / "essais" / "composition" / "auto").exists():
            chemins.append("docs/essais/composition/auto")               # v33 : images de composition extraites (zones à définir)
        self._run("add", *chemins)
        if not self._run("status", "--porcelain", *chemins).strip():
            if self.conflit_resolu:                      # v26 : fusion locale (conflit résolu) pas encore poussée
                self._run("push", "origin", "HEAD:main")
                return True
            return False
        self._run("commit", "-m", message)
        self._rebase()                                   # une seule tentative ; conflit -> GitErreur (rebase abandonné)
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
                return lectures, "reporte", f"{vid} : 429 / anti-bot YouTube, reportée au prochain passage"
            return lectures, "erreur", f"{vid} : {e}"
    if texte.strip():
        nouvelles, _ = lectures_texte(meta, [("sous-titres", texte)], config)
        lectures = fusionner_lectures(lectures, nouvelles)
    return lectures, etat, None


SOURCES_ECRAN = ("miniature", "debut-fin", "video-complete", "record")
SOURCES_TEXTE = ("titre", "description", "sous-titres")
SOURCES_RESULTATS = ("debut-fin", "video-complete")


def segments_tri(tri, duree_s, cfg):
    """SPEC §3 : tri 3 = 10 premières secondes + 30 dernières, 1 image / 2 s ; tri 4 = vidéo entière, 1 image / 10 s.
    Retourne [(début, durée, pas)] en secondes (fusionnés si les deux segments du tri 3 se touchent)."""
    if tri == 4:
        return [(0, int(duree_s), cfg["tri4_pas_s"])]
    debut, fin, pas = cfg["tri3_debut_s"], cfg["tri3_fin_s"], cfg["tri3_pas_s"]
    if duree_s <= debut + fin:
        return [(0, int(duree_s), pas)]
    return [(0, debut, pas), (int(duree_s - fin), fin, pas)]


def est_texte(l):
    """Lecture issue d'un texte : titre, description, sous-titres, ou texte OCR de la miniature (v34 : `detail.texte_miniature`)."""
    return l["score_source"] in SOURCES_TEXTE or bool((l.get("detail") or {}).get("texte_miniature"))


def _est_ecran(l):
    """Lecture issue d'une image : écran reconnu, ou HUD de combat (sans score ni source depuis la v13). Le texte lu sur la miniature
    (v34) n'est PAS un écran."""
    return (l["score_source"] in SOURCES_ECRAN and not est_texte(l)) or (l.get("detail") or {}).get("ecran") in ("combat", "combat_sans_chrono")


def _elements_hud(png, config, lectures):
    """v31 : couleur des losanges d'élément du panneau d'équipe, attachée (`detail.elements_hud`) aux lectures de HUD de l'image."""
    cfg = (config or {}).get("elements_hud")
    cibles = [l for l in lectures if (l.get("detail") or {}).get("ecran") in ("combat", "combat_sans_chrono")]
    if cfg and cibles:
        els = elements_hud.lire_losanges(png, cfg)
        for l in cibles:
            l["detail"]["elements_hud"] = els


def _chasseurs_results(png, texte, config, meta, lectures):
    """v31 : identité des chasseurs par les portraits des 6 lignes du Results (banque `data/icons/hunters_results`) -> `detail.hunter_ids`
    + note « chasseurs reconnus : n/6 ». Apprend la banque quand un build `sûr` de la même run donne l'identité. Banque vide : rien."""
    cibles = [l for l in lectures if _est_results_gb(l) and l.get("score") is not None]
    if not cibles:
        return
    try:
        from PIL import Image
        with Image.open(png) as im:
            img = im.convert("RGB").copy()
        succ = ocr_ecrans.mise_en_page_results(texte, config) == "successeur"
        week = id_semaine(parse_iso(meta["published_at"]))
        builds = elements.charger_builds(RACINE / "data", week)
        ids_b = elements.ids_du_build(builds, {"mode": "gb", "video_id": meta["video_id"], "t": cibles[0].get("t")})
        if ids_b:
            import portraits
            hunters_results.apprendre(RACINE, ids_b, hunters_results.decouper(img, hunters_results.zones_portraits(config, succ)),
                                      portraits.charger_cartes(RACINE / "data" / "icons"), config)
        ids, n = hunters_results.lire(img, config, RACINE, succ)
    except Exception:
        return
    if ids and n:
        for l in cibles:
            l["detail"]["hunter_ids"] = [i for i in ids if i]
            l["notes"].append(f"chasseurs reconnus : {n}/6")


def _est_results_gb(l):
    return l["mode"] == "gb" and l["score_source"] in SOURCES_RESULTATS and (l.get("detail") or {}).get("ecran") != "combat"


def fusionner_ecrans(lectures, vid, nouvelles, config=None, duree_s=None):
    """Les lectures d'écran de la vidéo remplacent ses lectures de texte pour les mêmes modes (le score lu à
    l'écran vaut mieux que celui du titre) ; une même image lue plusieurs fois ne compte qu'une fois.
    v12 : le HUD GB (lectures sans score) ne remplace rien ; ses lectures sont regroupées par run
    (`ocr_ecrans.regrouper_hud`). Les lectures de l'écran Results sont regroupées en écrans, la plus complète est
    gardée et contrôlée (`ocr_ecrans.fusionner_results`)."""
    modes = {l["mode"] for l in nouvelles if l.get("score") is not None and not chrono_bot.echec_controle_bot(l)
             and not (l.get("detail") or {}).get("borne_basse")}     # v35 : un écran BOT en échec de contrôle ne remplace rien ; v36 : ni une borne basse (phases incomplètes)
    reste = [l for l in lectures if not (l["video_id"] == vid and l["mode"] in modes and est_texte(l))]
    ecran = [l for l in reste + nouvelles if l["video_id"] == vid and _est_ecran(l)]
    # v29 : contexte de l'exception « RC lu sur la dernière image » (SPEC §3.1) : RC du titre / de la description et durée de la
    # vidéo, gardés dans `detail` des lectures Results (les lectures de texte disparaissent à la fusion, la durée n'est pas relue)
    rc_texte = sorted({l["score"] for l in lectures if l["video_id"] == vid and l["mode"] == "gb" and l.get("score") is not None
                       and l["score_source"] in ("titre", "description")})
    for l in ecran:
        if _est_results_gb(l):
            if rc_texte:
                l["detail"]["rc_texte"] = sorted(set(l["detail"].get("rc_texte") or []) | set(rc_texte))
            if duree_s:
                l["detail"]["duree_video_s"] = int(duree_s)
    autres = [l for l in reste if not (l["video_id"] == vid and _est_ecran(l))]
    ecran = ocr_ecrans.fusionner_results(ocr_ecrans.regrouper_hud(ecran, config), config)
    ecran = ocr_ecrans.dedoublonner_lectures(ecran)
    # v18 : l'écran contrôlé prime sur le titre ; si la valeur du titre diffère, note `écart titre/écran : titre <valeur>`
    titres = {}
    for l in lectures:
        if l["video_id"] == vid and l["mode"] in modes and est_texte(l) and l.get("score") is not None:
            titres.setdefault(l["mode"], []).append(l["score"])
    for mode, valeurs in titres.items():
        lus = [l for l in ecran if l["mode"] == mode and l.get("score") is not None]
        if mode == "poc" or not lus or (mode == "gb" and len(lus) != 1) or any(l["score"] in valeurs for l in lus):
            continue
        for l in lus:
            if l["confidence"] == "sur" and not any(n.startswith("écart titre/écran") for n in l["notes"]):
                l["notes"].append(f"écart titre/écran : titre {valeurs[0]}")
    _lever_alerte_reset(ecran, config)
    # v35 : écran BOT en échec de contrôle = jamais un score (`detail.sans_score`), gardé avec sa note ; les lectures de texte de la vidéo restent
    texte_bot = [l for l in lectures if l["video_id"] == vid and l["mode"] == "bot" and est_texte(l)]
    chrono_bot.appliquer_echecs_ecran(ecran + texte_bot)
    chrono_bot.appliquer_phases_incompletes(ecran, config)      # v36 : phases incomplètes sans Play Time = borne basse (`detail.sans_score`), jamais un score
    valides = [l for l in ecran if l["mode"] == "bot" and l.get("score") is not None and not (l.get("detail") or {}).get("sans_score")]
    restaurer = [] if valides else [l for l in texte_bot if not any(l is x for x in autres)]
    return autres + restaurer + ecran


def _lever_alerte_reset(ecran, config):
    """v22 : un Personal Record dont `Time Left in Season` confirme la bonne semaine (v15/v17) lève l'alerte
    « publiée juste après le reset » sur toutes les lectures d'écran de la même vidéo (awb-GlVIa7Q)."""
    marges = classement.gb.tolerances((config or {}).get("gb"))
    leve = set()
    for l in ecran:
        tl = (l.get("detail") or {}).get("time_left")
        if l.get("score_source") == "record" and tl and l.get("published_at"):
            fin = classement.bornes(classement.id_semaine(classement.parse_iso(l["published_at"])))[1]
            if classement.gb.saison_precedente(tl, l["published_at"], fin, marges) is False:
                leve.add(l["video_id"])
    for l in ecran:
        if l["video_id"] in leve:
            l["notes"][:] = [n for n in l["notes"] if not n.startswith("publiée juste après le reset")]


def suffisant(lectures, vid, modes):
    """Le tri 3 suffit : BOT et HOTM = 1 lecture sûre ; POC et GB = 2 runs sûres (2 groupes / équipes). v30 : le Personal Record du GB
    ne classe plus de run (`score_source: record`) : il ne compte pas, la vidéo continue ses tris jusqu'à un écran Results."""
    sures = [l for l in lectures if l["video_id"] == vid and l["confidence"] == "sur" and l.get("score_source") != "record"]
    if not modes:
        return False
    return all(len([l for l in sures if l["mode"] == m]) >= (2 if m in ("poc", "gb") else 1) for m in modes)


MARQUEURS_ECRAN = ("results", "phase 1", "phase1", "play time", "進行時間", "rage count", "personal record", "final score", "hunter rank",
                   "your points have been registered", "warning", "합산", "증명", "클리어", "이번", "플레이어 스코어", "계승자")


def langues_ocr(meta, cfg):
    """Langues tesseract selon les modes de la vidéo (`images.ocr_langues_mode`) : BOT et GB = client anglais,
    POC et HOTM = coréen (SPEC §3.1). Mode inconnu : `images.ocr_langues`. Moins de langues = OCR plus rapide."""
    par_mode, langs = cfg.get("ocr_langues_mode", {}), []
    for m in meta.get("mode_guess", []):
        for l in par_mode.get(m, cfg["ocr_langues"]).split("+"):
            if l not in langs:
                langs.append(l)
    langue_video = (meta.get("lang") or "").lower().replace("_", "-").split("-")[0]
    for l in (cfg.get("ocr_langues_video") or {}).get(langue_video, "").split("+"):     # ex. vidéo coréenne : + kor
        if l and l not in langs and ("gb" in meta.get("mode_guess", []) or "bot" in meta.get("mode_guess", [])):   # v26 : RESULT BOT japonais
            langs.append(l)
    return "+".join(langs) or cfg["ocr_langues"]


def ressemble_ecran(texte):
    bas = ocr_ecrans.normaliser(texte).lower()
    return any(m in bas for m in MARQUEURS_ECRAN) or "phase1" in ocr_ecrans.compact(texte) or ("points" in bas and "boss rage" in bas)


def _ocr_image(outils, png, langs, cfg, st, complet=False, collecte=False):
    """Texte d'une image ; "" si elle ne ressemble pas à un écran RESULT ou si tesseract est trop lent.
    `complet` : OCR complet sans filtre rapide (tri 3 : toutes les images des 10 premières et 30 dernières secondes)."""
    try:
        if cfg.get("ocr_rapide", True) and not complet:
            petit = outils.reduire(png, cfg.get("ocr_largeur_rapide", 960))
            rapide = outils.ocr(petit, langs, cfg.get("ocr_psm_rapide", 11), cfg.get("ocr_timeout_rapide_s", 40))
            Path(petit).unlink(missing_ok=True)
            st["rapide_rejete"] = rapide      # diagnostic (--garder-ocr) : texte de l'image écartée par le filtre rapide
            if not ressemble_ecran(rapide) and not (collecte and libelles_inconnus.ressemble_score(rapide)):
                return ""                      # v24 : `collecte` laisse passer un écran de score à libellés inconnus (autre langue)
        st["candidates"] += 1
        largeur = cfg.get("ocr_largeur_complet")
        taille = outils.dimensions(png) if largeur else None
        cible = outils.reduire(png, largeur) if taille and taille[0] > largeur else png      # 1080p : OCR de l'image entière réduite
        texte = outils.ocr(cible, langs, 6, cfg.get("ocr_timeout_s", 90))
        if cible is not png:
            Path(cible).unlink(missing_ok=True)
        return texte
    except OcrTropLent:
        st["lentes"] += 1
        return ""


ZONES_TEXTE = {"boss", "g1_dmg", "g2_dmg", "time_left"}     # zones lues sans liste de caractères (texte ou lettres)


def lire_zones_results(outils, png, config, type_ecran="gb_results", texte=None, langues=None):
    """v13-v15 : écran Results (reconnu, même en animation) ou Personal Record du salon : lecture de zones ciblées,
    recadrées et agrandies, en FRACTIONS de l'image, jamais en pixels (`config.gb.zones` pour le Results : boss,
    `Player's Score`, `Hunter Rank` 1 à 6, `Final Score`, `Rage Count`, `Play Time` ; `config.gb.zones_record` pour le
    Personal Record). Une zone couvre toute la case du champ. Format différent de 16:9 (Short vertical, 4:3, bandes
    noires) : zones non appliquées (`format_ok: False`). Retourne {nom: texte lu} ; "" si illisible."""
    gb_cfg, cfg = config.get("gb") or {}, config["pc"]["images"]
    zones = dict(gb_cfg.get({"gb_record": "zones_record", "gb_combat_incertain": "zones_hud"}.get(type_ecran, "zones"), {}))
    layout = ocr_ecrans.mise_en_page_results(texte, config) if type_ecran in RESULTATS_TYPES and texte else "standard"
    if layout == "successeur":      # ligne « Successor Score » : Hunter Rank décalés, valeur du successeur lue à part
        zones.update({k: v for k, v in (gb_cfg.get("zones_successeur") or {}).items() if isinstance(v, list)})
    taille = outils.dimensions(png)
    if taille and taille[1] and abs(taille[0] / taille[1] - 16 / 9) > gb_cfg.get("format_tolerance", 0.02):
        return {"format_ok": False}
    sortie = {"format_ok": True}
    variantes = (gb_cfg.get("zones_ocr") or {}).get("variantes") or [{"echelle": 3, "seuil": None}]
    for nom, zone in zones.items():
        textes = []
        for v in variantes:          # plusieurs prétraitements (seuil / agrandissement) puis vote : un chiffre mal lu est écarté
            try:
                petit = outils.recadrer(png, zone, v.get("echelle", 3), v.get("seuil"))
                chiffres = None if nom in ZONES_TEXTE else ["-c", "tessedit_char_whitelist=0123456789,.:"]
                textes.append(outils.ocr(petit, (langues or "eng") if nom in ZONES_TEXTE else "eng", 7,
                                         cfg.get("ocr_timeout_rapide_s", 40), chiffres))
                Path(petit).unlink(missing_ok=True)
            except (OcrTropLent, RuntimeError):
                textes.append("")
        sortie[nom] = ocr_ecrans.consensus_zone(nom, textes, config)
    return sortie


def zone_armes_bot(png, config):
    """v26 : écran RESULT du BOT (16:9) -> True si les 2 cases de gauche du bandeau (`config.bot.zone_armes_sjw`) sont vides
    (SJW absent), False si une icône s'y trouve, None si l'image est illisible ou d'un autre format (jamais une preuve)."""
    try:
        from PIL import Image
        import regles_deduites
        with Image.open(png) as im:
            im = im.convert("RGB")
        if abs(im.size[0] / im.size[1] - 16 / 9) > 0.02:
            return None
        return regles_deduites.zone_vide(im, (config.get("bot") or {}).get("zone_armes_sjw"))
    except (OSError, ImportError, ZeroDivisionError):
        return None


def _bot_texte_complet(texte, config):
    """v27 : le texte de l'image entière donne déjà phases, chrono du bandeau et temps de jeu (chemin v26) : pas de lecture par zone."""
    e = ocr_ecrans.lire_bot(ocr_ecrans.normaliser(texte), config)
    return not e.get("via_zones")


def recadrer_bot(png, zone, echelle, canal, seuil, sortie):
    """v27 : zone de l'image (fractions x, y, largeur, hauteur) agrandie, en niveaux de gris selon `canal` (`cyan` = min(G, B) : blanc et
    cyan restent clairs, décors violets/rouges s'éteignent ; `max` ; `gris` ; `masque_cyan` : seuls les pixels très cyan, pour la dernière phase), noir sur blanc ; avec `seuil` : binarisée. PIL + numpy
    (installés avec opencv). Écrit `sortie` ; retourne False si PIL/numpy manquent."""
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return False
    with Image.open(png) as im:
        im = im.convert("RGB")
    w, h = im.size
    x, y, l, hh = zone
    c = im.crop((int(x * w), int(y * h), int((x + l) * w), int((y + hh) * h)))
    c = c.resize((max(1, int(c.size[0] * echelle)), max(1, int(c.size[1] * echelle))), Image.LANCZOS)
    a = np.asarray(c).astype(int)
    if canal == "masque_cyan":          # dernière phase : chiffres cyan lumineux sur décor ; pixels très cyan (G, B ≫ R) en noir, le reste blanc
        r, gr, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        out = np.where((np.minimum(gr, b) - r > 60) & (np.minimum(gr, b) > 120), 0, 255)
    else:
        g = {"cyan": np.minimum(a[:, :, 1], a[:, :, 2]), "max": a.max(axis=2)}.get(canal)
        if g is None:
            g = np.asarray(c.convert("L")).astype(int)
        out = np.where(g > seuil, 0, 255) if seuil else 255 - g
    Image.fromarray(out.astype(np.uint8)).save(sortie)
    return True


def lire_zones_bot(outils, png, config):
    """v27 (SPEC §3.1) : lecture PAR ZONE de l'écran RESULT du BOT (16:9) : une zone par ligne de phase et la zone du temps de
    jeu, chacune sous plusieurs prétraitements puis votée (`ocr_ecrans.zones_bot_lues`). Retourne {"phases": [...],
    "temps_jeu": entier | None} ; None si l'image n'est pas en 16:9 ou si PIL manque (jamais une preuve)."""
    cfg = (config.get("bot") or {}).get("zones_lecture")
    if not cfg:
        return None
    taille = outils.dimensions(png)
    if not taille or not taille[1] or abs(taille[0] / taille[1] - 16 / 9) > 0.02:
        return None
    delai = config["pc"]["images"].get("ocr_timeout_rapide_s", 40)
    chiffres = ["-c", "tessedit_char_whitelist=0123456789,.:"]
    tmp = Path(png).with_name(Path(png).stem + "_bz.png")

    def lire(zone, echelle, variantes):
        textes = []
        for v in variantes:
            try:
                if not recadrer_bot(png, zone, v.get("echelle", echelle), v.get("canal", "gris"), v.get("seuil"), tmp):
                    return None
                textes.append(outils.ocr(tmp, "eng", 7, delai, chiffres))
            except (OcrTropLent, RuntimeError):
                textes.append("")
            except OSError:
                return None            # image illisible : jamais une preuve
        return textes

    try:
        phases = [lire(z, cfg.get("echelle_phases", 3), cfg.get("variantes_phases", [])) for z in cfg.get("phases", [])]
        temps = lire(cfg["temps_jeu"], cfg.get("echelle_temps_jeu", 2.5), cfg.get("variantes_temps_jeu", [])) if cfg.get("temps_jeu") else []
    finally:
        tmp.unlink(missing_ok=True)
    if any(p is None for p in phases) or temps is None:
        return None
    return ocr_ecrans.zones_bot_lues(phases, temps, config)


RESULTATS_TYPES = ("gb_results", "gb_results_partiel")
ZONES_TYPES = RESULTATS_TYPES + ("gb_record", "gb_combat_incertain")


def _garder(ocr_debug, vid, etiquette, t, texte, png):
    """Diagnostic (--garder-ocr) : texte lu + image ; le type d'écran reconnu est ajouté au nom du fichier."""
    if not (ocr_debug and texte):
        return
    type_ecran = ocr_ecrans.detecter(texte)
    base = Path(ocr_debug) / f"{vid}_{etiquette}_{t}{'_' + type_ecran if type_ecran else ''}"
    Path(ocr_debug).mkdir(parents=True, exist_ok=True)
    base.with_suffix(".txt").write_text(texte, encoding="utf-8")
    try:
        shutil.copyfile(png, base.with_suffix(".png"))
    except OSError:
        pass


def lire_results_gb(vid, meta, outils, config, chemin, tmp, t0, duree_s, langs, journal, ocr_debug, source, cherche):
    """v11-v12 : lit les images à 1 image/s à partir de `t0`. `cherche` : `t0` est un HUD de fin de run (chrono ≤ 15 s),
    l'écran Results est cherché dans les `gb.recherche_results_s` (30) secondes ; sinon `t0` est une image déjà
    reconnue comme Results. Une fois l'écran trouvé, TOUTES ses images sont lues jusqu'à la fin de la vidéo
    (au plus `gb.results_fin_max_s` = 60 s après) : l'écran s'anime, la plus complète est gardée par
    `ocr_ecrans.fusionner_results`. Retourne (lectures, nombre d'images, première image Results | None, dernier t lu)."""
    cfg, gb_cfg = config["pc"]["images"], config.get("gb", {})
    cherche_s, cap = gb_cfg.get("recherche_results_s", 30), gb_cfg.get("results_fin_max_s", 60)
    fenetre = int(min(duree_s - t0, (cherche_s if cherche else 0) + cap))
    if fenetre <= 0:
        return [], 0, None, int(t0)
    st, n, trouve, dernier, lectures, zones_lues = {"candidates": 0, "lentes": 0}, 0, None if cherche else t0, int(t0), [], 0
    for t, png in outils.images(chemin, [(int(t0), fenetre, 1)], tmp, prefixe=f"r{int(t0)}_"):
        if (trouve is None and t > t0 + cherche_s) or (trouve is not None and t > trouve + cap):
            Path(png).unlink(missing_ok=True)
            break
        n, dernier = n + 1, t
        texte = _ocr_image(outils, png, langs, cfg, st, complet=True)
        _garder(ocr_debug, vid, "recherche", t, texte, png)
        type_ecran = ocr_ecrans.detecter(texte)
        if trouve is None and type_ecran in RESULTATS_TYPES:
            trouve = t
            journal(f"  écran Results trouvé à {t} s")
        zones = None
        if type_ecran in ZONES_TYPES and zones_lues < gb_cfg.get("zones_max_images", 12):   # les zones sont chères (plusieurs OCR par zone)
            zones = lire_zones_results(outils, png, config, type_ecran, texte, langs)
            zones_lues += 1
        ls = ocr_ecrans.lectures_depuis_texte(texte, meta, config, source, t, zones)
        _elements_hud(png, config, ls)
        _chasseurs_results(png, texte, config, meta, ls)
        lectures += [l for l in ls
                     if _est_results_gb(l) or (l["mode"] == "gb" and l["score_source"] == "record")      # + Personal Record du salon
                     or (l.get("detail") or {}).get("ecran") == "combat_sans_chrono"]                     # + HUD au chrono illisible (SPEC v19)
        Path(png).unlink(missing_ok=True)
    if trouve is None:
        journal(f"  écran Results non trouvé entre {int(t0)} et {dernier} s")
    else:
        pleines = [l for l in lectures if l["score"] is not None and l["score_source"] != "record"]
        journal(f"  écran Results lu de {int(t0)} à {dernier} s : {n} image(s), {len(pleines)} lecture(s) avec Rage Count")
    return lectures, n, trouve, dernier


def traiter_images(vid, meta, outils, config, lectures, pc, jour, journal=lambda m: None, ocr_debug=None,
                   horloge=time.monotonic, apres=None):
    """Tri 3, puis tri 4 si le tri 3 ne suffit pas. Retourne (lectures, avertissement | None, reporte).
    Par image : doublon exact ignoré ; tri 3 = OCR complet de toutes les images ; tri 4 = OCR rapide (image réduite,
    `psm` clairsemé) puis complet seulement si le texte ressemble à un écran RESULT ; image trop lente = ignorée.
    v11 : HUD GB avec chrono ≤ 15 s -> recherche de l'écran `Results` dans les 30 s suivantes (1 image/s).
    Budget de temps par vidéo (`budget_video_min`) : dépassé, la vidéo reste « partielle » et est reprise au passage
    suivant (`essais_max` fois, puis considérée faite).
    v33 : `apres(chemin, tmp)` est appelée une fois les tris faits, sur la vidéo DÉJÀ téléchargée (relevé de rotation, SPEC_ROTATION §1)."""
    cfg = config["pc"]["images"]
    minutes = duree_minutes(meta.get("duration"))
    if minutes is None or minutes > cfg["max_minutes"]:
        return lectures, f"{vid} : durée {meta.get('duration')} hors limite ({cfg['max_minutes']} min), images non traitées", False
    langs = langues_ocr(meta, cfg)
    fin = horloge() + cfg.get("budget_video_min", 15) * 60
    seuil_fin = config.get("gb", {}).get("chrono_fin_s", 15)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            if ocr_debug:    # diagnostic : résolutions proposées par YouTube (`yt-dlp -F`)
                try:
                    pc["hauteurs"] = outils.hauteurs(vid)
                    journal(f"  formats disponibles : {', '.join(str(h) + 'p' for h in pc['hauteurs']) or 'inconnus'}")
                except OutilAbsent:
                    raise
                except Exception as e:
                    journal(f"  formats non lus : {e}")
            journal("  téléchargement…")
            chemin = outils.telecharger(vid, tmp)
            for tri in (3, 4):
                if pc.get(f"tri{tri}") == "fait":
                    continue
                source = "debut-fin" if tri == 3 else "video-complete"
                nouvelles, st, complet, vus, detectes = [], {"images": 0, "doublons": 0, "candidates": 0, "lentes": 0}, True, {}, []
                t0 = horloge()
                hauteur = cfg.get("tri4_hauteur", 720) if tri == 4 else None      # v15 : tri 3 et Results en 1080p, tri 4 en 720p
                for t, png in outils.images(chemin, segments_tri(tri, minutes * 60, cfg), tmp, hauteur=hauteur):
                    if horloge() > fin:
                        complet = False
                        break
                    st["images"] += 1
                    if "image_taille" not in pc:
                        taille = outils.dimensions(png)
                        if taille:
                            pc["image_taille"] = list(taille)
                            journal(f"  image lue : {taille[0]}x{taille[1]}")
                    h = outils.empreinte(png)
                    if h in vus:
                        st["doublons"] += 1
                        texte, zones = vus[h]
                    else:
                        inconnus = pc.setdefault("libelles_inconnus", [])
                        texte = _ocr_image(outils, png, langs, cfg, st, complet=(tri == 3 and cfg.get("tri3_ocr_complet", True)),
                                           collecte=len(inconnus) < libelles_inconnus.MAX_PAR_VIDEO)
                        type_img = ocr_ecrans.detecter(texte)
                        if libelles_inconnus.a_garder(texte, type_img, inconnus) and libelles_inconnus.espace(t, inconnus):
                            libelles_inconnus.garder(RACINE, vid, t, texte, png)      # v24 : libellé d'une langue inconnue
                            inconnus.append(t)
                            journal(f"  écran de score sans libellé reconnu gardé à t={t} s (docs/essais/ocr/libelles_inconnus)")
                        zones = lire_zones_results(outils, png, config, type_img, texte, langs) if type_img in ZONES_TYPES else None
                        if type_img == "bot" or (type_img is None and ocr_ecrans.candidat_bot(texte, config)):
                            zb = None
                            if type_img is None or not _bot_texte_complet(texte, config):      # v27 : texte entier insuffisant -> zones
                                zb = lire_zones_bot(outils, png, config)
                            if type_img is None and not ocr_ecrans.zones_bot_valides(zb):
                                zb = None
                            elif type_img is None:
                                type_img = "bot"
                            if type_img == "bot":
                                zones = {"armes_sjw_vides": zone_armes_bot(png, config), "bot": zb}
                        vus[h] = (texte, zones)
                        _garder(ocr_debug, vid, f"tri{tri}", t, texte or st.pop("rapide_rejete", ""), png)
                    if ocr_ecrans.detecter(texte) in RESULTATS_TYPES:
                        detectes.append(t)
                    nl = ocr_ecrans.lectures_depuis_texte(texte, meta, config, source, t, zones)
                    _elements_hud(png, config, nl)
                    nouvelles += nl
                    Path(png).unlink(missing_ok=True)
                lectures = fusionner_ecrans(lectures, vid, nouvelles, config, duree_s=minutes * 60)
                # v21 : HUD de fin de run (chrono lu ≤ 5 s) -> les 2 images suivantes (1 img/s) : le HUD y a souvent un chrono illisible
                # mais des Points plus récents (SPEC v19 : chrono HUD déduit) ; les tri 3 sautent une image sur deux
                suivis = pc.setdefault("hud_suite", [])
                for h in [x for x in lectures if x["video_id"] == vid and (x.get("detail") or {}).get("ecran") == "combat"
                          and x["detail"]["chrono_hud"] <= config.get("gb", {}).get("hud_chrono_points_s", 5) and x["t"] is not None]:
                    if int(h["t"]) in suivis or horloge() > fin:
                        continue
                    suivis.append(int(h["t"]))
                    suite = []
                    for t_s, png_s in outils.images(chemin, [(int(h["t"]) + 1, 2, 1)], tmp, prefixe=f"h{int(h['t'])}_"):
                        if t_s > minutes * 60:
                            Path(png_s).unlink(missing_ok=True)
                            continue
                        texte_s = _ocr_image(outils, png_s, langs, cfg, st, complet=True)
                        _garder(ocr_debug, vid, "suite_hud", t_s, texte_s, png_s)
                        ls = ocr_ecrans.lectures_depuis_texte(texte_s, meta, config, source, t_s)
                        _elements_hud(png_s, config, ls)
                        suite += [l for l in ls if (l.get("detail") or {}).get("ecran") in ("combat", "combat_sans_chrono")]
                        Path(png_s).unlink(missing_ok=True)
                    st["images"] += 2
                    lectures = fusionner_ecrans(lectures, vid, suite, config, duree_s=minutes * 60)
                # v12 : écran Results lu jusqu'à la fin de la vidéo ; chrono HUD ≤ 15 s -> on cherche l'écran qui suit
                lus = pc.setdefault("results_lus", [])            # [[début, fin]] déjà lus (aucune relecture au tri 4)
                couvert = lambda t: any(a <= t <= b for a, b in lus)
                res_t = detectes + [l["t"] for l in lectures if l["video_id"] == vid and _est_results_gb(l) and l["t"] is not None]
                departs = [(t, False) for t in sorted(set(detectes))]
                departs += [(h["t"], True) for h in lectures
                            if h["video_id"] == vid and (h.get("detail") or {}).get("ecran") == "combat"
                            and h["detail"]["chrono_hud"] <= seuil_fin and h["t"] is not None
                            and not any(h["t"] <= r <= h["t"] + 90 for r in res_t)]
                for t_dep, cherche in sorted(departs):
                    if couvert(t_dep):
                        continue
                    if horloge() > fin:
                        complet = False
                        break
                    trouvees, n_img, _, dernier = lire_results_gb(vid, meta, outils, config, chemin, tmp, t_dep, minutes * 60,
                                                                  langs, journal, ocr_debug, source, cherche)
                    lus.append([t_dep, dernier])
                    st["images"] += n_img
                    lectures = fusionner_ecrans(lectures, vid, trouvees, config, duree_s=minutes * 60)
                    nouvelles += trouvees
                # v28 : Results GB non `sûr` sans aucun HUD de fin de run dans les `gb.hud_amont_s` s qui précèdent -> on lit ces images
                # une fois (1 img/s) : un HUD à chrono ≤ 5 s ou à Points récents confirme le Final Score (SPEC v19/v21)
                amont, amont_s = pc.setdefault("hud_amont", []), config.get("gb", {}).get("hud_amont_s", 30)
                for r in [x for x in lectures if x["video_id"] == vid and x["mode"] == "gb" and x.get("score") is not None
                          and x["score_source"] in SOURCES_RESULTATS and x.get("confidence") != "sur" and x.get("t") is not None]:
                    t_r = int(r["t"])
                    a_hud = any(h["video_id"] == vid and (h.get("detail") or {}).get("ecran") in ("combat", "combat_sans_chrono")
                                and 0 <= t_r - h["t"] <= amont_s and (h["detail"].get("hud_points") is not None
                                                                      or (h["detail"].get("chrono_hud") or 99) <= 5)
                                for h in lectures if h["t"] is not None)
                    if a_hud or t_r in amont or horloge() > fin:
                        continue
                    amont.append(t_r)
                    debut_a = max(0, t_r - amont_s)
                    suite = []
                    for t_s, png_s in outils.images(chemin, [(debut_a, t_r - debut_a, 1)], tmp, prefixe=f"a{t_r}_"):
                        texte_s = _ocr_image(outils, png_s, langs, cfg, st, complet=True)
                        _garder(ocr_debug, vid, "hud_amont", t_s, texte_s, png_s)
                        ls = ocr_ecrans.lectures_depuis_texte(texte_s, meta, config, source, t_s)
                        _elements_hud(png_s, config, ls)
                        suite += [l for l in ls if (l.get("detail") or {}).get("ecran") in ("combat", "combat_sans_chrono")]
                        Path(png_s).unlink(missing_ok=True)
                    st["images"] += t_r - debut_a
                    journal(f"  HUD de fin cherché de {debut_a} à {t_r} s : {len(suite)} lecture(s)")
                    lectures = fusionner_ecrans(lectures, vid, suite, config, duree_s=minutes * 60)
                n_ecrans = len(nouvelles)
                journal(f"  tri {tri} : {st['images']} image(s), {st['candidates']} lue(s) à l'OCR complet, "
                        f"{n_ecrans} écran(s) lu(s), {st['lentes']} trop lente(s), {st['doublons']} doublon(s), "
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
            if apres is not None:
                apres(chemin, tmp)
        except OutilAbsent:
            raise
        except Exception as e:
            if est_429(e):
                return lectures, f"{vid} : 429 / anti-bot YouTube (téléchargement), reportée au prochain passage", True
            return lectures, f"{vid} : images : {e}", False
    # v15 : GB sans aucun écran reconnu après le tri 4 : libellés de la langue inconnus, la vidéo reste `en_cours`
    if "gb" in meta.get("mode_guess", []) and pc.get("tri4") in ("fait", "inutile") and not any(
            l["video_id"] == vid and l["mode"] == "gb" and (l.get("score") is not None or (l.get("detail") or {}).get("ecran") == "combat")
            and not est_texte(l) for l in lectures):
        langue = meta.get("lang") or "?"
        pc["libelles_inconnus"] = langue
        return lectures, f"{vid} : libellés {langue} inconnus (aucun écran GB reconnu)", False
    pc.pop("libelles_inconnus", None)
    return lectures, None, False


def traiter_miniature(vid, meta, outils, config, lectures, pc, journal=lambda m: None, telecharger=None):
    """v34, tri 2 : texte OCR de la miniature (`miniature.py`) lu avec les règles du tri 1 -> lecture provisoire (`score_source: miniature`,
    `exact: false`, `a_verifier`) ; une miniature qui ressemble à un écran RESULT est en plus lue comme un écran. Une fois par vidéo
    (`pc.tri2` = `fait` | `absent` ; une erreur de l'OCR ne marque rien). Retourne les lectures."""
    cfg = miniature.reglages(config)
    if pc.get("tri2") in ("fait", "absent") or not cfg["actif"]:
        return lectures
    with tempfile.TemporaryDirectory() as tmp:
        try:
            nouvelles, plein, etat = miniature.lire(vid, meta, outils, config, tmp, langues_ocr(meta, config["pc"]["images"]), telecharger, journal)
        except OutilAbsent:
            raise
    if etat == "erreur":
        return lectures
    pc["tri2"] = etat
    ecrans = ocr_ecrans.lectures_depuis_texte(plein, meta, config, "miniature") if plein and ocr_ecrans.detecter(plein) in RESULTATS_TYPES else []
    lectures = [l for l in lectures if not (l["video_id"] == vid and (l.get("detail") or {}).get("texte_miniature"))]
    avec_ecran = {l["mode"] for l in lectures if l["video_id"] == vid and _est_ecran(l) and l.get("score") is not None}
    avec_texte = {l["mode"] for l in lectures if l["video_id"] == vid and l.get("score") is not None and est_texte(l)}
    gardees = []
    for n in nouvelles:
        seule = n["mode"] not in avec_texte       # la miniature est la seule source de score : accord plus strict (`accord_seul`, 3)
        if n["mode"] not in avec_ecran and (not seule or n["detail"].get("votes_miniature", 0) >= cfg["accord_seul"]):
            lectures.append(n)
            gardees.append(n)
    if any(e.get("score") is not None for e in ecrans):
        lectures = fusionner_ecrans(lectures, vid, [e for e in ecrans if e.get("score") is not None], config)
    if gardees:
        journal("  miniature : " + ", ".join(f"{n['mode']} {n['score']}" for n in gardees))
    return lectures


def passage_rotation(vid, week, outils, chemin, tmp, meta, d, journal):
    """Relevé de la rotation d'une vidéo déjà téléchargée (SPEC_ROTATION) ; ne lève jamais : `erreur` + trace dans le journal."""
    try:
        cfg = rotation.charger_config()
        ctx = rotation.contexte(week, vid, RACINE, cfg)
        if ctx is None:
            return "absent"
        db = builds_db()
        cartes = None
        try:
            import portraits
            cartes = portraits.charger_cartes(RACINE / "data" / "icons") or None
        except Exception:
            cartes = None
        etat = rotation.passage_video(outils, chemin, ctx, cfg, db, tmp, journal, ocr=rotation.ocr_recharge(outils, tmp), ocr_t=rotation.ocr_chrono(outils, tmp), cartes=cartes, racine=RACINE,
                                      duree_s=duree_minutes(meta.get("duration")) and duree_minutes(meta.get("duration")) * 60)
        journal(f"  rotation {vid} : {etat}")
        return etat
    except OutilAbsent:
        raise
    except Exception as e:
        journal(f"  rotation {vid} : erreur {e}")
        return "erreur"


def builds_db():
    import builds as B
    return B.charger_db(RACINE)


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


# --- état du passage, relance anti-bot (discussion 1, critère de gel n° 3) ---------------------------------------------

FICHIER_RELANCE = RACINE / "logs" / "relance.json"
NOM_TACHE_RELANCE = "ShadowLedger PC relance"


def planifier_windows(quand, commande_bat, nom=NOM_TACHE_RELANCE):
    """Tâche ponctuelle du Planificateur de tâches (PowerShell, indépendant de la langue de Windows) : `quand` = datetime
    naïf (heure de Paris = heure du PC) ; la tâche lance `lancer_pc.bat daily relance`. Retourne None ou le message d'erreur."""
    if sys.platform != "win32":
        return "planification possible seulement sous Windows"
    bat = str(commande_bat).replace("'", "''")
    ps = (f"$a = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c \"{bat}\" daily relance'; "
          f"$t = New-ScheduledTaskTrigger -Once -At ([datetime]'{quand:%Y-%m-%dT%H:%M:%S}'); "
          "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
          "-MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 6); "
          f"Register-ScheduledTask -TaskName '{nom}' -Force -Action $a -Trigger $t -Settings $s | Out-Null")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:]


def programmer_relance(instant, jour, planifier=None, fichier=None, delai_h=2):
    """Anti-bot : une seule relance par soir (`jour` = date de Paris du passage), 2 h plus tard. Retourne un texte pour le
    rapport : heure de la relance, ou la raison pour laquelle il n'y en a pas."""
    fichier = Path(fichier or FICHIER_RELANCE)
    try:
        deja = json.loads(fichier.read_text(encoding="utf-8")).get("jour") if fichier.exists() else None
    except (OSError, ValueError):
        deja = None
    if deja == jour:
        return "aucune (une relance a déjà été programmée ce soir) : prochain passage normal"
    quand = (instant.astimezone(PARIS) + timedelta(hours=delai_h)).replace(tzinfo=None, second=0, microsecond=0)
    err = (planifier or planifier_windows)(quand, RACINE / "pipeline" / "pc" / "lancer_pc.bat")
    if err:
        return f"non programmée ({err})"
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(json.dumps({"jour": jour, "a": quand.isoformat()}), encoding="utf-8")
    return f"{quand:%d/%m/%Y %H:%M} (une seule fois par soir)"


def semaine_du_passage(passage, instant):
    courante = id_semaine(instant)
    return courante if passage == "daily" else semaine_precedente(courante)


def lignes_exports_deplaces(git):
    """v33 : note du bloc quand des fichiers d'`exports/` du PC ont été mis de côté pour que le pull réussisse."""
    f = tuple(getattr(git, "exports_deplaces", ()) or ())
    return [f"- Exports du PC déplacés dans exports/_local/ pour le pull (git) : {len(f)} fichier(s) : " + ", ".join(f[:5])] if f else []


def signaler_echec(passage, instant, cause, d=None, git=None, conflit_resolu=False):
    """Un passage qui n'aboutit pas (anti-bot, conflit git, JSON abîmé, crash, verrou refusé, passage interrompu) écrit quand même
    son bloc « Passage complet : non » + la cause dans `_rapport_pc.md` (jamais effacé) ; poussé si possible (v26, critère de gel
    n° 3). Retourne le bloc. Ne lève jamais : un échec de l'écriture ou du push ne masque pas l'erreur d'origine."""
    d = d or Donnees()
    week = semaine_du_passage(passage, instant)
    lignes = entete_etat(False, 0, 0, 0, [cause[:300]])
    if conflit_resolu or (git is not None and getattr(git, "conflit_resolu", False)):
        lignes.append("- Conflit git résolu automatiquement")
    lignes += lignes_exports_deplaces(git)
    bloc = rapport_pc.ecrire_bloc(d, week, f"pc-{passage}", instant, lignes)
    try:          # `_rapport.md` : même en-tête qu'avant (le passage GitHub suivant le remplace par le dernier bloc du PC)
        chemin = f"runs/{week}/_rapport.md"
        ancien = (d.data / chemin).read_text(encoding="utf-8") if (d.data / chemin).exists() else ""
        reste = ancien.split("\n", 2)[2] if ancien.count("\n") >= 2 and ancien.startswith("# ") else ""
        titre = f"# Rapport — semaine {week} — passage pc-{passage} — {instant.astimezone(PARIS).strftime('%Y-%m-%d %H:%M')} (Paris)"
        d.ecrire(chemin, "\n".join([titre, ""] + lignes + ["", reste]).rstrip() + "\n")
    except OSError:
        pass
    if git:
        try:
            git.pousser(f"données: passage PC {passage} interrompu")
        except Exception:
            pass          # le bloc reste dans data/ : le passage suivant le commite (`Git.tirer`)
    return bloc


def signaler_crash(passage, instant, erreur, d=None, git=None):
    """Plantage du passage (compatibilité) : bloc « Passage complet : non » + l'erreur."""
    return signaler_echec(passage, instant, f"crash : {type(erreur).__name__} : {str(erreur)[:200]}", d, git)


def bloquante(avert):
    """Avertissement d'une vidéo qui relève d'une erreur bloquante (exception pendant les images, ffmpeg) et non d'un simple report."""
    t = (avert or "").lower()
    return " : images : " in t or "ffmpeg" in t


def resume_gb(d, semaine, jour, maximum=5):
    """v33 : résumé lisible en tête du bloc : une ligne par vidéo GB traitée ce jour par le PC (Results lu ? RC, statut, groupe, motif
    principal si `a_verifier`). Au plus `maximum` lignes. Lit `processed.json` (`pc.date`, `pc.results_lus`) et `gb.json` (déjà recalculé)."""
    try:
        lignes_gb = d.lire(f"runs/{semaine}/gb.json", [])
    except Exception:
        lignes_gb = []
    traitees = [(v, p) for v, p in d.processed().items()
                if p.get("week") == semaine and "gb" in (p.get("modes") or []) and (p.get("pc") or {}).get("date") == jour]
    sortie = []
    for vid, p in traitees:
        lus = (p.get("pc") or {}).get("results_lus") or []
        ligne = next((l for l in lignes_gb if vid in (l.get("video_ids") or [l.get("video_id")])), None)
        results = f"Results lu ({lus[0][0]}-{lus[0][1]} s)" if lus else "aucun Results lu"
        if ligne is None:
            sortie.append(f"- Résumé GB : {vid} · {results} · pas classée")
            continue
        det = (ligne.get("runs_detail") or [{}])[0]
        motif = next((n for n in (ligne.get("notes") or "").split("; ") if n and not n.startswith(("lecture fusionnée", "boss non", "écart OCR"))), "")
        sortie.append(f"- Résumé GB : {vid} · {ligne.get('player')} · {results} · {ligne['score']['total']} RC {'sûr' if ligne['confidence'] == 'sur' else 'à vérifier'}"
                      + (f" · groupe {det['team']}" if det.get("team") else "") + (f" · {det['element']}" if det.get("element") else "")
                      + ("" if ligne["confidence"] == "sur" or not motif else f" · {motif}"))
    return sortie[:maximum] + ([f"- Résumé GB : … et {len(sortie) - maximum} autre(s) vidéo(s)"] if len(sortie) > maximum else [])


def entete_etat(complet, traitees, restantes, a_traiter, bloquantes, relance=None, duree_min=None, top10=None, gel3=None):
    """Lignes placées en tête du rapport poussé (SPEC §6, critère de gel n° 3). v29 : `top10` = nombre de vidéos candidates au
    top 10 encore en attente (ligne « Top 10 couvert », en tête) ; `gel3` = texte du critère de gel n° 3 (passages couverts)."""
    l = [ordre_pc.ligne_top10(top10)] if top10 is not None else []
    l += [f"- **Passage complet : {'oui' if complet else 'non'}**"
         + ("" if complet else " (" + (" ; ".join(b.split(" : ")[0] if b.startswith("anti-bot") else b for b in bloquantes[:1]) if bloquantes else "vidéos restantes à traiter") + ")"),
         f"- Vidéos traitées ce passage : {traitees} · en_cours restantes : {restantes} (dont {a_traiter} à traiter par le PC)",
         "- Erreurs bloquantes : " + (" ; ".join(bloquantes) if bloquantes else "aucune")]
    if duree_min is not None:       # durée réelle du passage (horloge monotone, hors push final) ; budget : `pc.budget_minutes`
        l.append(f"- Durée du passage : {int(duree_min)} min")
    if relance:
        l.append(f"- Relance automatique : {relance}")
    if gel3:
        l.append(f"- Critère de gel n° 3 : {gel3}")
    return l


def passage_builds(semaine, outils, git=None, journal=None, force=False, pptx=True):
    """Étape 2 sur le PC : images de composition des vidéos du top 10 (`composition.fournisseur_pc`), calcul des builds,
    PowerPoint, puis commit/push de `data/builds`. Retourne la liste des builds."""
    import builds as B
    import composition
    journal = journal or (lambda m: None)
    if git:
        git.tirer()
    cfg2 = B.charger_config()
    fournisseur = composition.fournisseur_pc(outils, cfg2, journal)
    journal(f"Builds — semaine {semaine}")
    liste = B.calculer(semaine, RACINE, cfg2, fournisseur=fournisseur, force=force)
    if pptx:
        try:
            import export_pptx
            fichiers = export_pptx.exporter(semaine, RACINE)
            journal(f"{len(fichiers)} fichier(s) PowerPoint")
        except SystemExit as e:          # python-pptx absent
            journal(f"PowerPoint ignoré : {e}")
    if git:
        git.pousser(f"données: builds {semaine}")
    return liste


def lancer(passage, instant, d=None, config=None, outils=None, git=None, whisper=False, maximum=None, images=None,
           journal=None, dormir=None, horloge=time.monotonic, ocr_debug=None, seulement=None, refaire=False,
           relance=False, planifier=None, fichier_relance=None):
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

    traitees, images_traitees, antibot, bloquantes = 0, 0, False, []
    relectures_posees = []
    if meta.get("frozen"):
        alertes.append(f"semaine {week} déjà gelée : rien à traiter")
    else:
        processed, videos, lectures = d.processed(), d.videos(week), d.lectures(week)
        if not seulement:           # v34 : relecture automatique du top 10 provisoire (règles plus anciennes, aucun Results lu)
            relectures_posees = relectures.poser(d, week, config, processed, jour)
            if relectures_posees:
                journal("Relectures posées : " + ", ".join(f"{v} ({m})" for v, m in relectures_posees))
                d.ecrire("processed.json", processed)
        if refaire:  # diagnostic : la vidéo choisie est retraitée comme si rien n'avait été fait
            for v in (seulement or ()):
                if v in processed:
                    processed[v].pop("pc", None)
                    processed[v].update(status="en_cours", pc_needed=True)
                    lectures = [l for l in lectures if not (l["video_id"] == v and _est_ecran(l))]

        def sauver():
            d.ecrire(f"runs/{week}/_lectures.json", lectures)
            d.ecrire("processed.json", processed)

        def titre(vid):
            return (videos.get(vid, {}).get("title") or "")[:50]

        a_faire = [v for v, p in processed.items() if p.get("week") == week and p["status"] == "en_cours"
                   and (not seulement or v in seulement) and p.get("pc_needed") and (p.get("pc") or {}).get("sous_titres") not in ("fait", "absent")]
        a_faire = ordre_pc.ordonner(d, week, a_faire)[0]          # v29 : candidates au top 10 d'abord
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
                    if bloquante(avert):
                        bloquantes.append(avert)
                if etat == "reporte":  # 429 : on s'arrête, YouTube limite le débit de cette adresse
                    antibot = True
                    alertes.append("429 / anti-bot YouTube : sous-titres arrêtés pour ce passage, les vidéos restantes sont reportées (réessayer dans 1 à 2 h)")
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
            bloquantes.append(f"outil absent : {e}")
        cfg_img = pc_cfg["images"]
        if cfg_img["actif"] if images is None else images:
            try:        # v33 : rotations (SPEC_ROTATION) : top 3 du BOT, vidéo déjà téléchargée par les tris 3-4 (ou seulement pour la rotation)
                rotation_cfg = rotation.charger_config()
                ordre_rotation = rotation.a_traiter(week, processed, RACINE, rotation_cfg)      # BOT d'abord, puis POC, GB, HOTM
                a_rotation = set(ordre_rotation)
            except Exception as e:
                ordre_rotation, a_rotation, rotation_cfg = [], set(), {"version": 1}
                alertes.append(f"rotation : sélection impossible ({e})")
            a_images = [v for v, p in processed.items() if p.get("week") == week and v in videos and (not seulement or v in seulement)
                        and ((p["status"] == "en_cours" and p.get("pc_needed") and (p.get("pc") or {}).get("tri4") not in ("fait", "inutile"))
                             or v in a_rotation)]
            a_images = ordre_pc.ordonner(d, week, a_images)[0]       # v29 : idem pour les images (anti-bot : on s'arrête quand on peut)
            places = [i for i, v in enumerate(a_images) if v in a_rotation]      # v36 : entre elles, les vidéos de rotation passent BOT, POC, GB, HOTM
            for i, v in zip(places, sorted((a_images[i] for i in places), key=ordre_rotation.index)):
                a_images[i] = v
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
                    apres = None
                    if vid in a_rotation:
                        def apres(chemin, tmp, vid=vid, etat=etat):
                            etat["rotation"] = passage_rotation(vid, week, outils, chemin, tmp, videos[vid], d, journal)
                            etat["rotation_version"] = rotation_cfg.get("version", 1)
                    try:
                        lectures = traiter_miniature(vid, videos[vid], outils, config, lectures, etat, journal)       # v34 : tri 2
                    except OutilAbsent:
                        raise
                    except Exception as e:
                        journal(f"  miniature : {e}")
                    lectures, avert, reporte = traiter_images(vid, videos[vid], outils, config, lectures, etat, jour,
                                                              journal, ocr_debug, horloge, apres)
                    journal(f"  → {int(horloge() - t0)} s" + (f" — {avert}" if avert else ""))
                    if avert:
                        alertes.append(avert)
                        if bloquante(avert):
                            bloquantes.append(avert)
                    if not reporte and not (avert and bloquante(avert)):
                        images_traitees += 1
                    if etat:
                        processed[vid]["pc"] = etat
                        processed[vid]["updated_at"] = jour
                    if etat.get("tri3") == "fait":
                        processed[vid]["last_tri"] = max(processed[vid].get("last_tri", 0), 3)
                    if etat.get("tri4") in ("fait", "inutile"):
                        processed[vid]["last_tri"] = 4 if etat["tri4"] == "fait" else processed[vid]["last_tri"]
                        processed[vid]["pc_needed"] = False
                        if any(l["video_id"] == vid and l.get("score") is not None for l in lectures) and not etat.get("libelles_inconnus"):
                            processed[vid]["status"] = "termine"
                    sauver()
                    if reporte:
                        antibot = True
                        alertes.append("429 / anti-bot YouTube : images arrêtées pour ce passage, les vidéos restantes sont reportées (réessayer dans 1 à 2 h)")
                        break
                    if n < len(lot):
                        dormir(pause)
            except OutilAbsent as e:
                alertes.append(str(e))
                bloquantes.append(f"outil absent : {e}")
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
    proc = [p for p in d.processed().values() if p.get("week") == week]
    restantes = sum(1 for p in proc if p["status"] == "en_cours")
    a_traiter = sum(1 for p in proc if p["status"] == "en_cours" and p.get("pc_needed") and (p.get("pc") or {}).get("tri4") not in ("fait", "inutile"))
    texte_relance = None
    if antibot:
        bloquantes.insert(0, "anti-bot YouTube (passage incomplet : anti-bot)")
        if relance:
            texte_relance = "aucune (c'était déjà la relance) : prochain passage normal"
        else:
            texte_relance = programmer_relance(instant, jour, planifier, fichier_relance)
        alertes.append(f"passage incomplet : anti-bot ; relance : {texte_relance}")
    complet = not bloquantes and a_traiter == 0
    top10_n = ordre_pc.candidates_restantes(d, week, d.processed())      # v29 : après le classement du passage
    etat = dict(complet=complet, traitees=traitees + images_traitees, restantes=restantes, a_traiter=a_traiter, bloquantes=list(bloquantes),
                relance=texte_relance)

    def rapport():
        gel3 = rapport_pc.critere_gel3(d, week, f"pc-{passage}", instant, top10_n, etat["bloquantes"], relance=bool(relance))
        lignes = entete_etat(etat["complet"], etat["traitees"], restantes, a_traiter, etat["bloquantes"], texte_relance,
                             (horloge() - debut_passage) / 60, top10_n, gel3)
        if relance:
            lignes.append("- Type : relance automatique (ne compte pas pour le critère de gel n° 3)")
        if git is not None and getattr(git, "conflit_resolu", False):
            lignes.append("- Conflit git résolu automatiquement")
        lignes += lignes_exports_deplaces(git)
        lignes += relectures.lignes_rapport(relectures_posees)
        lignes += resume_gb(d, week, jour)
        rapport_pc.ecrire_bloc(d, week, f"pc-{passage}", instant, lignes)      # v26 : bloc daté, jamais effacé, propre au PC
        ecrire_rapport(d, week, f"pc-{passage}", instant, None, res, alertes, lignes)
    rapport()
    if git:
        conflit_avant = git.conflit_resolu
        try:
            git.pousser(f"données: passage PC {passage} {jour}")
            if git.conflit_resolu and not conflit_avant:       # conflit résolu au push : noté dans le bloc, poussé à part
                rapport()
                git.pousser(f"données: rapport PC {passage} {jour} (conflit git résolu)")
        except GitErreur as e:
            etat["complet"] = False
            etat["bloquantes"].append(f"git : {e}")
            alertes.append(f"git : {e}")
            rapport()
            raise
    return {"week": week, "traitees": traitees, "alertes": alertes, **etat}


def publier_essai(outils, source, destination, git=None, maximum=8, resume=None, nom_resume="_resume.json"):
    """Diagnostic : copie dans `destination` (docs/essais/ocr, versionné) les textes OCR de `source` (logs/ocr) et les
    images de `maximum` fichiers PAR VIDÉO, en JPEG réduit ; puis commit + push si `git`. Passent d'abord les images
    de recherche de l'écran Results, puis les écrans reconnus (nom de fichier terminé par le type : `_gb_results`,
    `_gb_combat`…, 2 au plus pour le HUD, 4 pour les autres), puis les textes les plus longs. Retourne les noms écrits."""
    source, destination = Path(source), Path(destination)
    textes = sorted(source.glob("*.txt"), key=lambda f: -f.stat().st_size)
    types = {f: (re.search(r"_(gb_\w+|bot|hotm|poc)$", f.stem) or [None, None])[1] for f in textes}
    par_video = {}
    for f in textes:
        m = re.match(r"(.+?)_(?:tri[34]|recherche)_", f.stem)
        par_video.setdefault(m.group(1) if m else f.stem, []).append(f)
    destination.mkdir(parents=True, exist_ok=True)
    ecrits = []
    if resume is not None:  # lectures et état des vidéos après le passage (diagnostic)
        (destination / nom_resume).write_text(json.dumps({**resume, "fichiers_logs_ocr": sorted(f.name for f in source.glob("*.txt")),
                                                          "textes_recherche": {f.name: f.read_text(encoding="utf-8", errors="replace")
                                                                               for f in sorted(source.glob("*_recherche_*.txt"))}},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
        ecrits.append(nom_resume)
    t_de = lambda f: int((re.search(r"_(?:tri[34]|recherche)_(\d+)", f.stem) or [0, 0])[1])
    for fichiers in par_video.values():
        reconnus = sorted((f for f in fichiers if types[f] in ("gb_results", "gb_results_partiel", "gb_record")), key=t_de)
        if len(reconnus) > 4:                                    # écrans Results / record : répartis du début à la fin
            reconnus = [reconnus[round(k * (len(reconnus) - 1) / 3)] for k in range(4)]
        combats = sorted((f for f in fichiers if types[f] == "gb_combat"), key=t_de)
        choisis = list(dict.fromkeys(reconnus + combats[:1] + combats[-1:]))
        if combats:       # images juste après le dernier HUD de la vidéo : l'écran Results, dans une langue peut-être inconnue
            apres = sorted((f for f in fichiers if types[f] is None and t_de(f) > t_de(combats[-1])), key=t_de)
            if apres:
                choisis += list(dict.fromkeys(apres[round(k * (len(apres) - 1) / 3)] for k in range(4)))
        choisis += sorted((f for f in fichiers if "_tri3_" in f.stem and f not in choisis), key=t_de)[-4:]   # fin de vidéo (langue inconnue)
        tri4 = sorted((f for f in fichiers if "_tri4_" in f.stem and f not in choisis), key=t_de)
        if tri4:                                                 # milieu de vidéo (langue inconnue) : 3 images réparties
            choisis += list(dict.fromkeys(tri4[round(k * (len(tri4) - 1) / 2)] for k in range(3)))
        choisis += [f for f in fichiers if "_recherche_" in f.stem and f not in choisis][:2]
        choisis += [f for f in fichiers if f not in choisis]
        for f in choisis[:maximum]:
            png = f.with_suffix(".png")
            if png.exists():
                jpg = destination / (f.stem + ".jpg")
                outils._lancer([outils.cfg["images"]["ffmpeg"], "-nostdin", "-v", "error", "-y", "-i", str(png), "-q:v", "4", str(jpg)], 60)
                ecrits.append(jpg.name)
            shutil.copyfile(f, destination / f.name)
            ecrits.append(f.name)
    if git and ecrits:
        git.pousser_chemin("essai: images et textes OCR du PC", str(destination))
    return ecrits


def bilan_essai(d, week, ids, config):
    """Diagnostic des vidéos de test GB : par vidéo, résolution (formats proposés, image lue), écrans Results lus (RC,
    Final Score, contrôle, notes), HUD de fin de run et écart `Points` HUD / `Final Score` en %, puis les lignes
    `gb.json` des joueurs concernés (somme des runs)."""
    lectures, processed, videos = d.lectures(week), d.processed(), d.videos(week)
    fenetre = (config.get("gb") or {}).get("hud_results_fenetre_s", 60)
    bilan = {}
    for v in sorted(ids):
        huds = [l for l in lectures if l["video_id"] == v and (l.get("detail") or {}).get("ecran") == "combat"]
        pc_ = (processed.get(v) or {}).get("pc") or {}
        resultats = []
        for l in sorted((x for x in lectures if x["video_id"] == v and x["mode"] == "gb" and x.get("score") is not None
                         and x["score_source"] in ("debut-fin", "video-complete")), key=lambda x: x["t"] or 0):
            hud = max((h for h in huds if h["t"] is not None and l["t"] is not None and h.get("damage") is not None
                       and 0 <= l["t"] - h["t"] <= fenetre), key=lambda h: h["t"], default=None)
            d_ = l.get("detail") or {}
            resultats.append({"t": l["t"], "rage_count": l["score"], "final_score": l["damage"], "stage": l["stage"],
                              "confidence": l["confidence"], "hunter_rank_lus": d_.get("hunter_ranks_lus"),
                              "rc_images": d_.get("rc_images"), "final_images": d_.get("final_images"),
                              "hud_points": hud["damage"] if hud else None,
                              "ecart_hud_final_pct": round((l["damage"] - hud["damage"]) / hud["damage"] * 100, 3)
                              if hud and l["damage"] else None, "notes": l["notes"]})
        bilan[v] = {"titre": (videos.get(v) or {}).get("title"), "duree": (videos.get(v) or {}).get("duration"),
                    "formats_disponibles_p": pc_.get("hauteurs"), "image_lue_px": pc_.get("image_taille"),
                    "ecran_results_lu": bool(resultats),
                    "hud": [{"t": h["t"], "chrono": h["detail"]["chrono_hud"], "points": h["detail"].get("hud_points"),
                             "boss_rage_count": h["detail"]["hud_rage_count"]} for h in huds],
                    "resultats": resultats,
                    "lectures_texte": [{"source": l["score_source"], "score": l["score"], "damage": l.get("damage")}
                                       for l in lectures if l["video_id"] == v and l["mode"] == "gb"
                                       and l["score_source"] in ("titre", "description", "sous-titres")]}
    lignes = [{"channel": r["channel"], "video_ids": r["video_ids"], "total": r["score"]["total"], "runs": r["score"]["runs"],
               "rank": r["rank"], "confidence": r["confidence"], "notes": r["notes"],
               "runs_detail": [{k: x.get(k) for k in ("video_id", "t", "team", "damage", "exact", "score_source")} for x in r["runs_detail"]]}
              for r in d.lire(f"runs/{week}/gb.json", []) if set(r["video_ids"]) & set(ids)]
    return {"par_video": bilan, "lignes_gb": lignes}


def normaliser_argv(argv):
    """v26 : la tâche de relance anti-bot lance `lancer_pc.bat daily relance` (mot nu) ; l'option est `--relance`. Le 15/11 à 02:32
    `pc.py: error: unrecognized arguments: relance` : la relance n'a jamais tourné."""
    return ["--relance" if x == "relance" else x for x in argv]


def _echec_bloc(a, cause):
    """v26 : écrit le bloc « Passage complet : non » d'un passage daily/weekly qui échoue (jamais d'exception, jamais de push
    après une erreur git : le prochain passage commite le bloc, `Git.tirer`)."""
    if a.passage not in ("daily", "weekly"):
        return
    try:
        signaler_echec(a.passage, parse_iso(a.maintenant) if a.maintenant else maintenant(), cause,
                       git=None if (a.no_git or cause.startswith(("git", "fichier"))) else Git())
    except Exception:
        pass


if __name__ == "__main__":
    for flux in (sys.stdout, sys.stderr):  # titres coréens / japonais : la console Windows (cp1252) planterait sinon
        flux.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("passage", choices=["daily", "weekly", "builds", "ytdlp-test", "ytdlp-profil"],
                    help="builds : étape 2 (images de composition, builds, PowerPoint) ; ytdlp-test : cherche les réglages yt-dlp qui passent l'anti-bot")
    ap.add_argument("--mode", choices=["poc", "bot", "gb", "hotm"], help="avec builds --video : mode de la vidéo (défaut bot)")
    ap.add_argument("--semaine", help="avec builds : semaine AAAA-MM-JJ (défaut : semaine courante)")
    ap.add_argument("--profil", help="avec ytdlp-profil : dossier du profil Chrome du compte secondaire (ex. \"Profile 1\")")
    ap.add_argument("--no-git", action="store_true", help="pas de pull/push (essai local)")
    ap.add_argument("--relance", action="store_true", help="passage de relance (anti-bot) : pas de nouvelle relance programmée")
    ap.add_argument("--whisper", action="store_true", help="active Whisper (config pc.whisper_cmd requis)")
    ap.add_argument("--max", type=int, help="limite les vidéos traitées, sous-titres ET images")
    ap.add_argument("--video", action="append", help="ne traite que cette vidéo (identifiant YouTube ; répétable)")
    ap.add_argument("--publier-essai", action="store_true",
                    help="comme --garder-ocr, puis copie les meilleures images (JPEG) et textes dans docs/essais/ocr et les pousse")
    ap.add_argument("--images-par-video", type=int, help="avec --publier-essai : nombre d'images publiées par vidéo (défaut 6 à 8)")
    ap.add_argument("--resolution", type=int, help="télécharge les vidéos en hauteur ≤ N pixels (ex. 1080 pour tester les zones en 1080p)")
    ap.add_argument("--refaire", action="store_true", help="avec --video : retraite la vidéo même si elle est déjà faite")
    ap.add_argument("--garder-ocr", action="store_true", help="écrit le texte lu par tesseract et l'image dans logs/ocr/ (diagnostic)")
    ap.add_argument("--maintenant", help="instant simulé ISO 8601 (tests)")
    a = ap.parse_args(normaliser_argv(sys.argv[1:]))
    config = charger_config()
    verrou = Verrou(RACINE / "logs" / "pc.lock")
    ok, detenteur = verrou.prendre(a.passage + (f" --video {a.video[0]}" if a.video else ""))
    if not ok:      # un autre passage tourne : on n'ajoute ni yt-dlp ni OCR en parallèle (anti-bot, délais, git). Code 3 = refus, rien n'est perdu.
        print(f"Passage refusé : un autre passage PC tourne déjà ({detenteur}). Relancer quand il est terminé "
              f"(ou supprimer logs\\pc.lock s'il est resté après un arrêt brutal).", file=sys.stderr)
        if a.passage in ("daily", "weekly"):          # v26 : jamais d'échec sans trace
            try:
                signaler_echec(a.passage, parse_iso(a.maintenant) if a.maintenant else maintenant(),
                               f"passage refusé : un autre passage PC tourne déjà ({detenteur})")
            except Exception:
                pass
        sys.exit(3)
    import atexit
    atexit.register(verrou.liberer)
    if verrou.perime and a.passage in ("daily", "weekly") and (verrou.perime.get("passage") or "").split(" ")[0] in ("daily", "weekly"):
        try:      # v26 : le passage précédent est mort sans rien écrire (PC éteint, fenêtre fermée, arrêt brutal) : on le dit
            debut = verrou.perime.get("debut")
            instant_mort = parse_iso(datetime.fromtimestamp(debut, timezone.utc).isoformat()) if debut else maintenant()
            signaler_echec(verrou.perime["passage"].split(" ")[0], instant_mort,
                           "passage interrompu (PC éteint, fenêtre fermée ou processus tué : aucune erreur enregistrée)")
        except Exception:
            pass
    if a.passage == "ytdlp-profil":
        from donnees import CONFIG_PC_LOCALE, ecrire_atomique
        if not a.profil:
            profs = profils_chrome()
            print("Profils Chrome trouvés sur ce PC :" if profs else "Aucun profil Chrome trouvé.")
            for d, nom, mail in profs:
                print(f'  --profil "{d}"   nom : {nom}   compte : {mail or "(non connecté)"}')
            print('Relancer avec --profil "<dossier>" en choisissant le profil du compte SECONDAIRE.')
            sys.exit(0)
        js = options_js()
        if js is None:
            print("Aucun moteur JavaScript : YouTube n'enverra pas les vidéos. Installer Deno (winget install DenoLand.Deno), "
                  "fermer et rouvrir cmd, puis relancer cette commande.", file=sys.stderr)
            sys.exit(1)
        opts = [*js, "--impersonate", "chrome", "--cookies-from-browser", f"chrome:{a.profil}"]
        vid = (a.video or ["5MI-RLj7FSk"])[0]
        try:
            sortie = Outils({**config["pc"], "yt_dlp_options": opts})._lancer([config["pc"]["yt_dlp"], *opts, "-F", f"https://www.youtube.com/watch?v={vid}"], 120)
        except (RuntimeError, subprocess.TimeoutExpired, OutilAbsent) as e:
            print(f"ÉCHEC avec le profil « {a.profil} » : {str(e)[:200]}\nVérifier : Chrome fermé, profil connecté à YouTube (ouvrir une vidéo).", file=sys.stderr)
            sys.exit(1)
        if not a_format_video(sortie):
            print("ÉCHEC : YouTube ne liste que des vignettes (moteur JavaScript ou cookies insuffisants). Voir « EJS » dans "
                  "https://github.com/yt-dlp/yt-dlp/wiki/EJS", file=sys.stderr)
            sys.exit(1)
        ecrire_atomique(CONFIG_PC_LOCALE, json.dumps({"yt_dlp_options": opts}, ensure_ascii=False, indent=1) + "\n")
        print(f"RÉUSSI. Enregistré dans pc_local.json : {opts}")
        sys.exit(0)
    if a.passage == "ytdlp-test":
        from donnees import CONFIG_PC_LOCALE, ecrire_atomique
        vid = (a.video or ["5MI-RLj7FSk"])[0]
        print(f"Essai des réglages yt-dlp sur {vid} (aucun téléchargement)…", flush=True)
        opts = tester_ytdlp(config["pc"], vid, journal=lambda m: print(m, flush=True))
        if opts is None:
            print("Aucun réglage ne passe. Pistes : ouvrir YouTube dans Firefox (connecté), mettre à jour yt-dlp "
                  "(py -3 -m pip install -U \"yt-dlp[default,curl-cffi]\"), attendre 1 à 2 h (adresse limitée).", file=sys.stderr)
            sys.exit(1)
        ecrire_atomique(CONFIG_PC_LOCALE, json.dumps({"yt_dlp_options": opts}, ensure_ascii=False, indent=1) + "\n")
        print(f"Enregistré dans {CONFIG_PC_LOCALE.name} (local au PC, non publié) : {opts}")
        sys.exit(0)
    if a.passage == "builds" and a.video:          # essai sur une vidéo hors classement : `--video ID [--mode bot]`
        import builds as B
        import composition
        cfg2 = B.charger_config()
        b = B.build_essai(a.video[0], a.mode or "bot", cfg=cfg2, fournisseur=composition.fournisseur_pc(Outils(config["pc"]), cfg2, lambda m: print(m, flush=True), (RACINE / "logs" / "ocr") if a.garder_ocr else None))
        sortie = RACINE / "docs" / "essais" / "builds"
        sortie.mkdir(parents=True, exist_ok=True)
        (sortie / f"{a.video[0]}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        if a.garder_ocr:       # textes complets des écrans hors composition (stats, statues, fiche…) : publiés avec le JSON, plus de collage
            dossier_ocr = sortie / f"{a.video[0]}_ocr"
            for f in [*(RACINE / "logs" / "ocr").glob(f"{a.video[0]}_hors-compo_*.*"), *(RACINE / "logs" / "ocr").glob(f"{a.video[0]}_compo_*.jpg")]:
                if f.suffix in (".txt", ".jpg"):
                    dossier_ocr.mkdir(parents=True, exist_ok=True)
                    (dossier_ocr / f.name).write_bytes(f.read_bytes())
        print(f"{b['status']} — {b['counts']} — {b['notes']}")
        if not a.no_git:
            try:
                Git().pousser_chemin(f"essai: build {a.video[0]}", "docs/essais/builds")
                print("Essai publié dans docs/essais/builds.")
            except GitErreur as e:
                print(f"ERREUR publication : {e}", file=sys.stderr)
        sys.exit(0)
    if a.passage == "builds":
        try:
            semaine = a.semaine or id_semaine(maintenant())
            n = passage_builds(semaine, Outils(config["pc"]), None if a.no_git else Git(), journal=lambda m: print(m, flush=True), force=a.refaire)
            from collections import Counter
            print(f"Semaine {semaine} : {len(n)} build(s) — {dict(Counter(b['status'] for b in n))}")
        except GitErreur as e:
            print(f"ERREUR git : {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    if a.resolution:
        config["pc"]["images"]["format_video"] = f"bv*[height<={a.resolution}]/b[height<={a.resolution}]"
    try:
        r = lancer(a.passage, parse_iso(a.maintenant) if a.maintenant else maintenant(), config=config,
                   git=None if a.no_git else Git(), whisper=a.whisper, maximum=a.max, seulement=set(a.video or []), refaire=a.refaire, relance=a.relance,
                   journal=lambda m: print(m, flush=True), dormir=time.sleep,
                   ocr_debug=(RACINE / "logs" / "ocr") if (a.garder_ocr or a.publier_essai) else None)
    except GitErreur as e:
        print(f"ERREUR git : {e}\nPassage interrompu (conflit ou réseau) : relancer plus tard.", file=sys.stderr)
        _echec_bloc(a, f"git : {str(e)[:250]}")
        sys.exit(1)
    except JsonAbime as e:
        print(f"ERREUR fichier de données : {e}\nVérifier : py -3 pipeline\\verifier_json.py", file=sys.stderr)
        _echec_bloc(a, f"fichier de données abîmé : {str(e)[:250]}")
        sys.exit(1)
    except Exception as e:        # crash : tracé dans logs\pc.log, signalé en tête du rapport
        import traceback
        traceback.print_exc()
        _echec_bloc(a, f"crash : {type(e).__name__} : {str(e)[:200]}")
        sys.exit(2)
    if a.publier_essai:
        try:
            d_ = Donnees()
            ids = set(a.video or [])
            resume = {"semaine": r["week"], "alertes": r["alertes"],
                      "lectures": [l for l in d_.lectures(r["week"]) if not ids or l["video_id"] in ids],
                      "processed": {v: p for v, p in d_.processed().items() if v in ids}}
            nom = "_resume.json"
            if len(ids) > 1 or a.resolution:
                nom = f"_resume_{len(ids)}video{'s' if len(ids) > 1 else ''}{'_' + str(a.resolution) + 'p' if a.resolution else ''}.json"
                resume["bilan"] = bilan_essai(d_, r["week"], ids, config)
            noms = publier_essai(Outils(config["pc"]), RACINE / "logs" / "ocr", RACINE / "docs" / "essais" / "ocr", Git(),
                                 maximum=(a.images_par_video or (6 if len(ids) > 3 else 8)), resume=resume, nom_resume=nom)
            print(f"Essai publié dans docs/essais/ocr : {len(noms)} fichier(s).")
        except (GitErreur, OutilAbsent, OSError, RuntimeError) as e:
            print(f"ERREUR publication de l'essai : {e}", file=sys.stderr)
    print(f"Semaine {r['week']} : {r['traitees']} vidéo(s) traitée(s).")
    for x in r["alertes"]:
        print("-", x)
