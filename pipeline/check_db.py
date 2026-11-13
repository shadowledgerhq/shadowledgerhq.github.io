"""Contrôle de la base de données (data/db/*.json). Bibliothèque standard seulement.

Usage : python3 pipeline/check_db.py [--verbose] [--no-report]
Code de sortie : 0 = aucune erreur bloquante (les avertissements ne bloquent pas), 1 = erreur(s).
Écrit data/db/_rapport.md (30 lignes max), écrasé à chaque exécution.
Règles : data/db/_schema.md et skill shadow-ledger (« Objet de la base »).
"""
import json
import re
import struct
import sys
from collections import Counter
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DB = RACINE / "data" / "db"
ID_RE = re.compile(r"^[a-z0-9-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAILLE_ICONE = (128, 128)
SANS_ICONE = {"patches"}          # pas d'icône par nature
SEMAINE_NULL_OK = {"subjugation_support", "proof_modifiers"}  # entrées du wiki sans semaine
MAX_LIGNES_RAPPORT = 30


class Fichier:
    def __init__(self, nom):
        self.nom, self.entrees = nom, 0
        self.erreurs, self.avertissements = [], []

    def err(self, id_, msg):
        self.erreurs.append((id_, msg))

    def warn(self, id_, msg):
        self.avertissements.append((id_, msg))


def taille_png(chemin):
    """(largeur, hauteur) lues dans l'en-tête IHDR, ou None si ce n'est pas un PNG."""
    with open(chemin, "rb") as f:
        tete = f.read(24)
    if len(tete) < 24 or tete[:8] != b"\x89PNG\r\n\x1a\n" or tete[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", tete[16:24])


def date_valide(s):
    if not isinstance(s, str) or not DATE_RE.match(s):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def verifier_icone(r, id_, chemin, ou, obligatoire=True):
    if not chemin:
        if obligatoire:
            r.warn(id_, f"icône absente (null){ou}")
        return
    p = RACINE / chemin
    if not p.is_file():
        r.err(id_, f"fichier d'icône introuvable : {chemin}")
        return
    t = taille_png(p)
    if t is None:
        r.err(id_, f"icône non PNG : {chemin}")
    elif t != TAILLE_ICONE:
        r.err(id_, f"icône {t[0]}×{t[1]} au lieu de 128×128 : {chemin}")


def verifier_noms(r, id_, name, ou=""):
    if not isinstance(name, dict):
        r.err(id_, f"`name` absent ou invalide{ou}")
        return
    for lang in ("fr", "en"):
        if not (isinstance(name.get(lang), str) and name[lang].strip()):
            r.warn(id_, f"name.{lang} vide{ou}")


def verifier_entree(r, e, nom, ids_hunters):
    id_ = e.get("id") if isinstance(e.get("id"), str) else "?"
    if not isinstance(e.get("id"), str) or not ID_RE.match(e["id"]):
        r.err(id_, f"id invalide (a-z0-9- attendu) : {e.get('id')!r}")
    verifier_noms(r, id_, e.get("name"))
    src = e.get("source")
    if not (isinstance(src, str) and src.strip()):
        r.err(id_, "source absente")
    elif not src.startswith(("http://", "https://")):
        r.warn(id_, "source non URL (capture ou texte)")
    if not date_valide(e.get("verified_at")):
        r.err(id_, f"verified_at absent ou invalide : {e.get('verified_at')!r}")
    if "game_version" not in e:
        r.warn(id_, "game_version absent")  # null toléré
    if nom not in SANS_ICONE:
        verifier_icone(r, id_, e.get("icon"), "")
    # Semaine (soutien de subjugation, preuves HOTM)
    if nom in SEMAINE_NULL_OK and e.get("week") is not None and not date_valide(e["week"]):
        r.err(id_, f"week invalide : {e['week']!r}")
    # Références croisées
    if nom == "weapons":
        h = e.get("hunter_id")
        if h is not None and h not in ids_hunters:
            r.err(id_, f"hunter_id inconnu dans hunters.json : {h!r}")
    if nom == "artifact_sets":
        pieces = e.get("pieces")
        if not isinstance(pieces, list) or not pieces:
            r.warn(id_, "aucune pièce")
        else:
            for p in pieces:
                pid = f"{id_}/{p.get('slot') or '?'}"
                if "slot" not in p:
                    r.err(pid, "clé `slot` absente de la pièce")
                elif not p["slot"]:
                    r.warn(pid, "slot vide (pièce)")
                verifier_noms(r, pid, p.get("name"), " (pièce)")
                verifier_icone(r, pid, p.get("icon"), " (pièce)")
    if nom == "blessings" and not e.get("effects"):
        r.warn(id_, "pierre sans effets")


def verifier_patches(r, donnees, ids_par_fichier):
    """ids de changes[] : slugs provisoires, avertissement seulement."""
    for p in donnees:
        for c in p.get("changes") or []:
            cat, cid = c.get("category"), c.get("id")
            if cat == "rules":  # règles de mode : pas de fichier db
                continue
            if cat not in ids_par_fichier:
                r.warn(p.get("id", "?"), f"changes : catégorie inconnue {cat!r}")
            elif cid not in ids_par_fichier[cat]:
                r.warn(p.get("id", "?"), f"changes : id introuvable dans {cat}.json : {cid!r}")


def charger(chemin, r):
    try:
        d = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        r.err("-", f"JSON illisible : {ex}")
        return None
    if not isinstance(d, list) or not all(isinstance(x, dict) for x in d):
        r.err("-", "le fichier doit être une liste d'objets JSON")
        return None
    return d


def controler():
    fichiers, donnees = [], {}
    for chemin in sorted(DB.glob("*.json")):
        r = Fichier(chemin.stem)
        d = charger(chemin, r)
        if d is not None:
            donnees[r.nom] = d
            r.entrees = len(d)
        fichiers.append(r)
    ids_par_fichier = {n: {e.get("id") for e in d} for n, d in donnees.items()}
    ids_hunters = ids_par_fichier.get("hunters", set())
    for r in fichiers:
        d = donnees.get(r.nom)
        if d is None:
            continue
        vus = Counter(e.get("id") for e in d)
        for i, n in vus.items():
            if n > 1:
                r.err(i, f"id en double ({n} fois)")
        for e in d:
            verifier_entree(r, e, r.nom, ids_hunters)
        if r.nom == "patches":
            verifier_patches(r, d, ids_par_fichier)
    return fichiers


def resume(fichiers, verbose):
    lignes = []
    for r in fichiers:
        lignes.append(f"{r.nom}.json : {r.entrees} entrées, {len(r.erreurs)} erreur(s), {len(r.avertissements)} avertissement(s)")
        if verbose or r.erreurs:
            for i, m in r.erreurs:
                lignes.append(f"  ERREUR [{i}] {m}")
        if verbose:
            for i, m in r.avertissements:
                lignes.append(f"  avertissement [{i}] {m}")
    return lignes


def rapport(fichiers):
    te = sum(len(r.erreurs) for r in fichiers)
    tw = sum(len(r.avertissements) for r in fichiers)
    L = [f"# Rapport de contrôle de la base — {date.today().isoformat()}",
         f"Total : {sum(r.entrees for r in fichiers)} entrées, **{te} erreur(s)**, {tw} avertissement(s). "
         "Généré par `pipeline/check_db.py` (écrasé à chaque exécution).", "",
         "| Fichier | Entrées | Erreurs | Avertissements |", "| --- | ---: | ---: | ---: |"]
    for r in fichiers:
        L.append(f"| {r.nom} | {r.entrees} | {len(r.erreurs)} | {len(r.avertissements)} |")
    tout = Counter()
    for r in fichiers:
        for _, m in r.avertissements:
            tout[re.sub(r"(?<=changes : id introuvable dans ).*|(?<=changes : catégorie inconnue ).*", "…", re.sub(r" \(pièce\)", "", m))] += 1
    if tout:
        L += ["", "Avertissements par type (à suivre dans le temps) :"]
        L += [f"- {n} × {m}" for m, n in tout.most_common(8)]
    if te:
        L += ["", "Erreurs (premières) :"]
        L += [f"- {r.nom} [{i}] {m}" for r in fichiers for i, m in r.erreurs][:6]
    return L[:MAX_LIGNES_RAPPORT]


def main(argv):
    fichiers = controler()
    for l in resume(fichiers, "--verbose" in argv):
        print(l)
    erreurs = sum(len(r.erreurs) for r in fichiers)
    print(f"\n{'ÉCHEC' if erreurs else 'OK'} : {erreurs} erreur(s) bloquante(s), "
          f"{sum(len(r.avertissements) for r in fichiers)} avertissement(s).")
    if "--no-report" not in argv:
        (DB / "_rapport.md").write_text("\n".join(rapport(fichiers)) + "\n", encoding="utf-8")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
