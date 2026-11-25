"""SPEC v40 : écran Results du POC refonte (« Power of Calamity Tier N Team M »).

Lecture ANCRÉE sur les libellés : la mise en page de l'écran suit la HAUTEUR de la vidéo (cartes de 394 unités de large, quel que
soit le format ; marge gauche variable selon l'appareil), des fractions fixes ne tiennent donc pas. Les mots de l'image entière
(`outils.boites`) donnent les ancres : les 3 ou 4 libellés « … Contribution » (Player, [Successor], Hunter, Total) et la ligne
« Team 1 / Team 2 » du bas ; chaque valeur est ensuite lue dans une zone calculée à partir de l'ancre (unité = largeur du mot
« Contribution » / 134, échelle de référence 900 px de haut), sous plusieurs prétraitements. Les contrôles (a)(b)(c) de la SPEC
départagent les variantes d'OCR et décident du `sûr`.

`outils` : `dimensions(png)`, `boites(png)`, `recadrer_px(png, x, y, largeur, hauteur, echelle, seuil)`, `ocr(png, langues, psm, timeout, extra)`
(`pc.Outils`)."""
import re
import statistics
from itertools import product
from pathlib import Path

REF_CONTRIBUTION = 134.0           # largeur du mot « Contribution » à 900 px de haut
VARIANTES = ((3, 140), (3, 170), (3, None))                      # 1er étage (contributions)
VARIANTES_PLUS = ((4, 120), (3, 100), (3, 190), (3, 210), (2, 150), (3, 160, True), (3, 200, True))   # 2e étage si un contrôle échoue
VARIANTES_BAS = VARIANTES + VARIANTES_PLUS + ((2, None), (2, 130), (2, 170))      # bloc du bas : tous (les petits chiffres préfèrent l'échelle 2)
CHIFFRES = ["-c", "tessedit_char_whitelist=0123456789,."]
CHIFFRES_POURCENT = ["-c", "tessedit_char_whitelist=0123456789,.%"]
CHIFFRES_TEMPS = ["-c", "tessedit_char_whitelist=0123456789:"]
TOLERANCE_RANK = 100               # contrôle (a)
TOLERANCE_POURCENT = 0.05          # contrôle (b)
NOTE_PREFIXE = "contrôle POC palier : "
_STRICT = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d{3})*(?![\d.,])")
_TITRE = re.compile(r"t[il1]er\s*(\d{1,2})\s*team\s*([12])", re.IGNORECASE)


def detecter(texte):
    """Écran de palier (client anglais) : ≥ 2 libellés « Contribution » (OCR abîmé toléré) et un signal propre au mode."""
    b = re.sub(r"[^a-z]", "", (texte or "").lower())
    return b.count("contribut") >= 2 and any(k in b for k in ("tier", "goalprog", "ranksc", "calam"))


# --- lecture des valeurs -----------------------------------------------------------------------

def nombres(texte):
    """Nombres à groupes de milliers stricts (`6,177,875,929,148`, `0`) lus dans un texte, dans l'ordre."""
    sortie = []
    for m in _STRICT.finditer((texte or "").replace(" ", "")):
        sortie.append(int(re.sub(r"[.,]", "", m.group(0))))
    return sortie


def pourcentage(texte):
    """Premier pourcentage du texte (`39.02%`, `39,02`) ; `3902%` (point perdu) est rétabli. None si absent ou > 100."""
    t = (texte or "").replace(" ", "")
    m = re.search(r"(\d{1,3})[.,](\d{1,2})", t)
    if m:
        v = float(f"{m.group(1)}.{m.group(2)}")
    else:
        m = re.search(r"(\d{3,5})%?", t)
        if not m:
            return None
        ch = m.group(1)
        v = float(f"{ch[:-2]}.{ch[-2:]}")
    return v if 0 <= v <= 100 else None


def _lire_zone(outils, png, x, y, largeur, hauteur, extra, psm=7, variantes=VARIANTES, langues="eng", timeout=40):
    """Textes d'une zone (pixels) sous chaque prétraitement ; "" si une lecture échoue."""
    textes = []
    for echelle, seuil, *reste in variantes:
        try:
            petit = outils.recadrer_px(png, x, y, largeur, hauteur, echelle, seuil, bool(reste and reste[0]))
            textes.append(outils.ocr(petit, langues, psm, timeout, extra) or "")
            Path(petit).unlink(missing_ok=True)
        except Exception:      # OcrTropLent, RuntimeError : lecture perdue, jamais bloquante
            textes.append("")
    return textes


def _candidats(valeurs, maximum=2):
    """Valeurs distinctes lues (non None), les plus fréquentes d'abord."""
    vus = {}
    for v in valeurs:
        if v is not None:
            vus[v] = vus.get(v, 0) + 1
    return [v for v, _ in sorted(vus.items(), key=lambda kv: -kv[1])][:maximum]


# --- ancres ---------------------------------------------------------------------------------------

# Décalage vertical (unités de référence) des libellés de la colonne gauche par rapport à « Player Contribution », selon la mise en page.
DECALAGES = {"successeur": {"player": 0, "successor": 124, "hunter": 245, "total": 565},
             "standard": {"player": 0, "hunter": 125, "total": 442}}
_ROLES = (("player", re.compile(r"(?i)^pla[yv]")), ("successor", re.compile(r"(?i)^succ")), ("hunter", re.compile(r"(?i)^hunt")),
          ("total", re.compile(r"(?i)^tota")))
LARGEUR_ROLE = {"player": 65.0, "successor": 102.0, "hunter": 74.0, "total": 52.0}      # largeur du mot à l'échelle de référence


def repere(mots, largeur_img):
    """(mise en page, x gauche, y de « Player Contribution », unité) d'après les libellés de la colonne gauche, ou None.
    Les mots Player / Successor / Hunter / Total et les « Contribution » (sans nom) donnent chacun un y de « Player » implicite
    dans chaque mise en page ; la mise en page retenue est celle où ces y concordent le mieux (≥ 2 libellés)."""
    gauche = [m for m in mots if m[1] < 0.6 * largeur_img]
    nommes = []
    for m in gauche:
        for role, rx in _ROLES:
            if rx.match(m[0]):
                nommes.append((role, m))
                break
    contribs = [m for m in gauche if m[0].lower().startswith(("contri", "contr1"))]
    echelles = [m[3] / REF_CONTRIBUTION for m in contribs if m[0].lower().startswith("contribution")] + \
               [m[3] / LARGEUR_ROLE[r] for r, m in nommes]
    if not echelles:
        return None
    u = max(0.3, statistics.median(echelles))
    meilleur = None
    for nom, decal in DECALAGES.items():
        if nom == "standard" and any(r == "successor" for r, _ in nommes):
            continue
        implicites = [m[2] - decal[r] * u for r, m in nommes if r in decal]
        if not implicites:
            continue
        ref = statistics.median(implicites)
        # « Contribution » sans nom : rattaché au rôle le plus proche de sa hauteur dans cette mise en page
        extra = []
        for m in contribs:
            if any(abs(m[2] - n[2]) < 10 * u and abs(m[1] - n[1]) < 160 * u for _, n in nommes):
                continue
            plus_proche = min(decal.items(), key=lambda kv: abs(ref + kv[1] * u - m[2]))
            if abs(ref + plus_proche[1] * u - m[2]) < 22 * u:
                extra.append(m[2] - plus_proche[1] * u)
        tous = implicites + extra
        if len(tous) < 2:
            continue
        ecart = statistics.pstdev(tous)
        if meilleur is None or ecart < meilleur[0] - 1e-6 or (abs(ecart - meilleur[0]) < 1e-6 and nom == "successeur"):
            meilleur = (ecart, nom, statistics.median(tous))
    if meilleur is None or meilleur[0] > 14 * u:
        return None
    _, nom, y_p = meilleur
    lefts = [m[1] for _, m in nommes]
    x_l = statistics.median(lefts) if lefts else min(m[1] for m in contribs) - 72 * u
    return nom, x_l, y_p, u


def _ligne_team(mots, hauteur_image):
    """(mots Team, y de la ligne) lus sur la ligne du bas, ou None. Team 2 est à 249 unités de Team 1 ; un seul mot lu suffit."""
    c = [m for m in mots if re.fullmatch(r"(?i)team\s*[12]?", m[0]) and m[2] > 0.55 * hauteur_image]
    if not c:
        return None
    c.sort(key=lambda m: m[1])
    return c, statistics.median(m[2] for m in c)


def _un_nombre(textes, elargi=False):
    """Candidats d'une zone : les chiffres de chaque lecture (séparateurs mal lus ignorés : les contrôles (a)(c) valident) ; `elargi` :
    aussi sans 1 à 3 chiffres parasites en tête (portrait, cadre)."""
    sortie = []
    for t in textes:
        for ligne in (t or "").splitlines():
            ch = re.sub(r"\D", "", ligne)
            if not 1 <= len(ch) <= 16:
                continue
            sortie.append(int(ch))
            if elargi:
                sortie += [int(ch[c:]) for c in (1, 2, 3) if len(ch) > c + 3]
    return sortie


# --- lecture d'une image ------------------------------------------------------------------------

def lire(outils, png, texte=None):
    """Valeurs de l'écran de palier : dict (None = illisible) ; {} si les libellés ne sont pas trouvés. Ne décide rien : `controles`."""
    taille = outils.dimensions(png)
    if not taille:
        return {}
    largeur_img, hauteur_img = taille
    mots = outils.boites(png)
    r = repere(mots, largeur_img)
    if not r:
        return {}
    layout, x_l, y_p, u = r
    dec = DECALAGES[layout]
    successeur = layout == "successeur"
    y_total, y_chasseur = y_p + dec["total"] * u, y_p + dec["hunter"] * u
    e = {"layout": layout, "echelle": round(u, 3)}
    # titre : « Tier N Team M » (le titre peut être plus à gauche que la colonne des cartes)
    tit = _lire_zone(outils, png, x_l - 160 * u, y_p - 70 * u, 660 * u, 62 * u, None, psm=7, variantes=((3, None), (3, 140)))
    tit.append(texte or "")
    paires = [(int(m.group(1)), int(m.group(2))) for t in tit for m in [_TITRE.search(t)] if m]
    pal = _candidats(paires, 1)
    e["tier"], e["team"] = (pal[0] if pal else (None, None))
    # lignes de contributions : joueur, [successeur], chasseurs 1 à 3
    lignes = [("player", y_p + 40 * u)]
    if successeur:
        lignes.append(("successor", y_p + dec["successor"] * u + 40 * u))
    lignes += [(f"hunter_{k}", y_chasseur + (44 + 68.5 * (k - 1)) * u) for k in (1, 2, 3)]
    zones = {nom: (x_l + 193 * u, y - 2 * u, 195 * u, 62 * u, CHIFFRES) for nom, y in lignes}
    zones["total"] = (x_l - 4 * u, y_total + 25 * u, 345 * u, 75 * u, CHIFFRES)
    lt = _ligne_team(mots, hauteur_img)           # bloc du bas : Rank Score, Goal Progress, Team 1 %, Team 2 %
    if lt:
        c, y_team = lt
        x1 = next((m[1] for m in c if m[0].lower().endswith("1")), None)
        x2 = next((m[1] for m in c if m[0].lower().endswith("2")), None)
        if x1 is None and x2 is not None:
            x1 = x2 - 249 * u
        if x1 is None:                       # « Team » seul : le plus à gauche est Team 1
            x1 = c[0][1]
        if x2 is None:
            x2 = x1 + 249 * u
        top = y_team - 122 * u
        zones["rank_score"] = (x1 - 50 * u, top, 265 * u, 70 * u, CHIFFRES)
        zones["goal"] = (x1 + 265 * u, top, 185 * u, 70 * u, CHIFFRES_POURCENT)
        zones["t1"] = (x1 + 82 * u, y_team - 12 * u, 95 * u, 40 * u, CHIFFRES_POURCENT)
        zones["t2"] = (x2 + 82 * u, y_team - 12 * u, 95 * u, 40 * u, CHIFFRES_POURCENT)
    pt = next((m for m in mots if m[0].lower() == "time" and m[2] < 0.2 * hauteur_img), None)
    if pt:                                   # temps de jeu : à droite du mot « Time » (mm:ss, secondes < 60)
        zones["play_time"] = (pt[1] + pt[3] + 5 * u, pt[2] - 8 * u, 150 * u, 38 * u, CHIFFRES_TEMPS)
    brut = {nom: [] for nom in zones}
    noms_contrib = [n for n in zones if n in ("player", "successor", "hunter_1", "hunter_2", "hunter_3", "total")]

    def calculer(elargi):
        cand = {n: _candidats(_un_nombre(brut[n], elargi=elargi), 8) for n in noms_contrib}
        if "rank_score" in zones:
            cand["rank_score"] = _candidats(_un_nombre(brut["rank_score"]), 8)
            for k in ("goal", "t1", "t2"):
                cand[k] = _candidats([pourcentage(t) for t in brut[k]], 4)
        horloges = []
        for t in brut.get("play_time", []):
            m = re.search(r"(\d{1,2}):(\d{2})(?!\d)", t)
            if m and int(m.group(2)) < 60:
                horloges.append(f"{int(m.group(1)):02d}:{m.group(2)}")
        e["play_time"] = (_candidats(horloges, 1) or [None])[0]
        e.update(_choisir(cand, successeur, e.get("tier")))
        e["_candidats"] = cand
        return controles(e)[0]

    # 1er étage, 2e étage (plus de prétraitements) : chiffres tels que lus ; 3e étage : sans 1 à 3 chiffres de tête (portrait, cadre),
    # jamais `sûr` (une somme fausse mais cohérente est possible : `via_expansion` fait échouer le contrôle c)
    BAS = ("rank_score", "goal")        # Rank Score et objectif : toujours tous les prétraitements (t1, t2 : par étage) (un chiffre mal lu reste cohérent : 48,79 / 48,75)
    for k, etage in enumerate((VARIANTES, VARIANTES_PLUS)):
        for nom, (x, y, w, h, extra) in zones.items():
            if nom in BAS:
                if k == 0:
                    brut[nom] += _lire_zone(outils, png, x, y, w, h, extra, variantes=VARIANTES_BAS)
                continue
            brut[nom] += _lire_zone(outils, png, x, y, w, h, extra, variantes=etage)
        if calculer(False):
            return e
    e["via_expansion"] = False
    if not calculer(True):
        e["via_expansion"] = False
        return e
    e["via_expansion"] = True            # passe les contrôles seulement grâce aux chiffres de tête écartés : écran sans score
    return e


def _choisir(cand, successeur, tier=None):
    """Combinaison de candidats qui passe le contrôle (c) (somme des contributions = total), sinon la plus votée ; Rank Score, objectif et
    équipes : combinaison qui passe (b) puis (a) (palier lu), sinon la plus votée."""
    noms = ["player"] + (["successor"] if successeur else []) + ["hunter_1", "hunter_2", "hunter_3"]
    listes = [cand.get(n) or [None] for n in noms]
    totaux = cand.get("total") or [None]
    choix = None
    for combo in product(*listes):
        if None in combo:
            continue
        for t in totaux:
            if t is not None and sum(combo) == t:
                choix = (combo, t)
                break
        if choix:
            break
    if choix is None:
        choix = (tuple(l[0] if l else None for l in listes), totaux[0] if totaux else None)
    combo, total = choix
    r = dict(zip(noms, combo))
    sortie = {"player": r["player"], "successor": r.get("successor"), "successeur_present": successeur,
              "hunters": [r["hunter_1"], r["hunter_2"], r["hunter_3"]], "total_contribution": total}
    rangs, buts, t1s, t2s = (cand.get(k) or [None] for k in ("rank_score", "goal", "t1", "t2"))
    pris = None
    for exige_a in (True, False):
        meilleurs = []
        for rk, g, a, b in product(rangs, buts, t1s, t2s):
            if None in (rk, g, a, b) or abs(g - (a + b)) > TOLERANCE_POURCENT + 1e-9:
                continue
            ecart_a = abs(rk - 1_000_000 * (tier - 1 + g / 100)) if tier is not None else None
            if exige_a and (ecart_a is None or ecart_a > TOLERANCE_RANK):
                continue
            meilleurs.append((round(abs(g - (a + b)), 4), ecart_a if ecart_a is not None else 0, (rk, g, a, b)))
        if meilleurs:
            pris = min(meilleurs, key=lambda m: m[:2])[2]       # lecture la plus cohérente d'abord (écart (b), puis (a))
            break
    if pris is None:
        pris = (rangs[0], buts[0], t1s[0], t2s[0])
    sortie["rank_score"], sortie["goal_progress"], sortie["team_pct"] = pris[0], pris[1], [pris[2], pris[3]]
    return sortie


# --- contrôles (SPEC v40 §3) -----------------------------------------------------------------------

def controles(e):
    """(ok, notes) : (a) |Rank Score − 1e6 × (Tier − 1 + Goal % / 100)| ≤ 100 ; (b) |Goal % − (Team 1 % + Team 2 %)| ≤ 0,05 ;
    (c) Player + Successor + Hunter 1 + 2 + 3 = Total Contribution. Une valeur illisible fait échouer le contrôle concerné."""
    notes = []
    tier, rank, goal, pct = e.get("tier"), e.get("rank_score"), e.get("goal_progress"), e.get("team_pct") or [None, None]
    if None in (tier, rank, goal):
        notes.append(NOTE_PREFIXE + "a : palier, Rank Score ou Goal Progress illisible")
    else:
        attendu = 1_000_000 * (tier - 1 + goal / 100)
        if abs(rank - attendu) > TOLERANCE_RANK:
            notes.append(NOTE_PREFIXE + f"a : Rank Score {rank} ≠ {int(round(attendu))} (palier {tier}, {goal} %)")
    if None in (goal, *pct):
        notes.append(NOTE_PREFIXE + "b : Goal Progress ou pourcentage d'équipe illisible")
    elif abs(goal - (pct[0] + pct[1])) > TOLERANCE_POURCENT + 1e-9:
        notes.append(NOTE_PREFIXE + f"b : Goal Progress {goal} % ≠ Team 1 {pct[0]} % + Team 2 {pct[1]} %")
    parts = [e.get("player"), *( [e.get("successor")] if e.get("successeur_present") else [] ), *(e.get("hunters") or [None, None, None])]
    total = e.get("total_contribution")
    if total is None or None in parts or len(parts) < 4:
        notes.append(NOTE_PREFIXE + "c : contribution illisible")
    elif sum(parts) != total:
        notes.append(NOTE_PREFIXE + f"c : somme {sum(parts)} ≠ Total Contribution {total}")
    if e.get("via_expansion"):
        notes.append(NOTE_PREFIXE + "c : chiffres de tête écartés pour passer le contrôle (lecture non fiable)")
    if e.get("team") not in (1, 2):
        notes.append(NOTE_PREFIXE + "équipe illisible")
    return not notes, notes


# --- texte (titre, description, sous-titres) : SPEC v40 §4 ------------------------------------------------

_PALIER_MOTS = r"(?:tier|palier|단계|\bt)"
_CLEAR = re.compile(rf"(?:{_PALIER_MOTS}\s*[-:#]?\s*(\d{{1,2}})\s*(?:clear(?:ed)?|terminé|완료|クリア)|clear(?:ed)?\s*(?:the\s*)?{_PALIER_MOTS}\s*[-:#]?\s*(\d{{1,2}}))", re.IGNORECASE)
_PALIER = re.compile(rf"(?<![a-z0-9]){_PALIER_MOTS}\s*[-:#]?\s*(\d{{1,2}})(?!\d)", re.IGNORECASE)
_RANK_TEXTE = re.compile(r"rank\s*score\D{0,12}(\d{1,3}(?:[.,]\d{3}){2}|\d{7,8})(?!\d)", re.IGNORECASE)
NOTE_PALIER_TITRE = "palier du titre : rang prudent"
NOTE_PALIER_CLEAR = "palier du titre : clear"
NOTE_DEGATS_INFO = "dégâts du texte : information"
UNITE_RANK_SCORE = 1_000_000


def lecture_texte(meta, textes, config, lecture_vide, notes_reset=()):
    """POC refonte : lecture provisoire (`a_verifier`, `exact: false`) d'après le texte, ou None. Ordre : `Rank Score` écrit (7-8 chiffres) >
    « Tier N clear » (N × 1e6) > « Tier N » / « T N » / « palier N » / « 단계 N » (borne basse (N − 1) × 1e6, la plus haute des mentions,
    note « palier du titre : rang prudent »). Un nombre de dégâts n'est plus un score : note « dégâts du texte : information » seulement
    (jamais seul : sans palier ni Rank Score, aucune lecture). [À VÉRIFIER : mots coréen et japonais]"""
    from scores import extraire
    info = False
    for source, texte in textes:
        t = texte or ""
        if config.get("plausible", {}).get("poc") and extraire(t, "poc", config, source) not in (None, False, {}, []):
            info = True
        trouve = None
        m = _RANK_TEXTE.search(t)
        if m:
            v = int(re.sub(r"[.,]", "", m.group(1)))
            if 1_000_000 <= v < 100_000_000:
                trouve = (v, "rank_score", f"Rank Score du texte : {m.group(1)}", None)
        if trouve is None:
            n = [int(a or b) for a, b in _CLEAR.findall(t)]
            if n:
                trouve = (max(n) * UNITE_RANK_SCORE, "clear", NOTE_PALIER_CLEAR, max(n))
        if trouve is None:
            n = [int(x) for x in _PALIER.findall(t) if 1 <= int(x) <= 99]
            if n:
                trouve = ((max(n) - 1) * UNITE_RANK_SCORE, "palier", NOTE_PALIER_TITRE, max(n))
        if trouve:
            lec = lecture_vide(meta, "poc")
            lec["notes"] += list(notes_reset)
            lec.update(score=trouve[0], score_source=source, regles=config.get("tri1_version"), exact=False, confidence="a_verifier",
                       detail={"poc_texte": trouve[1], "palier": trouve[3]})
            lec["notes"].append(trouve[2])
            if info:
                lec["notes"].append(NOTE_DEGATS_INFO)
            return lec
    return None


def semaine_refonte(meta, config):
    """Vrai si la vidéo (date de publication) appartient à une semaine de la refonte du POC (`poc_refonte.semaine_debut`)."""
    from semaine import semaine_de
    debut = ((config or {}).get("poc_refonte") or {}).get("semaine_debut")
    return bool(debut and meta.get("published_at") and semaine_de(meta["published_at"]) >= debut)
