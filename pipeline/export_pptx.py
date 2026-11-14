"""PowerPoint des builds du top 10 (docs/SPEC_ETAPE2.md §3). Un fichier par vidéo du top 10 et par langue :
`exports/<semaine>/builds/<mode>/<rang:02>-<video_id>-fr.pptx` et `-en.pptx`. Charte = `export_excel.py` (constantes
importées, pas recopiées). Gratuit : `py -3 -m pip install python-pptx`.

    python3 pipeline/export_pptx.py [AAAA-MM-JJ] [--mode poc|bot|gb|hotm] [--sortie DOSSIER]
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import builds as B
import export_excel as X
import sjw as sjw_mod

RACINE = B.RACINE
LANGUES = ("fr", "en")
COULEUR_MODE = {"poc": "EF4444", "bot": X.BLEU, "gb": X.OR, "hotm": X.VIOLET}
COULEUR_STATUT = {"build_complet": X.VERT, "build_partiel": X.AMBRE, "pas_de_build": X.ROUGE}
FICHE_VIDE = "—"
W, H = 13.333, 7.5
BOITE = 1.1
PAS_Y = 1.5          # hauteur d'une rangée d'icônes (icône + nom sur 2 lignes)


def _import_pptx():
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.dml import MSO_LINE
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
        from pptx.util import Inches, Pt
    except ImportError:
        sys.exit("python-pptx absent : py -3 -m pip install python-pptx")
    return locals()


# --- noms (jamais de traduction faite par le code, §3.3) ---------------------------------------------------------------

def nom_affiche(db, categorie, ident, lang):
    """(texte, italique). `name.<lang>` ; si le FR est vide : EN en italique + `(EN)` ; si tout est vide : l'id en italique."""
    if not ident:
        return "", False
    obj = (db.get(categorie) or {}).get(ident) or {}
    n = obj.get("name") or {}
    if n.get(lang):
        return n[lang], False
    if lang == "fr" and n.get("en"):
        return f"{n['en']} (EN)", True
    return ident, True


def nom_piece(db, set_id, slot, lang):
    if not set_id:
        return "", False
    s = (db.get("artifact_sets") or {}).get(set_id) or {}
    for p in s.get("pieces") or []:
        if p.get("slot") == slot and (p.get("name") or {}).get(lang):
            return p["name"][lang], False
    return nom_affiche(db, "artifact_sets", set_id, lang)


def chemin_icone(db, categorie, ident, racine, slot=None):
    if not ident:
        return None
    if categorie == "artifact_pieces":
        c = Path(racine) / "data" / "icons" / "artifact_pieces" / f"{ident}--{slot}.png"
    else:
        ic = ((db.get(categorie) or {}).get(ident) or {}).get("icon")
        c = Path(racine) / ic if ic else None
    return c if c and c.exists() else None


def lib(cfg, cle, lang):
    return (cfg["libelles"].get(cle) or {}).get(lang) or cle


def t_utile(b):
    tc = b.get("t_composition")
    return tc[0] if tc else None


def score_texte(row):
    sc = (row or {}).get("score") or {}
    if sc.get("total") is None:
        return "—"
    v = X.valeur_run(sc["total"], sc.get("unit"))
    return v + (" RC" if sc.get("unit") == "rage_count" else "")


def date_semaine(week, lang):
    d = date.fromisoformat(week)
    return f"{d:%d/%m/%Y}" if lang == "fr" else d.isoformat()


# --- dessin ------------------------------------------------------------------------------------------------------------

class Dessin:
    def __init__(self, racine, db, cfg, lang):
        self.m = _import_pptx()
        self.racine, self.db, self.cfg, self.lang = racine, db, cfg, lang
        self.prs = self.m["Presentation"]()
        self.prs.slide_width, self.prs.slide_height = self.m["Inches"](W), self.m["Inches"](H)

    def rgb(self, h):
        return self.m["RGBColor"].from_string(h)

    def rect(self, s, x, y, w, h, fond=None, bord=None, pointille=False, arrondi=False, epaisseur=1.0):
        m = self.m
        forme = s.shapes.add_shape(m["MSO_SHAPE"].ROUNDED_RECTANGLE if arrondi else m["MSO_SHAPE"].RECTANGLE,
                                   m["Inches"](x), m["Inches"](y), m["Inches"](w), m["Inches"](h))
        if arrondi:
            forme.adjustments[0] = 0.08
        if fond:
            forme.fill.solid()
            forme.fill.fore_color.rgb = self.rgb(fond)
        else:
            forme.fill.background()
        if bord:
            forme.line.color.rgb = self.rgb(bord)
            forme.line.width = m["Pt"](epaisseur)
            if pointille:
                forme.line.dash_style = m["MSO_LINE"].DASH
        else:
            forme.line.fill.background()
        forme.shadow.inherit = False
        return forme

    def texte(self, s, x, y, w, h, txt, taille=12, couleur=X.TEXTE, gras=False, italique=False, align="l", ancre="t", lien=None):
        m = self.m
        tb = s.shapes.add_textbox(m["Inches"](x), m["Inches"](y), m["Inches"](w), m["Inches"](h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = {"t": m["MSO_ANCHOR"].TOP, "m": m["MSO_ANCHOR"].MIDDLE, "b": m["MSO_ANCHOR"].BOTTOM}[ancre]
        lignes = str(txt).split("\n")
        for i, ligne in enumerate(lignes):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = {"l": m["PP_ALIGN"].LEFT, "c": m["PP_ALIGN"].CENTER, "r": m["PP_ALIGN"].RIGHT}[align]
            r = p.add_run()
            r.text = ligne
            r.font.name, r.font.size, r.font.bold, r.font.italic = "Segoe UI", m["Pt"](taille), gras, italique
            r.font.color.rgb = self.rgb(couleur)
        if lien:
            tb.click_action.hyperlink.address = lien
        return tb

    def diapo(self, titre, b, row, notes=""):
        """Slide vide + fond nuit + bandeau haut + pied (§3.3)."""
        m = self.m
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = self.rgb(X.NUIT)
        self.rect(s, 0, 0, W, 0.9, X.ENTETE)
        self.rect(s, 0, 0.84, W, 0.06, COULEUR_MODE.get(b["mode"], X.VIOLET))
        mode = b["mode"].upper()
        self.texte(s, 0.4, 0.2, 8.5, 0.5, f"{mode} · #{b.get('rank')} · {b.get('player') or ''}", 14, X.TEXTE, ancre="m")
        self.texte(s, 8.9, 0.2, 4.0, 0.5, f"{lib(self.cfg, 'semaine', self.lang)} {date_semaine(b['week'], self.lang)}", 12, X.SOURD, align="r", ancre="m")
        self.texte(s, 0.5, 1.0, 12.3, 0.6, titre, 28, X.BLEU, gras=True)
        t = t_utile(b)
        src = f"{lib(self.cfg, 'video', self.lang)} : {(row or {}).get('channel') or b.get('player') or ''} — youtu.be/{b.get('video_id')}" + (f"?t={t}" if t else "")
        self.texte(s, 0.4, 6.95, 6.6, 0.4, src, 11, X.SOURD, ancre="m")
        self.texte(s, 7.1, 6.95, 5.8, 0.4, lib(self.cfg, "pied", self.lang), 11, X.SOURD, align="r", ancre="m")
        if b["week"] in X.SEMAINES_ESSAI:
            self.rect(s, 9.6, 1.05, 3.3, 0.45, "B91C1C")
            self.texte(s, 9.6, 1.05, 3.3, 0.45, lib(self.cfg, "essai", self.lang), 12, "FFFFFF", gras=True, align="c", ancre="m")
        s.notes_slide.notes_text_frame.text = notes
        return s

    def case(self, s, x, y, nom, icone=None, etat=None, niveau=None, italique=False, label_etat=None, taille=BOITE):
        """Icône carrée de `taille` in sur panneau arrondi + nom dessous ; `etat` : None, "non_trouve", "non_gere", "inconnue"."""
        self.rect(s, x, y, taille, taille, X.PANNEAU2 if not etat else None, X.SOURD if etat else "2A3158", pointille=bool(etat), arrondi=True)
        if etat:
            lab = lib(self.cfg, {"non_trouve": "non_trouve", "non_gere": "non_gere", "inconnue": "icone_inconnue"}[etat], self.lang)
            self.texte(s, x + 0.05, y + 0.05, taille - 0.1, taille - 0.1, lab, 9, X.SOURD, italique=True, align="c", ancre="m")
        elif icone:
            marge = 0.08
            s.shapes.add_picture(str(icone), self.m["Inches"](x + marge), self.m["Inches"](y + marge),
                                 self.m["Inches"](taille - 2 * marge), self.m["Inches"](taille - 2 * marge))
        elif nom:
            self.texte(s, x + 0.05, y + 0.05, taille - 0.1, taille - 0.1, "?", 20, X.SOURD, align="c", ancre="m")
        if niveau is not None:
            self.rect(s, x + taille - 0.5, y + taille - 0.28, 0.5, 0.26, X.VIOLET, arrondi=True)
            self.texte(s, x + taille - 0.5, y + taille - 0.28, 0.5, 0.26, str(niveau), 10, "FFFFFF", gras=True, align="c", ancre="m")
        if nom:
            self.texte(s, x - 0.12, y + taille + 0.04, taille + 0.24, 0.3, nom, 9, X.SOURD if italique else X.TEXTE, italique=italique, align="c")

    def sauver(self, chemin):
        Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(chemin))


# --- contenus de slides --------------------------------------------------------------------------------------------------

def _est_inconnue(b, element, owner, slot=None):
    return any(u.get("element") == element and u.get("owner") == owner and (slot is None or u.get("slot") == slot) for u in b.get("unmatched") or [])


def _notes(b, extra=""):
    t = b.get("t_composition")
    n = [f"build {b['run_id']}-{b['run_index']} · statut {b['status']} · confiance {b['confidence']}",
         f"horodatages : composition {t}, RESULT {b.get('t_result')}"]
    if b.get("unmatched"):
        n.append("non reconnues : " + "; ".join(f"{u['element']}/{u.get('owner')}/{u.get('slot')} → {u.get('best_id')} ({u.get('score')})" for u in b["unmatched"]))
    if b.get("notes"):
        n.append("notes : " + b["notes"])
    if extra:
        n.append(extra)
    return "\n".join(n)


def _artefacts(d, s, b, pieces, owner, x0, y0, element, pas_x=BOITE + 0.28):
    for i, a in enumerate(pieces):
        x, y = x0 + (i % 4) * pas_x, y0 + (i // 4) * PAS_Y
        if a.get("set_id"):
            nom, it = nom_piece(d.db, a["set_id"], a["slot"], d.lang)
            d.case(s, x, y, nom, chemin_icone(d.db, "artifact_pieces", a["set_id"], d.racine, a["slot"]), None, a.get("level"), it)
        elif a.get("empty"):
            d.case(s, x, y, "", None, None)
            d.texte(s, x, y + 0.45, BOITE, 0.3, FICHE_VIDE, 16, X.SOURD, align="c")
        else:
            d.case(s, x, y, "", None, "inconnue" if _est_inconnue(b, element, owner, a["slot"]) else "non_trouve")


def _noyaux(d, s, b, noyaux, owner, x0, y0, element):
    for i, c in enumerate(noyaux):
        x = x0 + i * (BOITE + 0.28)
        if c.get("id"):
            nom, it = nom_affiche(d.db, "cores", c["id"], d.lang)
            d.case(s, x, y0, nom, chemin_icone(d.db, "cores", c["id"], d.racine), None, f"Lv {c['level']}" if c.get("level") else None, it)
        else:
            d.case(s, x, y0, "", None, "inconnue" if _est_inconnue(b, element, owner, c["slot"]) else "non_trouve")


def _bonus(d, s, b, cle, x, y, largeur=5.6):
    lignes = []
    for sb in (b.get("set_bonuses") or {}).get(cle) or []:
        nom, _ = nom_affiche(d.db, "artifact_sets", sb["set_id"], d.lang)
        lignes.append(f"{nom} ×{sb['pieces']}" + (f" ({'/'.join(map(str, sb['tiers']))})" if sb.get("tiers") else ""))
    d.texte(s, x, y, largeur, 0.4, f"{lib(d.cfg, 'bonus_sets', d.lang)} : " + (" · ".join(lignes) if lignes else FICHE_VIDE), 11, X.SOURD)


def _fmt_stat(v):
    if isinstance(v, dict):
        pct = f"{v['percent']:.1f}".replace(".", ",").rstrip("0").rstrip(",") if v.get("percent") is not None else "?"
        r = f" ({X.entier(v['rating'])})" if v.get("rating") is not None else ""
        return f"{pct} %{r}"
    return X.entier(v) if isinstance(v, (int, float)) else FICHE_VIDE


def _stats(d, s, stats, x, y, pas=2.35):
    """Tableau 2 colonnes : stats | attributs (valeurs comme à l'écran). Stat non lue : `—`."""
    liste = sorted((st for st in d.db.get("stats", {}).values() if st.get("required")), key=lambda st: (st.get("category") != "stat", st.get("order", 0)))
    for col, (cat, titre) in enumerate((("stat", "stats"), ("attribute", "attributs"))):
        cx = x + col * pas
        d.texte(s, cx, y, 2.2, 0.3, lib(d.cfg, titre, d.lang), 12, X.BLEU, gras=True)
        for i, st in enumerate(st for st in liste if st.get("category") == cat):
            nom, it = nom_affiche(d.db, "stats", st["id"], d.lang)
            ligne_y = y + 0.38 + i * 0.4
            d.rect(s, cx, ligne_y, pas - 0.1, 0.36, X.PANNEAU if i % 2 else X.PANNEAU2)
            d.texte(s, cx + 0.06, ligne_y, pas - 1.15, 0.36, nom, 9, X.SOURD if it else X.TEXTE, italique=it, ancre="m")
            d.texte(s, cx + pas - 1.1, ligne_y, 0.95, 0.36, _fmt_stat((stats or {}).get(st["id"])), 9, X.TEXTE, align="r", ancre="m")


def slide_titre(d, b, row):
    cfg, lang = d.cfg, d.lang
    s = d.diapo(f"{X.NOMS.get(b['mode'], b['mode'])} — {lib(cfg, 'titre_build', lang)}", b, row, _notes(b))
    rang = b.get("rank") or 0
    couleur = {1: X.OR, 2: X.ARGENT, 3: X.BRONZE}.get(rang, X.VIOLET)
    d.rect(s, 0.6, 2.0, 1.4, 1.4, couleur, arrondi=True)
    d.texte(s, 0.6, 2.0, 1.4, 1.4, f"#{rang}", 36, X.NUIT, gras=True, align="c", ancre="m")
    l = [f"{lib(cfg, 'joueur', lang)} : {b.get('player') or ''}", f"{lib(cfg, 'score', lang)} : {score_texte(row)}"]
    if b["mode"] in ("poc", "gb"):
        l.append(f"{lib(cfg, 'run', lang)} {b['run_index']}/{max(1, len((row or {}).get('runs_detail') or [1]))} · "
                 f"{lib(cfg, 'equipe' if b['mode'] == 'poc' else 'groupe', lang)} {b.get('team') or '?'}")
    if b["mode"] == "hotm":
        sj = {False: "avec_sjw", True: "sans_sjw"}.get(b.get("hunter_mode"))
        l.append(f"{lib(cfg, 'porte', lang)} {b.get('gate') if b.get('gate') is not None else '?'}" + (f" · {lib(cfg, sj, lang)}" if sj else ""))
    d.texte(s, 2.4, 2.0, 8.0, 1.8, "\n".join(l), 20, X.TEXTE)
    d.rect(s, 2.4, 4.0, 3.6, 0.5, COULEUR_STATUT[b["status"]], arrondi=True)
    d.texte(s, 2.4, 4.0, 3.6, 0.5, lib(cfg, "statut_" + b["status"], lang), 16, X.NUIT, gras=True, align="c", ancre="m")
    t = t_utile(b)
    url = f"https://youtu.be/{b.get('video_id')}" + (f"?t={t}" if t else "")
    d.texte(s, 2.4, 4.8, 9.0, 0.4, url, 14, "7DD3FC", lien=url)
    return s


def slide_sjw(d, b, row):
    s = d.diapo(lib(d.cfg, "sjw", d.lang), b, row, _notes(b))
    sj = b.get("sjw")
    d.texte(s, 0.5, 1.65, 3, 0.3, lib(d.cfg, "armes", d.lang), 12, X.BLEU, gras=True)
    for i in range(2):
        w = ((sj or {}).get("weapons") or [{}, {}])[i]
        x = 0.5 + i * 1.5
        if w.get("id"):
            nom, it = nom_affiche(d.db, "weapons", w["id"], d.lang)
            d.case(s, x, 2.0, nom, chemin_icone(d.db, "weapons", w["id"], d.racine), None, w.get("level"), it)
        else:
            d.case(s, x, 2.0, "", None, "inconnue" if _est_inconnue(b, "sjw_weapons", "sjw") else "non_trouve")
    d.texte(s, 3.6, 1.65, 5, 0.3, lib(d.cfg, "artefacts", d.lang), 12, X.BLEU, gras=True)
    pieces = (sj or {}).get("artifacts") or [{"slot": c, "set_id": None} for c in B.SLOTS_ARTEFACT]
    _artefacts(d, s, b, pieces, "sjw", 3.6, 2.0, "sjw_artifacts", pas_x=1.3)
    _bonus(d, s, b, "sjw", 4.5, 5.1, 4.3)
    d.texte(s, 0.5, 4.3, 3, 0.3, lib(d.cfg, "noyaux", d.lang), 12, X.BLEU, gras=True)
    _noyaux(d, s, b, (sj or {}).get("cores") or [{"slot": c, "id": None} for c in B.SLOTS_NOYAU], "sjw", 0.5, 4.65, "sjw_cores")
    _stats(d, s, (sj or {}).get("stats"), 9.0, 1.65, pas=2.0)
    return s


def slide_chasseur(d, b, row, h):
    nom, it = nom_affiche(d.db, "hunters", h.get("id"), d.lang)
    entete = f"{lib(d.cfg, 'chasseur', d.lang)} {h['team_slot'] or h['position']}"
    s = d.diapo(entete + (f" — {nom}" if nom else ""), b, row, _notes(b))
    owner = f"hunter_{h['position']}"
    obj = d.db.get("hunters", {}).get(h.get("id")) or {}
    if h.get("id"):
        d.case(s, 0.5, 2.0, nom, chemin_icone(d.db, "hunters", h["id"], d.racine), None, None, it, taille=1.5)
        d.texte(s, 0.5, 3.85, 2.2, 0.6, " · ".join(x for x in (obj.get("element"), obj.get("role")) if x), 11, X.SOURD)
    else:
        d.case(s, 0.5, 2.0, "", None, "inconnue" if _est_inconnue(b, "hunters", owner) else "non_trouve", taille=1.5)
    d.texte(s, 0.5, 4.5, 2, 0.3, lib(d.cfg, "arme", d.lang), 12, X.BLEU, gras=True)
    w = h.get("weapon") or {}
    if w.get("id"):
        n2, i2 = nom_affiche(d.db, "weapons", w["id"], d.lang)
        d.case(s, 0.5, 4.85, n2, chemin_icone(d.db, "weapons", w["id"], d.racine), None, w.get("level"), i2)
    else:
        d.case(s, 0.5, 4.85, "", None, "inconnue" if _est_inconnue(b, "weapons", owner) else "non_trouve")
    d.texte(s, 3.0, 1.65, 5, 0.3, lib(d.cfg, "artefacts", d.lang), 12, X.BLEU, gras=True)
    _artefacts(d, s, b, h["artifacts"], owner, 3.0, 1.95, "artifacts")
    _bonus(d, s, b, owner, 3.0, 4.95)
    d.texte(s, 3.0, 5.25, 3, 0.3, lib(d.cfg, "noyaux", d.lang), 12, X.BLEU, gras=True)
    _noyaux(d, s, b, h["cores"], owner, 3.0, 5.5, "cores")
    _stats(d, s, h.get("stats"), 8.7, 1.65)
    return s


def slide_ombres(d, b, row):
    s = d.diapo(lib(d.cfg, "ombres", d.lang), b, row, _notes(b))
    for i, o in enumerate(b["shadows"]):
        x = 2.2 + i * 3.0
        d.texte(s, x, 1.9, BOITE * 1.5, 0.3, f"{i + 1:02d}", 14, X.OR, gras=True, align="c")
        if o.get("id"):
            nom, it = nom_affiche(d.db, "shadows", o["id"], d.lang)
            d.case(s, x, 2.3, nom, chemin_icone(d.db, "shadows", o["id"], d.racine), None, None, it, taille=1.5)
        else:
            d.case(s, x, 2.3, "", None, "inconnue" if _est_inconnue(b, "shadows", "shadows") else "non_trouve", taille=1.5)
    return s


def slide_successeur(d, b, row):
    s = d.diapo(lib(d.cfg, "successeur", d.lang), b, row, _notes(b))
    su = b["successor"]
    if su.get("id"):
        nom, it = nom_affiche(d.db, "successors", su["id"], d.lang)
        d.case(s, 5.9, 2.3, nom, chemin_icone(d.db, "successors", su["id"], d.racine), None, su.get("level"), it, taille=1.5)
    else:
        d.case(s, 5.9, 2.3, "", None, "inconnue" if _est_inconnue(b, "successor", "successor") else "non_trouve", taille=1.5)
    return s


def _grille(d, s, b, items, cols, x0, y0, categorie, element, plus=True):
    for i, (ident, niveau, slot) in enumerate(items):
        x, y = x0 + (i % cols) * (BOITE + 0.7), y0 + (i // cols) * (BOITE + 0.7)
        if ident:
            nom, it = nom_affiche(d.db, categorie, ident, d.lang)
            d.case(s, x, y, nom, chemin_icone(d.db, categorie, ident, d.racine), None, (f"+{niveau}" if plus else f"Lv {niveau}") if niveau is not None else None, it)
        else:
            d.case(s, x, y, "", None, "inconnue" if _est_inconnue(b, element, "sjw", slot) else "non_trouve")


def slide_competences(d, b, row):
    s = d.diapo(lib(d.cfg, "competences", d.lang), b, row, _notes(b))
    par_slot = {c["slot"]: c for c in ((b.get("sjw") or {}).get("skills") or [])}
    for r, slots in enumerate(sjw_mod.GRILLE_SLIDE):
        items = [((par_slot.get(sl) or {}).get("id"), (par_slot.get(sl) or {}).get("level"), sl) for sl in slots]
        _grille(d, s, b, items, 3, 3.3, 2.0 + r * 2.2, "sjw_skills", "sjw_skills")
    return s


def slide_benedictions(d, b, row):
    s = d.diapo(lib(d.cfg, "benedictions", d.lang), b, row, _notes(b))
    bl = (b.get("sjw") or {}).get("blessings") or [{}] * sjw_mod.NB_BLESSINGS
    _grille(d, s, b, [(x.get("id"), x.get("level"), None) for x in bl], 4, 2.3, 1.8, "blessings", "blessings")
    return s


def slide_subjugation(d, b, row):
    s = d.diapo(lib(d.cfg, "subjugation", d.lang), b, row, _notes(b))
    for i, ident in enumerate(b.get("subjugation_support") or [None] * 3):
        x = 3.0 + i * 2.5
        d.texte(s, x, 1.9, BOITE, 0.3, f"{i + 1}", 14, X.OR, gras=True, align="c")
        if ident:
            nom, it = nom_affiche(d.db, "subjugation_support", ident, d.lang)
            d.case(s, x, 2.3, nom, chemin_icone(d.db, "subjugation_support", ident, d.racine), None, None, it)
        else:
            d.case(s, x, 2.3, "", None, "non_trouve")
    return s


def slide_preuve(d, b, row):
    s = d.diapo(lib(d.cfg, "preuve", d.lang), b, row, _notes(b))
    p = b.get("proof") or {}
    d.texte(s, 0.6, 1.8, 6, 0.5, f"{lib(d.cfg, 'niveau_preuve', d.lang)} : {p.get('level') if p.get('level') is not None else '?'}", 20, X.OR, gras=True)
    d.texte(s, 0.6, 2.5, 6, 0.3, lib(d.cfg, "handicaps", d.lang), 12, X.BLEU, gras=True)
    for i, m in enumerate(p.get("modifiers") or []):
        o = d.db.get("proof_modifiers", {}).get((m or {}).get("id")) or {}
        nom, it = nom_affiche(d.db, "proof_modifiers", (m or {}).get("id"), d.lang)
        y = 2.9 + i * 0.42
        d.rect(s, 0.6, y, 12.0, 0.38, X.PANNEAU if i % 2 else X.PANNEAU2)
        d.texte(s, 0.7, y, 8.2, 0.38, nom, 11, X.SOURD if it else X.TEXTE, italique=it, ancre="m")
        mx = o.get("max_level")
        d.texte(s, 9.0, y, 1.8, 0.38, f"{m.get('level')}/{mx if mx is not None else '?'}", 11, X.TEXTE, align="c", ancre="m")
        cout = (o.get("cost_per_level") or 0) * (m.get("level") or 0) if o.get("cost_per_level") is not None else None
        d.texte(s, 10.8, y, 1.7, 0.38, f"{lib(d.cfg, 'cout', d.lang)} {cout if cout is not None else '?'}", 11, X.TEXTE, align="r", ancre="m")
    return s


def slide_sources(d, buildsf, row):
    b = buildsf[0]
    cfg, lang = d.cfg, d.lang
    s = d.diapo(lib(cfg, "sources", lang), b, row, "Slide Sources (spec 1).")
    patches = sorted(d.db_patches, key=lambda p: p.get("date") or "")
    version = patches[-1].get("version") if patches else "?"
    credit = ""
    cr = Path(d.racine) / "data" / "icons" / "CREDITS.md"
    if cr.exists():
        credit = " ".join(ligne.strip("- ").replace("**", "") for ligne in cr.read_text(encoding="utf-8").splitlines()[:3] if ligne.strip() and not ligne.startswith("#"))[:300]
    ts = "; ".join(str(x.get("t_composition")) for x in buildsf if x.get("t_composition")) or "—"
    pub = ((row or {}).get("published_at") or "")[:10]
    lignes = [
        f"{lib(cfg, 'video', lang)} : {(row or {}).get('channel') or b.get('player')} — youtu.be/{b.get('video_id')} — {lib(cfg, 'publiee', lang)} {pub}",
        f"{lib(cfg, 'horodatages', lang)} : {ts}",
        f"{lib(cfg, 'donnees_jeu', lang)} : data/db (Shadow Ledger) — slagate.com (Sohoven), wiki Fandom (CC BY-SA), forum Netmarble · {lib(cfg, 'version_jeu', lang)} {version}",
        f"{lib(cfg, 'credits_icones', lang)} : {credit}",
        lib(cfg, "mention", lang),
        f"{lib(cfg, 'genere', lang)} {date.today():%d/%m/%Y} · spec 1",
    ]
    d.texte(s, 0.6, 1.8, 12.0, 4.8, "\n\n".join(lignes), 13, X.TEXTE)
    return s


def slides_build(d, b, row):
    """Les slides d'un build, dans l'ordre du §3.2. Sans objet -> pas de slide ; attendu non trouvé -> slide avec cases d'état."""
    att = b.get("attendus") or {}
    sjw_ok = bool(b.get("sjw")) or "sjw" in att
    slide_titre(d, b, row)
    if sjw_ok:
        slide_sjw(d, b, row)
    for h in b["hunters"]:
        slide_chasseur(d, b, row, h)
    if att.get("shadows") or any(o.get("id") for o in b["shadows"]):
        slide_ombres(d, b, row)
    if att.get("successor") or b["successor"].get("id"):
        slide_successeur(d, b, row)
    if sjw_ok and ("sjw_skills" in att or any(c.get("id") for c in (b.get("sjw") or {}).get("skills") or [])):
        slide_competences(d, b, row)
    if sjw_ok and ("blessings" in att or any(x.get("id") for x in (b.get("sjw") or {}).get("blessings") or [])):
        slide_benedictions(d, b, row)
    if b.get("found", {}).get("subjugation_support"):
        slide_subjugation(d, b, row)
    if b.get("found", {}).get("proof"):
        slide_preuve(d, b, row)


def generer_fichier(buildsf, row, lang, chemin, racine=RACINE, db=None, cfg=None):
    """Un fichier = les builds d'une même vidéo (1 ou 2 runs) + une seule slide Sources."""
    cfg = cfg or B.charger_config()
    db = db or B.charger_db(racine)
    d = Dessin(racine, db, cfg, lang)
    d.db_patches = list((db.get("patches") or {}).values()) if db.get("patches") else B._json(Path(racine) / "data" / "db" / "patches.json", [])
    for b in sorted(buildsf, key=lambda x: x["run_index"]):
        slides_build(d, b, row)
    slide_sources(d, sorted(buildsf, key=lambda x: x["run_index"]), row)
    d.sauver(chemin)
    return len(d.prs.slides)


def exporter(semaine, racine=RACINE, sortie=None, mode=None, cfg=None):
    racine = Path(racine)
    sortie = Path(sortie) if sortie else racine / "exports" / semaine / "builds"
    cfg = cfg or B.charger_config()
    db = B.charger_db(racine)
    toutes = []
    for f in sorted((racine / "data" / "builds" / semaine).glob("*/*.json")):
        b = B._json(f, None)
        if b and not f.name.startswith("_") and (mode is None or b["mode"] == mode):
            toutes.append(b)
    lignes = {}
    for f in (racine / "data" / "runs" / semaine).glob("*.json"):
        for r in B._json(f, []):
            if isinstance(r, dict) and r.get("run_id"):
                lignes[r["run_id"]] = r
    groupes = defaultdict(list)
    for b in toutes:
        groupes[(b.get("dossier") or b["mode"], b.get("rank") or 0, b.get("video_id"))].append(b)
    fichiers = []
    for (dossier, rang, vid), liste in sorted(groupes.items()):
        row = lignes.get(liste[0]["run_id"])
        for lang in LANGUES:
            chemin = sortie / dossier / f"{rang:02d}-{vid}-{lang}.pptx"
            generer_fichier(liste, row, lang, chemin, racine, db, cfg)
            fichiers.append(str(chemin.relative_to(sortie.parent.parent.parent)) if chemin.is_relative_to(racine) else str(chemin))
    B.ecrire_rapport(semaine, toutes, racine, fichiers)
    return fichiers


def main(argv=None):
    ap = argparse.ArgumentParser(description="PowerPoint des builds (SPEC_ETAPE2 §3)")
    ap.add_argument("semaine", nargs="?")
    ap.add_argument("--mode", choices=("poc", "bot", "gb", "hotm"))
    ap.add_argument("--sortie")
    a = ap.parse_args(argv)
    from semaine import id_semaine, maintenant
    semaine = a.semaine or id_semaine(maintenant())
    f = exporter(semaine, sortie=a.sortie, mode=a.mode)
    print(f"{len(f)} fichier(s) PowerPoint pour {semaine}.")


if __name__ == "__main__":
    main()
