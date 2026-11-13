"""Lecture/écriture des fichiers de data/ (docs/SPEC_ETAPE1.md §5).
N'écrit un fichier que si son contenu change (pas de commit inutile)."""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).resolve().parent / "config" / "etape1.json"


def charger_config(chemin=CONFIG):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


class Donnees:
    def __init__(self, racine=RACINE):
        self.data = Path(racine) / "data"

    # --- JSON génériques ---
    def lire(self, chemin, defaut):
        p = self.data / chemin
        if not p.exists():
            return defaut
        return json.loads(p.read_text(encoding="utf-8"))

    def ecrire(self, chemin, contenu):
        p = self.data / chemin
        texte = contenu if isinstance(contenu, str) else (
            json.dumps(contenu, ensure_ascii=False, indent=2) + "\n")
        if p.exists() and p.read_text(encoding="utf-8") == texte:
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texte, encoding="utf-8")
        return True

    # --- fichiers nommés ---
    def processed(self):
        return self.lire("processed.json", {})

    def rejected(self, week):
        return self.lire(f"rejected/{week}.json", [])

    def tous_rejetes(self):
        ids = set()
        for p in (self.data / "rejected").glob("*.json"):
            ids |= {r["video_id"] for r in json.loads(p.read_text(encoding="utf-8"))}
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
