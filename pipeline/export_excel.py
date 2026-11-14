"""Export Excel des classements d'une semaine, habillage « Shadow Ledger » (Solo Leveling: Arise : nuit, violet de l'armée
des ombres, bleu du mana, or du rang S). BROUILLON : colonnes et contenu à valider par la discussion 1.
Lit `data/runs/<semaine>/<mode>.json` et `hotm-gate-<n>.json`, écrit `exports/<semaine>/classements.xlsx` :
une page de garde + un onglet par mode (HOTM : un onglet par porte ; onglet vide s'il n'y a aucune donnée).
Gratuit : `py -3 -m pip install openpyxl` (hors étape 1, qui reste en bibliothèque standard).

    python3 pipeline/export_excel.py [AAAA-MM-JJ] [--sortie DOSSIER]
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
MODES = ("poc", "bot", "gb", "hotm")
NOMS = {"poc": "POC · Power Of Calamity", "bot": "BOT · Battlefield Of Time", "gb": "GB · Guild Boss",
        "hotm": "HOTM · Hall Of The Monarchs"}
UNITES = {"damage": "Dégâts", "seconds": "Temps", "rage_count": "Rage Count", "points": "Points"}
EQUIPE = {"poc": "Éq.", "gb": "G"}
COLONNES = ["Rang", "Joueur", "Score", "Détail des runs", "Statut", "Publiée (Paris)", "Vidéo", "Notes"]
LARGEURS = [11, 24, 18, 34, 15, 17, 18, 80]
# Palette (hex sans #)
NUIT, PANNEAU, PANNEAU2, ENTETE = "0B0E1A", "121830", "181F3D", "1E1B4B"
VIOLET, BLEU, OR, ARGENT, BRONZE, TEXTE, SOURD = "7C3AED", "38BDF8", "F5C542", "C0C8D8", "CD7F32", "E5E9F5", "7F88A8"
VERT, AMBRE = "34D399", "FBBF24"
PODIUM = {1: ("🥇", OR), 2: ("🥈", ARGENT), 3: ("🥉", BRONZE)}


def _compact(v, unite):
    if unite == "damage" and isinstance(v, (int, float)):
        for seuil, suffixe in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
            if abs(v) >= seuil:
                return f"{v / seuil:.2f} {suffixe}".replace(".", ",")
        return f"{v:,.0f}".replace(",", " ")
    if unite == "seconds" and isinstance(v, (int, float)):
        return f"{v:.2f} s".replace(".", ",")
    if unite == "rage_count" and isinstance(v, (int, float)):
        return f"{v:.0f}"
    return f"{v:,.0f}".replace(",", " ") if isinstance(v, (int, float)) else str(v)


def detail_runs(r):
    """« Éq.1 133,00 T + Éq.2 120,50 T » : une valeur par run, étiquetée par équipe / groupe quand elle est connue."""
    sc = r.get("score") or {}
    unite, valeurs = sc.get("unit"), sc.get("runs") or []
    equipes = [d.get("team") for d in (r.get("runs_detail") or [])]
    pieces = []
    for i, v in enumerate(valeurs):
        eq = equipes[i] if i < len(equipes) and len(equipes) == len(valeurs) else None
        etiquette = f"{EQUIPE.get(r.get('mode'), '')}{eq} " if eq and EQUIPE.get(r.get("mode")) else ""
        pieces.append(etiquette + _compact(v, unite))
    return " + ".join(pieces) if len(pieces) > 1 else ""      # une seule run : le score la donne déjà


def lignes_mode(runs):
    """[ligne] triée : classés (rang) d'abord, puis les autres. Colonnes : voir COLONNES (+ unité en dernier, usage interne)."""
    def cle(r):
        return (r.get("rank") is None, r.get("rank") or 0, str(r.get("player") or ""))
    sortie = []
    for r in sorted(runs, key=cle):
        sc = r.get("score") or {}
        sortie.append([r.get("rank"), r.get("player") or r.get("channel"), sc.get("total"), detail_runs(r), r.get("confidence"),
                       (r.get("published_at") or "")[:16].replace("T", " "),
                       f"https://www.youtube.com/watch?v={r['video_id']}" if r.get("video_id") else None, r.get("notes"),
                       sc.get("unit")])
    return sortie


def charger(semaine, racine=RACINE):
    """{onglet: runs}. HOTM : un onglet par porte (`hotm-gate-<n>.json`) ; onglet « hotm » vide s'il n'y en a aucune."""
    dossier = Path(racine) / "data" / "runs" / semaine
    out = {}
    for mode in MODES:
        f = dossier / f"{mode}.json"
        if mode == "hotm":
            portes = sorted(dossier.glob("hotm-gate-*.json"), key=lambda p: p.stem)
            for p in portes:
                out[p.stem.replace("-", " ")] = json.loads(p.read_text(encoding="utf-8"))
            if not portes:
                out["hotm"] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        elif f.exists():
            out[mode] = json.loads(f.read_text(encoding="utf-8"))
        else:
            out[mode] = []
    return out


def _nom_onglet(cle):
    if cle in NOMS:
        return NOMS[cle]
    if cle.startswith("hotm gate"):
        return f"HOTM · Porte {cle.rsplit(' ', 1)[-1]}"
    return cle.upper()


def _semaine_txt(semaine):
    d = date.fromisoformat(semaine)
    f = d + timedelta(days=7)
    return f"Semaine du jeudi {d:%d/%m/%Y} 01h au jeudi {f:%d/%m/%Y} 01h (heure de Paris)"


def exporter(semaine, sortie=None, racine=RACINE):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.worksheet.properties import WorksheetProperties
    except ImportError:
        sys.exit("openpyxl absent : py -3 -m pip install openpyxl")
    donnees = charger(semaine, racine)
    if not any(donnees.values()) and not (Path(racine) / "data" / "runs" / semaine).exists():
        sys.exit(f"Aucun classement pour la semaine {semaine}.")
    fond = lambda c: PatternFill("solid", fgColor=c)
    police = lambda c=TEXTE, t=11, g=False, i=False: Font(name="Segoe UI", size=t, bold=g, italic=i, color=c)
    trait = Side(style="thin", color="2A3158")
    wb = Workbook()
    accueil = wb.active
    accueil.title = "Shadow Ledger"

    def peindre(ws, lignes, colonnes):
        for ligne in ws.iter_rows(min_row=1, max_row=lignes, min_col=1, max_col=colonnes):
            for c in ligne:
                c.fill = fond(NUIT)
                c.font = police()
        ws.sheet_view.showGridLines = False

    def banniere(ws, colonnes, titre, sous):
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=colonnes)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=colonnes)
        ws["A1"], ws["A2"] = "⚔  SHADOW LEDGER  ·  " + titre, sous
        ws["A1"].font, ws["A2"].font = police(BLEU, 20, True), police(SOURD, 11, i=True)
        ws["A1"].alignment = ws["A2"].alignment = Alignment(vertical="center", indent=1)
        for c in range(1, colonnes + 1):
            ws.cell(3, c).fill = fond(VIOLET)
            ws.cell(3, c).border = Border()
        ws.row_dimensions[1].height, ws.row_dimensions[2].height, ws.row_dimensions[3].height = 40, 22, 4

    # --- page de garde -------------------------------------------------------------------------------------------
    peindre(accueil, 60, 26)
    banniere(accueil, 6, "Solo Leveling: Arise", _semaine_txt(semaine))
    for i, l in enumerate([14, 36, 14, 14, 14, 30], 1):
        accueil.column_dimensions[chr(64 + i)].width = l
    accueil["B5"], accueil["B6"] = "Classements hebdomadaires", "Source des données : slagate.com · classements calculés automatiquement"
    accueil["B5"].font, accueil["B6"].font = police(OR, 14, True), police(SOURD, 10, i=True)
    for j, t in enumerate(["Mode", "Classés", "À vérifier", "Total"], 2):
        c = accueil.cell(8, j, t)
        c.font, c.fill, c.alignment = police(TEXTE, 11, True), fond(ENTETE), Alignment(horizontal="center" if j > 2 else "left", indent=1)
    ligne = 9
    for cle, runs in donnees.items():
        sur = sum(1 for r in runs if r.get("confidence") == "sur" and r.get("rank") is not None)
        for j, v in enumerate([_nom_onglet(cle), sur, len(runs) - sur, len(runs)], 2):
            c = accueil.cell(ligne, j, v)
            c.font = police(TEXTE if j == 2 else (VERT if j == 3 else AMBRE if j == 4 else SOURD), 11, j == 2)
            c.fill = fond(PANNEAU if ligne % 2 else PANNEAU2)
            c.alignment = Alignment(horizontal="left" if j == 2 else "center", indent=1)
        ligne += 1
    accueil.cell(ligne + 1, 2, "Légende").font = police(OR, 12, True)
    for k, (txt, couleur) in enumerate([("✔ Sûr : valeur contrôlée, ligne classée", VERT),
                                         ("⚠ À vérifier : valeur provisoire ou non contrôlée, ligne non classée", AMBRE),
                                         ("🥇🥈🥉 Podium du classement", OR)], ligne + 2):
        accueil.cell(k, 2, txt).font = police(couleur, 10)

    # --- un onglet par mode (ou par porte HOTM) ------------------------------------------------------------------
    for cle, runs in donnees.items():
        mode = "hotm" if cle.startswith("hotm") else cle
        ws = wb.create_sheet(_nom_onglet(cle).split(" · ")[0] + (" " + cle.rsplit(" ", 1)[-1] if cle.startswith("hotm gate") else ""))
        ws.sheet_properties.tabColor = {"poc": "EF4444", "bot": BLEU, "gb": OR, "hotm": VIOLET}.get(mode, VIOLET)
        lignes = lignes_mode(runs)
        peindre(ws, max(len(lignes) + 30, 60), 26)
        banniere(ws, len(COLONNES), _nom_onglet(cle), _semaine_txt(semaine))
        for i, l in enumerate(LARGEURS, 1):
            ws.column_dimensions[chr(64 + i)].width = l
        for j, t in enumerate(COLONNES, 1):
            c = ws.cell(5, j, t)
            c.font, c.fill, c.border = police(BLEU, 11, True), fond(ENTETE), Border(bottom=Side(style="medium", color=VIOLET))
            c.alignment = Alignment(horizontal="center" if j in (1, 3, 5, 6, 7) else "left", vertical="center", indent=0 if j in (1, 3, 5, 6, 7) else 1)
        ws.row_dimensions[5].height = 26
        if not lignes:
            ws.merge_cells(start_row=7, start_column=1, end_row=7, end_column=len(COLONNES))
            ws["A7"] = "Aucune donnée cette semaine pour ce classement."
            ws["A7"].font, ws["A7"].alignment = police(SOURD, 12, i=True), Alignment(horizontal="center")
        for k, l in enumerate(lignes, 6):
            *cellules, unite = l
            sur = cellules[4] == "sur"
            rang = cellules[0]
            for j, v in enumerate(cellules, 1):
                c = ws.cell(k, j, v)
                c.fill, c.border = fond(PANNEAU if k % 2 == 0 else PANNEAU2), Border(bottom=trait)
                c.font = police(TEXTE if sur else SOURD, 11, j in (1, 2, 3) and sur, not sur)
                c.alignment = Alignment(vertical="center", horizontal="center" if j in (1, 3, 5, 6, 7) else "left",
                                        indent=0 if j in (1, 3, 5, 6, 7) else 1, wrap_text=(j == 8))
            if rang in PODIUM:
                medaille, couleur = PODIUM[rang]
                ws.cell(k, 1).value = f"{medaille} {rang}"
                for j in (1, 2, 3):
                    ws.cell(k, j).font = police(couleur, 12, True)
            elif rang is None:
                ws.cell(k, 1).value = "—"
            s = ws.cell(k, 5)
            s.value, s.font = ("✔ Sûr", police(VERT, 11, True)) if sur else ("⚠ À vérifier", police(AMBRE, 11, False, True))
            sc = ws.cell(k, 3)
            if isinstance(sc.value, (int, float)):
                sc.number_format = ('#,##0.00,,,," T"' if sc.value >= 1e12 else '#,##0.00,,," M"' if sc.value >= 1e8 and unite == "damage"
                                    else '0.00" s"' if unite == "seconds" else '0" RC"' if unite == "rage_count" else "#,##0")
            if cellules[6]:
                v = ws.cell(k, 7)
                v.hyperlink, v.value, v.font = cellules[6], "▶ Voir la vidéo", police(BLEU, 11, False)
                v.font = Font(name="Segoe UI", size=11, color=BLEU, underline="single")
            ws.row_dimensions[k].height = 30 if (cellules[7] and len(cellules[7]) > 90) else 22
        ws.freeze_panes = "A6"
        ws.auto_filter.ref = f"A5:{chr(64 + len(COLONNES))}{max(5 + len(lignes), 6)}"
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
