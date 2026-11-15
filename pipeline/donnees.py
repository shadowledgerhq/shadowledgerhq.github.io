"""Lecture/écriture des fichiers de data/ (docs/SPEC_ETAPE1.md §5).
N'écrit un fichier que si son contenu change (pas de commit inutile)."""
import json
import os
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).resolve().parent / "config" / "etape1.json"


CONFIG_PC_LOCALE = Path(__file__).resolve().parent / "config" / "pc_local.json"


def charger_config(chemin=CONFIG, locale=CONFIG_PC_LOCALE):
    """Config de l'étape 1 + réglages propres au PC (`pc_local.json`, ignoré par git : options yt-dlp, cookies…).
    Les clés de `pc_local.json` remplacent celles de `pc` (ex. `yt_dlp_options`)."""
    cfg = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if chemin == CONFIG and Path(locale).exists():
        cfg.setdefault("pc", {}).update(lire_json(locale))
    return cfg


class JsonAbime(ValueError):
    """Fichier JSON illisible : le message nomme le fichier, la ligne et la cause probable."""


def lire_json(chemin):
    """json.loads d'un fichier, avec le nom du fichier fautif dans l'erreur (JsonAbime)."""
    p = Path(chemin)
    texte = p.read_text(encoding="utf-8")
    try:
        return json.loads(texte)
    except json.JSONDecodeError as e:
        marq = any(l.startswith(("<<<<<<<", "=======", ">>>>>>>")) for l in texte.splitlines())
        cause = "marqueurs de conflit git (<<<<<<<) dans le fichier" if marq else "fichier coupé ou abîmé"
        raise JsonAbime(f"{p} illisible : {e.msg} (ligne {e.lineno}, colonne {e.colno}) ; {cause}") from e


def ecrire_atomique(p, texte):
    """Écrit dans un fichier temporaire voisin puis remplace : jamais de fichier à moitié écrit."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(texte, encoding="utf-8")
    os.replace(tmp, p)


class Donnees:
    def __init__(self, racine=RACINE):
        self.data = Path(racine) / "data"

    # --- JSON génériques ---
    def lire(self, chemin, defaut):
        p = self.data / chemin
        if not p.exists():
            return defaut
        return lire_json(p)

    def ecrire(self, chemin, contenu):
        p = self.data / chemin
        texte = contenu if isinstance(contenu, str) else (
            json.dumps(contenu, ensure_ascii=False, indent=2) + "\n")
        if p.exists() and p.read_text(encoding="utf-8") == texte:
            return False
        ecrire_atomique(p, texte)
        return True

    # --- fichiers nommés ---
    def processed(self):
        return self.lire("processed.json", {})

    def rejected(self, week):
        return self.lire(f"rejected/{week}.json", [])

    def tous_rejetes(self):
        ids = set()
        for p in (self.data / "rejected").glob("*.json"):
            ids |= {r["video_id"] for r in lire_json(p)}
        return ids

    def channels(self):
        return self.lire("channels.json", [])

    def meta(self, week):
        return self.lire(f"runs/{week}/_meta.json", None)

    def lectures(self, week):
        """Runs lues par les tris (une entrée par score lu), entrée de classement.py."""
        return self.lire(f"runs/{week}/_lectures.json", [])

    def videos(self, week):
        """Métadonnées des vidéos de la semaine (titre, chaîne, date…), indexées par video_id."""
        return self.lire(f"runs/{week}/_videos.json", {})

    def boss(self, week):
        return self.lire(f"runs/{week}/_boss.json", [])


def ajouter_rejet(liste, entree):
    """Ajoute un rejet s'il n'y est pas déjà (clé video_id). Retourne True si ajouté."""
    if any(r["video_id"] == entree["video_id"] for r in liste):
        return False
    liste.append(entree)
    return True
