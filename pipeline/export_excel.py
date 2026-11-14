"""Export Excel des classements d'une semaine (SPEC_ETAPE1 §5.6, v21), habillage « Shadow Ledger » (Solo Leveling: Arise :
nuit, violet de l'armée des ombres, bleu du mana, or du rang S). Mise en forme validée par Alexis le 14/11.
Lit `data/runs/<semaine>/<mode>.json`, `hotm-gate-<n>.json` (jamais `hotm-gate-inconnue`), `_meta.json` et
`data/rejected/<semaine>.json` ; écrit `exports/<semaine>/classements.xlsx` : page de garde, POC, BOT, GB, HOTM (un onglet
par porte avec données, sinon un onglet vide), Rejetées. Gratuit : `py -3 -m pip install openpyxl` (hors étape 1).

    python3 pipeline/export_excel.py [AAAA-MM-JJ] [--sortie DOSSIER]
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
RACINE = Path(__file__).resolve().parents[1]
MODES = ("poc", "bot", "gb", "hotm")
NOMS = {"poc": "POC · Power Of Calamity", "bot": "BOT · Battlefield Of Time", "gb": "GB · Guild Boss",
        "hotm": "HOTM · Hall Of The Monarchs"}
EQUIPE = {"poc": "Éq. ", "gb": "G"}
SEMAINES_ESSAI = {"2026-11-12"}          # semaine d'essai : jamais gelée ni publiée (SPEC §6)
CREDIT = "Scores lus sur les vidéos YouTube des joueurs cités."
# Largeurs de colonnes (caractères)
L = {"Rang": 11, "Joueur": 26, "Score": 21, "Détail des runs": 38, "Dégâts": 20, "Statut": 15, "Publiée (Paris)": 17,
     "Vidéo": 18, "Notes": 58}
CIBLE = 218          # largeur visée (caractères) d'une fenêtre Excel courante : les marges centrent le tableau
# Palette (hex sans #)
NUIT, PANNEAU, PANNEAU2, ENTETE, TOP10 = "0B0E1A", "121830", "181F3D", "1E1B4B", "261C5C"
VIOLET, BLEU, OR, ARGENT, BRONZE, TEXTE, SOURD = "7C3AED", "38BDF8", "F5C542", "C0C8D8", "CD7F32", "E5E9F5", "7F88A8"
VERT, AMBRE, ROUGE = "34D399", "FBBF24", "F87171"
PODIUM = {1: ("🥇", OR), 2: ("🥈", ARGENT), 3: ("🥉", BRONZE)}


# --- mise en forme des valeurs ---------------------------------------------------------------------------------------

def entier(v):
    return f"{int(round(v)):,}".replace(",", " ")


def arrondi(v):
    for seuil, suffixe in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(v) >= seuil:
            return f"{v / seuil:.2f} {suffixe}".replace(".", ",")
    return entier(v)


def temps(s):
    """Secondes -> `mm:ss.mmm` comme l'écran BOT (19.926 -> 00:19.926)."""
    ms = int(round(s * 1000))
    return f"{ms // 60000:02d}:{ms % 60000 // 1000:02d}.{ms % 1000:03d}"


def valeur_run(v, unite):
    if unite == "seconds":
        return temps(v)
    if unite == "rage_count":
        return f"{v:.0f}"
    return entier(v)


def detail_runs(r):
    """POC et GB : toujours remplie, `Éq. 1 : … · Éq. 2 : …` / `G1 : 167 · G2 : 165` ; inconnu -> `Éq. ? :` / `G? :`. Vide ailleurs."""
    mode = r.get("mode")
    if mode not in EQUIPE:
        return ""
    sc = r.get("score") or {}
    valeurs, unite = sc.get("runs") or [], sc.get("unit")
    details = r.get("runs_detail") or []
    pieces = []
    for i, v in enumerate(valeurs):
        eq = details[i].get("team") if len(details) == len(valeurs) else None
        pieces.append(f"{EQUIPE[mode]}{eq if eq else '?'} : {valeur_run(v, unite)}")
    return " · ".join(pieces)


def degats_gb(r):
    """(valeur, exact) : somme des dégâts des runs ; entier complet si tous exacts, sinon arrondi (`≈ …`) ; None si inconnu."""
    details = r.get("runs_detail") or []
    dmg = [d.get("damage") for d in details]
    if not dmg or any(d is None for d in dmg):
        return None, False
    return sum(dmg), all(d.get("damage_exact") for d in details)


def notes_propres(texte):
    """Notes de la ligne sans `boss non contrôlé` (déjà sur la page de garde si besoin)."""
    return "; ".join(n for n in (texte or "").split("; ") if n.strip() and n.strip() != "boss non contrôlé")


def joueur(r):
    nom = r.get("player") or r.get("channel") or ""
    pseudo = r.get("player_ingame")
    return f"{nom} ({pseudo})" if r.get("mode") == "bot" and pseudo else nom


def colonnes_mode(mode, nb_videos):
    cols = ["Rang", "Joueur", "Score", "Détail des runs"] + (["Dégâts"] if mode == "gb" else []) + ["Statut", "Publiée (Paris)"]
    cols += ["Vidéo"] + [f"Vidéo {i}" for i in range(2, nb_videos + 1)] + ["Notes"]
    return cols


def ligne(r, mode, nb_videos, gele=False):
    """Dictionnaire colonne -> valeur d'une ligne de classement."""
    sc = r.get("score") or {}
    total = sc.get("total")
    sur = r.get("confidence") == "sur"
    statut = "Sûr" if sur else ("Non vérifié" if gele else "À vérifier")
    d = {"Rang": r.get("rank"), "Joueur": joueur(r), "Score": total, "Détail des runs": detail_runs(r),
         "Statut": statut, "Publiée (Paris)": (r.get("published_at") or "")[:16].replace("T", " "),
         "Notes": notes_propres(r.get("notes")), "_unite": sc.get("unit"), "_sur": sur}
    if mode == "gb":
        v, exact = degats_gb(r)
        d["Dégâts"] = v if exact else (f"≈ {arrondi(v)}" if v is not None else "—")
        d["_degats_exact"] = exact
    ids = list(r.get("video_ids") or ([r["video_id"]] if r.get("video_id") else []))
    for i in range(nb_videos):
        d["Vidéo" if i == 0 else f"Vidéo {i + 1}"] = f"https://www.youtube.com/watch?v={ids[i]}" if i < len(ids) else None
    return d


def ordre(runs):
    """Classés par rang ; puis les autres triés par score (BOT : temps croissant, autres : score décroissant)."""
    def cle(r):
        sc = r.get("score") or {}
        total = sc.get("total")
        valeur = float("inf") if total is None else (total if sc.get("unit") == "seconds" else -total)
        return (r.get("rank") is None, r.get("rank") or 0, valeur, str(r.get("player") or ""))
    return sorted(runs, key=cle)


def lignes_mode(runs, mode=None, gele=False):
    """Liste de lignes (dictionnaires) dans l'ordre d'affichage (sans la ligne de séparation « À vérifier »)."""
    mode = mode or (runs[0].get("mode") if runs else "poc")
    nb = max([len(r.get("video_ids") or [1]) for r in runs] + [1])
    return [ligne(r, mode, nb, gele) for r in ordre(runs)]


# --- lecture des données ---------------------------------------------------------------------------------------------

def _json(f, defaut):
    return json.loads(Path(f).read_text(encoding="utf-8")) if Path(f).exists() else defaut


def charger(semaine, racine=RACINE):
    """{onglet: runs}. HOTM : un onglet par porte (`hotm-gate-<n>.json`, jamais `inconnue`) ; onglet `hotm` vide sans donnée."""
    dossier = Path(racine) / "data" / "runs" / semaine
    out = {}
    for mode in MODES:
        if mode == "hotm":
            portes = sorted(p for p in dossier.glob("hotm-gate-*.json") if "inconnue" not in p.stem and _json(p, []))
            for p in portes:
                out[p.stem.replace("-", " ")] = _json(p, [])
            if not portes:
                out["hotm"] = []
        else:
            out[mode] = _json(dossier / f"{mode}.json", [])
    return out


def _nom_onglet(cle):
    if cle in NOMS:
        return NOMS[cle]
    return f"HOTM · Porte {cle.rsplit(' ', 1)[-1]}" if cle.startswith("hotm gate") else cle.upper()


def _titre_feuille(cle):
    return _nom_onglet(cle).split(" · ")[0] + (" " + cle.rsplit(" ", 1)[-1] if cle.startswith("hotm gate") else "")


def _semaine_txt(semaine):
    d = date.fromisoformat(semaine)
    return f"Semaine du jeudi {d:%d/%m/%Y} 01h au jeudi {d + timedelta(days=7):%d/%m/%Y} 01h (heure de Paris)"


def _etat_semaine(meta):
    if meta.get("frozen"):
        return f"Gelée le {str(meta.get('frozen_at') or '')[:10] or '?'}"
    return "Provisoire"


def _texte_bot(semaine, racine):
    try:
        import bot_saison
        from donnees import charger_config
        pos = bot_saison.position(semaine, charger_config())
    except Exception:
        return None
    if pos is None:
        return None
    return f"Saison S{pos[1]}-{pos[2]}" if pos[0] == "jeu" else "Semaine de calcul : pas de classement"


# --- classeur --------------------------------------------------------------------------------------------------------

def exporter(semaine, sortie=None, racine=RACINE):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter as lettre
        from openpyxl.worksheet.properties import PageSetupProperties
    except ImportError:
        sys.exit("openpyxl absent : py -3 -m pip install openpyxl")
    racine = Path(racine)
    if not (racine / "data" / "runs" / semaine).exists():
        sys.exit(f"Aucun classement pour la semaine {semaine}.")
    donnees = charger(semaine, racine)
    meta = _json(racine / "data" / "runs" / semaine / "_meta.json", {})
    gele = bool(meta.get("frozen"))
    rejetees = _json(racine / "data" / "rejected" / f"{semaine}.json", [])
    chaines = {c.get("channel_id"): c.get("name") or c.get("title") for c in _json(racine / "data" / "channels.json", []) if isinstance(c, dict)}
    fond = lambda c: PatternFill("solid", fgColor=c)
    police = lambda c=TEXTE, t=11, g=False, i=False: Font(name="Segoe UI", size=t, bold=g, italic=i, color=c)
    lien = Font(name="Segoe UI", size=11, color="7DD3FC", underline="single")
    trait = Side(style="thin", color="2A3158")
    centre = Alignment(horizontal="center", vertical="center")
    wb = Workbook()
    accueil = wb.active
    accueil.title = "Shadow Ledger"

    def peindre(ws, lignes, colonnes):
        for rangee in ws.iter_rows(min_row=1, max_row=lignes, min_col=1, max_col=colonnes):
            for c in rangee:
                c.fill, c.font = fond(NUIT), police()
        ws.sheet_view.showGridLines = False

    def banniere(ws, colonnes, titre, sous):
        for r_ in (1, 2):
            ws.merge_cells(start_row=r_, start_column=1, end_row=r_, end_column=colonnes)
        ws["A1"], ws["A2"] = "⚔  SHADOW LEDGER  ·  " + titre, sous
        ws["A1"].font, ws["A2"].font = police(BLEU, 20, True), police(SOURD, 11, i=True)
        ws["A1"].alignment = ws["A2"].alignment = centre
        for c in range(1, colonnes + 1):
            ws.cell(3, c).fill = fond(VIOLET)
        ws.row_dimensions[1].height, ws.row_dimensions[2].height, ws.row_dimensions[3].height = 40, 22, 4

    def fusionne_centre(ws, r_, c1, c2, texte, f):
        ws.merge_cells(start_row=r_, start_column=c1, end_row=r_, end_column=c2)
        ws.cell(r_, c1, texte).font = f
        ws.cell(r_, c1).alignment = centre

    # --- page de garde ----------------------------------------------------------------------------------------------
    peindre(accueil, 60, 26)
    banniere(accueil, 6, "Solo Leveling: Arise", _semaine_txt(semaine))
    for i, larg in enumerate([69, 44, 14, 14, 14, 69], 1):
        accueil.column_dimensions[lettre(i)].width = larg
    r_ = 5
    fusionne_centre(accueil, r_, 2, 5, "Classements hebdomadaires", police(OR, 14, True))
    r_ += 1
    fusionne_centre(accueil, r_, 2, 5, f"{_etat_semaine(meta)}  ·  généré le {date.today():%d/%m/%Y}", police(SOURD, 10, i=True))
    if semaine in SEMAINES_ESSAI:
        r_ += 1
        fusionne_centre(accueil, r_, 2, 5, "ESSAI — non publié", police("FFFFFF", 12, True))
        for c in range(2, 6):
            accueil.cell(r_, c).fill = fond("B91C1C")
        accueil.row_dimensions[r_].height = 22
    texte_bot = _texte_bot(semaine, racine)
    if texte_bot:
        r_ += 1
        fusionne_centre(accueil, r_, 2, 5, f"BOT : {texte_bot}", police(BLEU, 11, True))
    r_ += 2
    for j, t in enumerate(["Mode", "Classées", "À vérifier", "Total"], 2):
        c = accueil.cell(r_, j, t)
        c.font, c.fill, c.alignment = police(TEXTE, 11, True), fond(ENTETE), centre
    for cle, runs in donnees.items():
        r_ += 1
        sur = sum(1 for r in runs if r.get("confidence") == "sur" and r.get("rank") is not None)
        for j, v in enumerate([_nom_onglet(cle), sur, len(runs) - sur, len(runs)], 2):
            c = accueil.cell(r_, j, v)
            c.font = police(TEXTE if j == 2 else (VERT if j == 3 else AMBRE if j == 4 else SOURD), 11, j == 2)
            c.fill, c.alignment = fond(PANNEAU if r_ % 2 else PANNEAU2), centre
    r_ += 2
    fusionne_centre(accueil, r_, 2, 5, "Légende", police(OR, 12, True))
    for txt, couleur in (("✔ Sûr : valeur contrôlée, ligne classée", VERT),
                         ("⚠ À vérifier : valeur provisoire ou non contrôlée, ligne non classée", AMBRE),
                         ("🥇🥈🥉 Podium · fond violet et liseré : Top 10 du classement", OR)):
        r_ += 1
        fusionne_centre(accueil, r_, 2, 5, txt, police(couleur, 10))
    r_ += 2
    fusionne_centre(accueil, r_, 2, 5, CREDIT, police(SOURD, 10, i=True))

    # --- un onglet par mode (ou par porte HOTM) ---------------------------------------------------------------------
    for cle, runs in donnees.items():
        mode = "hotm" if cle.startswith("hotm") else cle
        ws = wb.create_sheet(_titre_feuille(cle))
        ws.sheet_properties.tabColor = {"poc": "EF4444", "bot": BLEU, "gb": OR, "hotm": VIOLET}.get(mode, VIOLET)
        nb = max([len(r.get("video_ids") or [1]) for r in runs] + [1])
        cols = colonnes_mode(mode, nb)
        larg = [L.get(c, L["Vidéo"] if c.startswith("Vidéo") else 20) for c in cols]
        marge = max(3, (CIBLE - sum(larg)) / 2)
        n = len(cols) + 2
        lignes = lignes_mode(runs, mode, gele)
        peindre(ws, len(lignes) + 40, 30)
        banniere(ws, n, _nom_onglet(cle), _semaine_txt(semaine) + ("   ·   ESSAI — non publié" if semaine in SEMAINES_ESSAI else ""))
        ws.column_dimensions["A"].width = ws.column_dimensions[lettre(n)].width = marge
        for i, w in enumerate(larg, 2):
            ws.column_dimensions[lettre(i)].width = w
        for j, t in enumerate(cols, 2):
            c = ws.cell(5, j, t if not t.startswith("Vidéo ") else t)
            c.font, c.fill, c.alignment = police(BLEU, 11, True), fond(ENTETE), centre
            c.border = Border(bottom=Side(style="medium", color=VIOLET))
        ws.row_dimensions[5].height = 26
        k = 6
        if not lignes:
            fusionne_centre(ws, 7, 2, n - 1, "Aucune run cette semaine pour ce classement." if mode == "hotm" else "Aucune donnée cette semaine.",
                            police(SOURD, 12, i=True))
        separe = False
        classes = 0
        for d in lignes:
            if d["Rang"] is None and not separe:
                separe = True
                fusionne_centre(ws, k, 2, n - 1, "À vérifier", police(AMBRE, 12, True))
                for c in range(2, n):
                    ws.cell(k, c).fill, ws.cell(k, c).border = fond(ENTETE), Border(top=Side(style="thin", color=AMBRE))
                ws.row_dimensions[k].height = 24
                k += 1
            sur, rang = d["_sur"], d["Rang"]
            top10 = rang is not None and classes < 10
            classes += rang is not None
            for j, t in enumerate(cols, 2):
                c = ws.cell(k, j, d.get(t))
                c.fill = fond(TOP10 if top10 else (PANNEAU if k % 2 == 0 else PANNEAU2))
                c.border = Border(bottom=trait, left=Side(style="thick", color=VIOLET) if (top10 and j == 2) else None)
                c.font = police(TEXTE if sur else SOURD, 11, t in ("Rang", "Joueur", "Score") and sur, not sur)
                c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=t in ("Détail des runs", "Notes", "Joueur"))
                if t.startswith("Vidéo"):
                    if d.get(t):
                        c.hyperlink, c.value, c.font = d[t], "▶ Voir la vidéo", lien
                elif t == "Statut":
                    c.value, c.font = (("✔ Sûr", police(VERT, 11, True)) if sur
                                       else (d[t], police(AMBRE, 11, False, True)) if d[t] == "À vérifier" else (d[t], police(ROUGE, 11, False, True)))
                    if sur is False:
                        c.value = "⚠ " + d[t]
                elif t == "Score" and isinstance(c.value, (int, float)):
                    u = d["_unite"]
                    if u == "seconds":
                        c.value, c.number_format = c.value / 86400, "mm:ss.000"          # temps Excel affiché mm:ss.mmm
                    else:
                        c.number_format = '0" RC"' if u == "rage_count" else "#,##0"
                elif t == "Dégâts" and isinstance(c.value, (int, float)):
                    c.number_format = "#,##0"
            if rang in PODIUM:
                medaille, couleur = PODIUM[rang]
                ws.cell(k, 2).value = f"{medaille} {rang}"
                for j in (2, 3, 4):
                    ws.cell(k, j).font = police(couleur, 12, True)
            elif rang is None:
                ws.cell(k, 2).value = "—"
            long = max(len(str(d.get("Notes") or "")) / 58, len(str(d.get("Détail des runs") or "")) / 36, len(str(d.get("Joueur") or "")) / 24)
            ws.row_dimensions[k].height = 22 if long <= 1 else 22 + 15 * (int(long))
            k += 1
        ws.freeze_panes = "A6"
        ws.print_area = f"A1:{lettre(n)}{max(k, 8)}"
        ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)

    # --- onglet Rejetées (dernier) ----------------------------------------------------------------------------------
    ws = wb.create_sheet("Rejetées")
    ws.sheet_properties.tabColor = "6B7280"
    cols = ["Vidéo", "Chaîne", "Raison", "Détail"]
    larg = [60, 30, 22, 60]
    marge = max(3, (CIBLE - sum(larg)) / 2)
    peindre(ws, len(rejetees) + 40, 30)
    banniere(ws, len(cols) + 2, "Vidéos rejetées", _semaine_txt(semaine))
    ws.column_dimensions["A"].width = ws.column_dimensions[lettre(len(cols) + 2)].width = marge
    for i, w in enumerate(larg, 2):
        ws.column_dimensions[lettre(i)].width = w
    for j, t in enumerate(cols, 2):
        c = ws.cell(5, j, t)
        c.font, c.fill, c.alignment = police(BLEU, 11, True), fond(ENTETE), centre
        c.border = Border(bottom=Side(style="medium", color=VIOLET))
    if not rejetees:
        fusionne_centre(ws, 7, 2, 5, "Aucune vidéo rejetée.", police(SOURD, 12, i=True))
    for k, x in enumerate(rejetees, 6):
        vals = [x.get("title") or x.get("video_id"), chaines.get(x.get("channel_id")) or x.get("channel_id"), x.get("reason"), x.get("detail")]
        for j, v in enumerate(vals, 2):
            c = ws.cell(k, j, v)
            c.fill, c.border = fond(PANNEAU if k % 2 == 0 else PANNEAU2), Border(bottom=trait)
            c.font, c.alignment = police(TEXTE, 11), Alignment(vertical="center", horizontal="center", wrap_text=True)
        if x.get("video_id"):
            v = ws.cell(k, 2)
            v.hyperlink, v.font = f"https://www.youtube.com/watch?v={x['video_id']}", lien
        ws.row_dimensions[k].height = 32
    ws.freeze_panes = "A6"
    dossier = Path(sortie) if sortie else racine / "exports" / semaine
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
