#!/usr/bin/env python3
"""Images du post X du mercredi (docs/reseaux/RESEAUX.md §5). Ne publie rien : fichiers seulement.

    python3 pipeline/post_x.py [AAAA-MM-JJ]   # semaine = jeudi de début ; défaut : semaine courante

Lit data/runs/<semaine>/ (poc, bot, gb, hotm-gate-<n>), ne garde que `confidence: sur` avec `rank` 1 à 3 (« — » sinon),
remplit docs/reseaux/gabarit-x-mode.svg et écrit dans exports/<semaine>/x/ : poc.png, bot.png, gb.png, hotm.png (1600x900,
`rsvg-convert`, ou cairosvg à défaut, ou le .svg seul si aucun des deux), texte.txt (FR/EN), alt.txt (texte alternatif).
HOTM = une image à 3 colonnes (une par porte)."""
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from donnees import Donnees, RACINE
from export_excel import arrondi, entier
from semaine import id_semaine, maintenant

GABARIT = Path(RACINE) / "docs" / "reseaux" / "gabarit-x-mode.svg"
SITE = "shadowledgerhq.github.io"
MODES = {  # clé -> (sigle, nom complet, critère FR, critère EN)
    "poc": ("POC", "Power Of Calamity", "Rank Score", "Rank Score"),
    "bot": ("BOT", "Battlefield Of Time", "chrono le plus court", "fastest time"),
    "gb": ("GB", "Guild Boss", "Rage Count (RC)", "Rage Count (RC)"),
    "hotm": ("HOTM", "Hall Of The Monarchs", "points par porte", "points per gate"),
}
MOIS_FR = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
MOIS_EN = "January February March April May June July August September October November December".split()
NOM_MAX = 28
NB_PORTES = 3


def date_fr(j):
    return f"{j.day} {MOIS_FR[j.month - 1]} {j.year}"


def date_en(j):
    return f"{MOIS_EN[j.month - 1]} {j.day}, {j.year}"


def temps(s):
    ms = int(round(s * 1000))
    return f"{ms // 60000}:{ms % 60000 // 1000:02d}.{ms % 1000:03d}"


def score_txt(ligne, mode):
    sc = ligne["score"]
    v, unite = sc["total"], sc.get("unit")
    if mode == "bot" or unite == "seconds":
        return temps(v)
    if mode == "gb":
        return f"{v:.0f} RC"
    if mode == "hotm":
        return f"{entier(v)} pts"
    return entier(v) if unite == "rank_score" else arrondi(v)


def nom_txt(ligne, max_car=NOM_MAX):
    n = " ".join(str(ligne.get("channel") or ligne.get("player") or "?").split())
    return n if len(n) <= max_car else n[:max_car - 1].rstrip() + "…"


def top3(lignes):
    """Lignes `sur` de rang 1 à 3 (ex aequo conservés), dans l'ordre du classement ; au plus 3."""
    sures = [l for l in lignes if l.get("confidence") == "sur" and isinstance(l.get("rank"), int) and 1 <= l["rank"] <= 3]
    return sorted(sures, key=lambda l: l["rank"])[:3]


def charger(d, semaine, mode):
    return d.lire(f"runs/{semaine}/{mode}.json", [])


def portes(d, semaine):
    """{n: top3} pour les portes 1..NB_PORTES (fichiers hotm-gate-<n>.json présents)."""
    return {n: top3(charger(d, semaine, f"hotm-gate-{n}")) for n in range(1, NB_PORTES + 1)}


def statut(meta, court=False):
    """Pied d'image (court : tient sur la ligne du gabarit) ou texte du post (long)."""
    if (meta or {}).get("frozen"):
        return "Classement définitif", "Final ranking"
    if court:
        return "Quasi définitif", "Near-final"
    return "Quasi définitif, reset jeudi 01h (Paris)", "Final at Thursday reset"


def remplir(svg, champs):
    if champs.get("critere_fr") == champs.get("critere_en"):  # un seul critère si FR = EN
        svg = svg.replace("{{critere_fr}} / {{critere_en}}", "{{critere_fr}}")
    for k, v in champs.items():
        svg = svg.replace("{{" + k + "}}", escape(str(v)))
    return svg


def champs_communs(mode, semaine, meta):
    sigle, nom, cfr, cen = MODES[mode]
    j = date.fromisoformat(semaine)
    sfr, sen = statut(meta, court=True)
    return {"semaine_fr": f"Semaine du {date_fr(j)}", "semaine_en": f"Week of {date_en(j)}", "mode": sigle, "mode_nom": nom,
            "critere_fr": cfr, "critere_en": cen, "statut_fr": sfr, "statut_en": sen, "site": SITE}


def svg_mode(gabarit, mode, lignes, semaine, meta):
    """Image POC / BOT / GB : gabarit rempli. Moins de 3 lignes sûres -> « — » (rang d'emplacement conservé)."""
    champs = champs_communs(mode, semaine, meta)
    rangs = []
    for i in range(3):
        l = lignes[i] if i < len(lignes) else None
        champs[f"p{i + 1}"] = nom_txt(l) if l else "—"
        champs[f"s{i + 1}"] = score_txt(l, mode) if l else ""
        rangs.append(l["rank"] if l else i + 1)
    svg = remplir(gabarit, champs)
    for y, r in zip((450, 580, 710), rangs):  # numéros de rang (ex aequo : 1, 1, 3)
        svg = re.sub(rf'(<text x="80" y="{y}"[^>]*>)\d(</text>)', rf"\g<1>{r}\2", svg)
    return svg


def svg_hotm(gabarit, par_porte, semaine, meta):
    """Image HOTM : en-tête et pied du gabarit, 3 colonnes (une par porte) à la place des 3 lignes."""
    debut = gabarit.index('<g font-size="52"')
    fin = gabarit.index("</g>", debut) + len("</g>")
    champs = champs_communs("hotm", semaine, meta)
    larg, ecart, x0 = 460, 30, 80
    cols = []
    for k, n in enumerate(sorted(par_porte)):
        x = x0 + k * (larg + ecart)
        lignes = par_porte[n]
        cols.append(f'<rect x="{x}" y="360" width="{larg}" height="385" rx="16" fill="#EDEBFF" fill-opacity=".05"/>'
                    f'<text x="{x + 24}" y="410" fill="#4FD1FF" font-size="36" font-weight="700">Gate {n}</text>')
        for i in range(3):
            l = lignes[i] if i < len(lignes) else None
            y = 480 + i * 100
            rang = l["rank"] if l else i + 1
            cols.append(f'<text x="{x + 24}" y="{y}" font-size="40" font-weight="800" fill="#EDEBFF" fill-opacity="{[.95, .8, .6][i]}">{rang}</text>'
                        f'<text x="{x + 70}" y="{y}" font-size="30" fill="#EDEBFF">{escape(nom_txt(l, 20) if l else "—")}</text>'
                        f'<text x="{x + 70}" y="{y + 38}" font-size="26" font-weight="700" fill="#4FD1FF">{escape(score_txt(l, "hotm") if l else "")}</text>')
    return remplir(gabarit[:debut] + "<g>" + "".join(cols) + "</g>" + gabarit[fin:], champs)


def alt_mode(mode, lignes, semaine):
    sigle = MODES[mode][0]
    j = date_fr(date.fromisoformat(semaine))
    morceaux = [f"{l['rank']} {nom_txt(l)} {score_txt(l, mode)}" for l in lignes] or ["aucune ligne sûre"]
    return f"{sigle} top 3, semaine du {j} : " + ", ".join(morceaux)


def alt_hotm(par_porte, semaine):
    j = date_fr(date.fromisoformat(semaine))
    parts = []
    for n in sorted(par_porte):
        ls = par_porte[n]
        parts.append(f"porte {n} : " + (", ".join(f"{l['rank']} {nom_txt(l)} {score_txt(l, 'hotm')}" for l in ls) or "aucune ligne sûre"))
    return f"HOTM top 3 par porte, semaine du {j} : " + " ; ".join(parts)


TEXTE = """🏆 Classement de la semaine · Weekly ranking — Solo Leveling: Arise
Top 3 POC · BOT · GB · HOTM 👇
{statut_fr} · {statut_en}
Complet / Full: {site}
#SoloLevelingArise
"""


def rendre(svg_path, png_path):
    """SVG -> PNG 1600x900 : rsvg-convert, sinon cairosvg, sinon rien (retourne False)."""
    exe = shutil.which("rsvg-convert")
    if exe:
        subprocess.run([exe, "-w", "1600", "-h", "900", "-o", str(png_path), str(svg_path)], check=True)
        return True
    try:
        import cairosvg
    except ImportError:
        return False
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1600, output_height=900)
    return True


def generer(semaine, d=None, sortie=None):
    d = d or Donnees()
    sortie = Path(sortie) if sortie else d.data.parent / "exports" / semaine / "x"
    sortie.mkdir(parents=True, exist_ok=True)
    meta = d.meta(semaine) or {}
    gabarit = GABARIT.read_text(encoding="utf-8")
    images, alts = {}, []
    for mode in ("poc", "bot", "gb"):
        lignes = top3(charger(d, semaine, mode))
        images[mode] = svg_mode(gabarit, mode, lignes, semaine, meta)
        alts.append((mode, alt_mode(mode, lignes, semaine)))
    par_porte = portes(d, semaine)
    images["hotm"] = svg_hotm(gabarit, par_porte, semaine, meta)
    alts.append(("hotm", alt_hotm(par_porte, semaine)))
    rendus = []
    for mode, svg in images.items():
        p = sortie / f"{mode}.svg"
        p.write_text(svg, encoding="utf-8")
        if rendre(p, sortie / f"{mode}.png"):
            p.unlink()
            rendus.append(f"{mode}.png")
        else:
            rendus.append(f"{mode}.svg (aucun moteur SVG : installer librsvg2-bin)")
    sfr, sen = statut(meta)
    (sortie / "texte.txt").write_text(TEXTE.format(statut_fr=sfr, statut_en=sen, site=SITE), encoding="utf-8")
    (sortie / "alt.txt").write_text("\n".join(f"{m}.png : {t}" for m, t in alts) + "\n", encoding="utf-8")
    return sortie, rendus


if __name__ == "__main__":
    semaine = sys.argv[1] if len(sys.argv) > 1 else id_semaine(maintenant())
    dossier, rendus = generer(semaine)
    print(f"{semaine} -> {dossier} : " + ", ".join(rendus) + ", texte.txt, alt.txt")
