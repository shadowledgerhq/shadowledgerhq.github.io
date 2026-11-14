"""Export Excel des classements d'une semaine (BROUILLON : aucune spécification d'export n'a encore été donnée par la
discussion 1 ; colonnes et mise en forme à valider). Lit `data/runs/<semaine>/<mode>.json`, écrit
`exports/<semaine>/classements.xlsx` (un onglet par mode). Gratuit : `py -3 -m pip install openpyxl` (hors étape 1, qui
reste en bibliothèque standard).

    python3 pipeline/export_excel.py [AAAA-MM-JJ] [--sortie DOSSIER]
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
MODES = ("poc", "bot", "gb", "hotm")
UNITES = {"damage": "Dégâts", "seconds": "Temps (s)", "rage_count": "Rage Count"}
COLONNES = ["Rang", "Joueur", "Score", "Unité", "Runs", "Statut", "Source", "Publiée (Paris)", "Vidéo", "Notes"]


def lignes_mode(runs):
    """[ligne] triée : classés (rang) d'abord, puis les autres (a_verifier). Une ligne = une liste de cellules."""
    def cle(r):
        return (r.get("rank") is None, r.get("rank") or 0, str(r.get("player") or ""))
    sortie = []
    for r in sorted(runs, key=cle):
        sc = r.get("score") or {}
        sortie.append([r.get("rank"), r.get("player") or r.get("channel"), sc.get("total"), UNITES.get(sc.get("unit"), sc.get("unit")),
                       " + ".join(str(x) for x in sc.get("runs", [])), r.get("confidence"), r.get("score_source"),
                       (r.get("published_at") or "")[:16].replace("T", " "),
                       f"https://www.youtube.com/watch?v={r['video_id']}" if r.get("video_id") else None, r.get("notes")])
    return sortie


def charger(semaine, racine=RACINE):
    dossier = Path(racine) / "data" / "runs" / semaine
    out = {}
    for mode in MODES:
        f = dossier / f"{mode}.json"
        if f.exists():
            out[mode] = json.loads(f.read_text(encoding="utf-8"))
    for f in sorted(dossier.glob("hotm-gate-*.json")):
        out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return out


def exporter(semaine, sortie=None, racine=RACINE):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        sys.exit("openpyxl absent : py -3 -m pip install openpyxl")
    donnees = charger(semaine, racine)
    if not donnees:
        sys.exit(f"Aucun classement pour la semaine {semaine}.")
    wb = Workbook()
    wb.remove(wb.active)
    for nom, runs in donnees.items():
        ws = wb.create_sheet(nom.upper()[:31])
        ws.append(COLONNES)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="203864")
        for ligne in lignes_mode(runs):
            ws.append(ligne)
        for i, largeur in enumerate([6, 22, 18, 12, 28, 12, 14, 17, 44, 70], 1):
            ws.column_dimensions[chr(64 + i)].width = largeur
        ws.freeze_panes = "A2"
        for ligne in ws.iter_rows(min_row=2):
            if ligne[5].value != "sur":
                for c in ligne:
                    c.font = Font(italic=True, color="7F7F7F")
            if isinstance(ligne[2].value, (int, float)) and ligne[3].value == "Dégâts":
                ligne[2].number_format = "#,##0"
    dossier = Path(sortie) if sortie else Path(racine) / "exports" / semaine
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "classements.xlsx"
    wb.save(fichier)
    return fichier


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("semaine", nargs="?")
    ap.add_argument("--sortie")
    a = ap.parse_args()
    semaine = a.semaine or sorted(p.name for p in (RACINE / "data" / "runs").iterdir() if p.is_dir())[-1]
    print(exporter(semaine, a.sortie))
