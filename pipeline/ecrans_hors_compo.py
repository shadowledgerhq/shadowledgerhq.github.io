"""Écrans hors composition (SPEC_ETAPE2 v3 §1.4) : analyse du TEXTE lu par OCR (une ligne par élément lu), sans OCR ici.
Libellés dans `config.ecrans` (JA seulement, autres langues [EN ATTENTE]). Valeur illisible -> absente, jamais inventée.
Format des textes : voir `tests/test_etape2_v3.py` (textes recopiés des captures `docs/essais/composition/poc_*_ja.png`).
`integrer` rattache le résultat à `obs` (observations de `builds.observer`) ; tout est facultatif, jamais compté dans le statut."""
import json
import re

import noms

NOMBRE = r"\d[\d,.\s]*"
RE_PCT = re.compile(r"(?<![\d.,])(-?\d+(?:[.,]\d+)?)\s*%\s*(?:[(（]\s*(" + NOMBRE + r")\s*[)）])?")
RE_ENTIER = re.compile(r"(?<![\d.,])(\d{1,3}(?:[,.\s]\d{3})+|\d+)(?![\d.,]*\s*%)")
LANG = "ja"


def _n(t):
    """Sans espaces ; `カ` (katakana) ramené à `力` (kanji) : tesseract lit `攻撃力` « 攻撃カ » (essai PC du 15/11), des deux côtés."""
    return re.sub(r"\s+", "", str(t or "")).replace("　", "").replace("カ", "力")


def _lignes(texte):
    return [l.strip() for l in str(texte or "").splitlines() if l.strip()]


def entier(t):
    """`1,335` / `15.440` / `5423` -> int ; None si rien de lisible."""
    m = re.search(r"\d[\d,.\s]*", str(t or ""))
    if not m:
        return None
    s = re.sub(r"[,.\s]", "", m.group(0))
    return int(s) if s else None


def detecter(texte, cfg):
    """Clé de l'écran hors composition (`fiche_sjw`, `stats`, `statues`, `gemmes`, `subjugation`) ou None : ≥ 2 libellés lus."""
    brut = _n(texte).upper()
    meilleur, n_max = None, 1
    for cle in ("fiche_sjw", "stats", "statues", "gemmes", "subjugation"):
        libs = [_n(x).upper() for l in (cfg["ecrans"].get(cle, {}).get("libelles") or {}).values() for x in l]
        n = sum(1 for x in libs if x and x in brut)
        if cle == "subjugation" and n >= 1:
            n = 2
        if n > n_max:
            meilleur, n_max = cle, n
    return meilleur


def _valeur_stat(reste, affichage):
    """`affichage` raw -> int ; percent_with_rating -> {"percent", "rating"} (rating None si non lu)."""
    if affichage == "raw":
        v = entier(reste)
        return v
    m = RE_PCT.search(reste)
    if not m:
        return None
    pct = float(m.group(1).replace(",", "."))
    return {"percent": pct, "rating": entier(m.group(2)) if m.group(2) else None}


def _jeton_pct(ligne):
    m = RE_PCT.search(ligne)
    if not m:
        return None
    return {"percent": float(m.group(1).replace(",", ".")), "rating": entier(m.group(2)) if m.group(2) else None}


def lire_stats(texte, db, cfg):
    """Écran `stats` (onglet 全体). Retourne {"stats": {id: valeur}, "nom_lu": texte | None, "candidats": [lignes de nom],
    "positionnel": [ids lus par position]}. Les libellés sont souvent perdus par l'OCR (essai PC 15/11 : `防御`, `クリティカル`, icône
    à la place de `攻撃力`) : les stats sans libellé lu sont affectées PAR POSITION (`ecrans.stats.ordre_brut` / `ordre_pct`, [À CONFIRMER]
    sur l'ordre de l'écran) seulement si le nombre de lignes de valeur sans libellé = le nombre de stats manquantes ; sinon non lues."""
    e = cfg["ecrans"]["stats"]
    table = sorted(e["stats"][LANG].items(), key=lambda kv: -len(_n(kv[0])))      # `_n` ramène カ à 力 des deux côtés
    stats, candidats, libres_brut, libres_pct = {}, [], [], []
    for ligne in _lignes(texte):
        l = _n(ligne)
        trouve = False
        for lib, ident in table:
            i = l.find(_n(lib))
            if i < 0:
                continue
            suite = l[i + len(_n(lib)):]
            if ident == "defense" and ("貫通" in l[i:i + 8] or suite[:2] in ("中通", "貫通")):
                continue                                   # 防御力貫通 (ou sa lecture « 防御力中通 ») n'est pas la défense
            affichage = (db.get("stats", {}).get(ident) or {}).get("display", "raw")
            v = _valeur_stat(suite, affichage)
            if v is not None and ident not in stats:
                stats[ident] = v
            trouve = True
            break
        if trouve:
            continue
        if "%" in ligne or "％" in ligne:
            libres_pct.append(_jeton_pct(ligne))             # None : ligne de valeur illisible (garde sa place dans l'ordre)
        elif re.search(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d{3,7})(?![\d,]|\.\d)", ligne):
            libres_brut.append(entier(re.findall(r"(?<![\d.,])(?:\d{1,3}(?:,\d{3})+|\d{3,7})(?![\d,]|\.\d)", ligne)[-1]))
        elif not re.search(r"\d", ligne) and len(l) >= 3 and l not in {_n(x) for x in e["ignorer"]}:
            candidats.append(ligne)
    positionnel = []
    for ordre, libres in ((e.get("ordre_brut") or [], libres_brut), (e.get("ordre_pct") or [], libres_pct)):
        manquants = [i for i in ordre if i not in stats]
        if manquants and len(libres) == len(manquants):
            for ident, v in zip(manquants, libres):
                if v is not None:
                    stats[ident] = v
                    positionnel.append(ident)
    return {"stats": stats, "nom_lu": None, "candidats": candidats, "positionnel": positionnel}


def nombres_fiche(texte):
    """Entiers à séparateur de milliers de la fiche de SJW (HP, attaque, défense, puissance…) : clés d'accord avec l'écran de stats."""
    return {int(re.sub(r"\D", "", x)) for x in re.findall(r"(?<![\d,.])\d{1,3}(?:,\d{3})+(?![\d,])", str(texte or ""))}


def lire_attributs(texte, cfg):
    """Fiche de SJW : 5 attributs. La valeur est un nombre SEUL (même ligne après le libellé, ou la ligne suivante), < 100 000 :
    `Lv.170/170` ou une ligne mêlée de texte n'est jamais une valeur (essai PC du 15/11 : 170 lu à tort)."""
    table = {_n(k): v for k, v in cfg["ecrans"]["attributs"][LANG].items()}
    lignes = _lignes(texte)
    sortie = {}
    pur = lambda t: bool(re.fullmatch(r"\d{1,3}(?:[,.]\d{3})*|\d+", t.strip()))
    for i, ligne in enumerate(lignes):
        ln = _n(ligne)
        for lib, ident in table.items():
            if lib in ln and ident not in sortie:
                reste = ln.split(lib, 1)[1]
                v = entier(reste) if pur(reste) else None
                if v is None:
                    for suite in lignes[i + 1:i + 2]:
                        if pur(_n(suite)):
                            v = entier(suite)
                            break
                if v is not None and v < 100000:
                    sortie[ident] = v
    return sortie


def lire_gemmes(texte, cfg):
    """{"colors": [{"position", "color": None, "level"}], "bonuses": [{"stat", "unit", "value"}]}."""
    e = cfg["ecrans"]["gemmes"]
    lignes = _lignes(texte)
    ent_n = [_n(x) for x in e["entete_niveaux"][LANG]]
    ent_b = [_n(x) for x in e["entete_bonus"][LANG]]
    i_n = next((i for i, l in enumerate(lignes) if _n(l) in ent_n), None)
    i_b = next((i for i, l in enumerate(lignes) if i_n is not None and i > i_n and _n(l) in ent_b), None)
    niveaux = []
    if i_n is not None:
        zone = lignes[i_n + 1:i_b if i_b is not None else None]
        for l in zone:
            niveaux += [int(x) for x in re.findall(r"(?<!\d)\d{1,2}(?!\d)", l)]
    couleurs = [{"position": i + 1, "color": None, "level": v} for i, v in enumerate(niveaux[:5])]
    bonus = []
    table = {_n(k): v for k, v in e["bonus"][LANG].items()}
    for l in (lignes[i_b + 1:] if i_b is not None else []):
        ln = _n(l)
        for lib in sorted(table, key=len, reverse=True):
            if ln.startswith(lib) or lib in ln:
                stat, unite = table[lib]
                reste = ln.split(lib, 1)[1]
                m = RE_PCT.search(reste) if unite == "percent" else None
                v = float(m.group(1).replace(",", ".")) if m else (entier(reste) if unite == "flat" else None)
                if v is not None:
                    bonus.append({"stat": stat, "unit": unite, "value": v})
                break
    return {"colors": couleurs, "bonuses": bonus}


RE_GRADE = re.compile(r"^[EDCBAS]$")


def lire_statues(texte, cfg, selection=1):
    """Écran statues : 5 grades (liste de gauche) puis 3 options (grade + texte + valeur) de la statue **sélectionnée**
    (`selection`, 1 par défaut : [À CONFIRMER], l'écran ne dit pas laquelle par le texte). Options des autres statues : non vues."""
    ent = [_n(x) for x in cfg["ecrans"]["statues"]["entete_options"][LANG]]
    lignes = _lignes(texte)
    i_o = next((i for i, l in enumerate(lignes) if any(_n(l).startswith(x) for x in ent)), len(lignes))
    grades = [l for l in lignes[:i_o] if RE_GRADE.match(l)][:5]
    options, courant = [], None
    for l in lignes[i_o + 1:]:
        if RE_GRADE.match(l):
            courant = {"text_read": None, "lang": LANG, "grade": l, "id": None}
            options.append(courant)
        elif courant is not None and courant["text_read"] is None and re.search(r"[^\W\d_]", l):
            courant["text_read"] = re.sub(r"\s+", " ", l).strip()
        if len(options) == 3 and options[-1]["text_read"]:
            break
    statues = [{"position": i + 1, "grade": g, "options": []} for i, g in enumerate(grades)]
    if statues and 1 <= selection <= len(statues):
        statues[selection - 1]["options"] = options[:3]
    return statues


def integrer(obs, lectures, db, cfg):
    """`lectures` = [(ecran, texte)] d'une même run. Remplit `obs` : stats par propriétaire (nom lu -> id), `statues`, `gems`,
    stats du successeur. Retourne les notes ajoutées."""
    notes = obs.setdefault("notes", [])
    fiche = set().union(*[nombres_fiche(t) for e, t in lectures if e == "fiche_sjw"]) if lectures else set()
    vus_zone, zones_statues = [], []
    for ecran, texte in lectures:
        if ecran == "gemmes":
            g = lire_gemmes(texte, cfg)
            if g["colors"] or g["bonuses"]:
                obs["gems"] = g
        elif ecran == "statues":
            s = lire_statues(texte, cfg)
            if s and _score_statues(s) >= _score_statues(obs.get("statues")):
                obs["statues"] = s
        elif ecran == "attributs_zone":
            vus_zone.append(lire_attributs_zone(texte))
        elif ecran == "statues_zone":
            zones_statues.append(json.loads(texte))
        elif ecran == "fiche_sjw":
            attr = lire_attributs(texte, cfg)
            if attr:
                obs.setdefault("sjw", {}).setdefault("stats", {}).update(attr)
        elif ecran == "stats":
            r = lire_stats(texte, db, cfg)
            if not r["stats"]:
                continue
            ident, categorie, lu = None, None, None
            for cand in r["candidats"]:
                for cat in ("hunters", "successors"):
                    a = noms.apparier(cand, db.get(cat, {}), cfg.get("seuil_nom", noms.SEUIL_NOM))
                    if a["id"]:
                        ident, categorie, lu = a["id"], cat, cand
                        if a["methode"] == "approche":
                            notes.append(f"nom approché : {cand}")
                        break
                if ident:
                    break
            if ident is None and fiche:                    # écran sans nom lisible : SJW si ≥ 2 valeurs (HP, attaque, défense) sont celles de sa fiche
                v = r["stats"]
                accord = [k for k, x in (("hp", v.get("hp")), ("attack", v.get("attack")), ("defense", (v.get("defense") or {}).get("rating")
                                                                                              if isinstance(v.get("defense"), dict) else v.get("defense"))) if x in fiche]
                if len(accord) >= 2:
                    obs.setdefault("sjw", {}).setdefault("stats", {}).update(v)
                    notes.append(f"stats rattachées à SJW par accord avec la fiche ({', '.join(accord)})")
                    continue
            if r.get("positionnel"):
                notes.append("stats lues par position : " + ", ".join(r["positionnel"]))
            if ident is None:
                lu = max(r["candidats"], key=len) if r["candidats"] else None
                obs.setdefault("unmatched", []).append({"element": "stats", "owner": None, "slot": None, "best_id": None, "score": 0.0,
                                                       "crop": None, "text_read": lu, "stats": r["stats"]})
            elif categorie == "successors":
                obs.setdefault("successor", {}).setdefault("stats", {}).update(r["stats"])
            else:
                hs = obs.setdefault("hunters", [])
                h = next((x for x in hs if x.get("id") == ident), None)
                if h is None:
                    h = {"position": None, "id": ident, "weapon": {}, "artifacts": [], "cores": [], "stats": {}}
                    hs.append(h)
                    notes.append("chasseur trouvé par l'écran de stats")
                h.setdefault("stats", {}).update(r["stats"])
    fusionner_zones(obs, vus_zone, zones_statues, notes, cfg)
    return notes


def lire_attributs_zone(texte):
    """`id: valeur` par ligne (une zone par attribut) -> {id: int} ; valeur = nombre seul (`1,335`), < 100 000, sinon non lue."""
    sortie = {}
    for ligne in _lignes(texte):
        ident, _, v = ligne.partition(":")
        v = v.strip()
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+|\d+", v) and int(v.replace(",", "")) < 100000:
            sortie[ident.strip()] = int(v.replace(",", ""))
    return sortie


def _score_statues(statues):
    return sum(1 + len(s.get("options") or []) for s in (statues or []))


def _score_zone_statues(z, connues):
    """(grades lus, options reconnues ×3 + options non vides) : choisit la lecture la plus complète."""
    n_connues = sum(1 for o in z["options"] if any(_n(k) in _n(o) for k in connues))
    return (sum(g is not None for g in z["grades"]), 3 * n_connues + sum(bool(o) for o in z["options"]))


def fusionner_zones(obs, attributs, statues, notes, cfg=None):
    """Lectures par zone. Attributs : valeur retenue si toutes les lectures de la zone qui la voient sont d'accord (écart -> non lue, note).
    Statues : la lecture aux grades les mieux lus ; options (celles de la lecture la plus complète, `options_connues` du config pesant
    plus) rattachées à la statue SÉLECTIONNÉE seulement si la sélection est détectée."""
    connues = ((cfg or {}).get("ecrans", {}).get("statues", {}).get("options_connues") or {}).get(LANG, [])
    if attributs:
        ids = {i for a in attributs for i in a}
        fin = {}
        for i in sorted(ids):
            votes = [a[i] for a in attributs if i in a]
            pal = sorted({v: votes.count(v) for v in votes}.items(), key=lambda kv: -kv[1])
            if len(pal) == 1 or pal[0][1] > pal[1][1]:           # pluralité stricte (1 seule lecture : retenue)
                fin[i] = pal[0][0]
            else:
                notes.append(f"attribut SJW {i} : lectures de zone en désaccord {sorted(v for v, _ in pal)}")
        if fin:
            obs.setdefault("sjw", {}).setdefault("stats", {}).update(fin)
            notes.append("attributs SJW lus par zone : " + ", ".join(sorted(fin)))
    if statues:
        meilleure = max(statues, key=lambda z: _score_zone_statues(z, connues))
        if sum(g is not None for g in meilleure["grades"]) >= 3:
            liste = [{"position": i + 1, "grade": g, "options": []} for i, g in enumerate(meilleure["grades"])]
            rattachees = 0
            for sel in sorted({z["selection"] for z in statues if z.get("selection") and any(z["options"])}):   # une lecture par statue sélectionnée
                z = max((z for z in statues if z.get("selection") == sel and any(z["options"])), key=lambda z: _score_zone_statues(z, connues))
                og = z.get("options_grades") or [None] * len(z["options"])
                liste[sel - 1]["options"] = [_option(o, g, connues) for o, g in zip(z["options"], og) if o]
                if z.get("effet"):
                    liste[sel - 1]["unique_effect_text_read"] = z["effet"]
                rattachees += 1
            if not rattachees:
                notes.append("statues : options non rattachées (statue sélectionnée ou panneau d'options non vus)")
            if _score_statues(liste) >= _score_statues(obs.get("statues")):
                obs["statues"] = liste
                notes.append(f"statues lues par zone (options de {rattachees} statue(s) sur {len(liste)})")


def _option(texte, grade, connues):
    """`text_read` brut ; `label` = libellé connu retrouvé (sinon None) ; `value` = dernier nombre (`60%`, `8,000`)."""
    label = next((k for k in connues if _n(k) in _n(texte)), None)
    m = re.findall(r"\d[\d,]*(?:\.\d+)?\s*%?", texte)
    return {"text_read": texte, "lang": LANG, "grade": grade, "id": None, "label": label, "value": m[-1].replace(" ", "") if m else None}
