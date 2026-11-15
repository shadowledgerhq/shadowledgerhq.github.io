"""Écrans hors composition (SPEC_ETAPE2 v3 §1.4) : analyse du TEXTE lu par OCR (une ligne par élément lu), sans OCR ici.
Libellés dans `config.ecrans` (JA seulement, autres langues [EN ATTENTE]). Valeur illisible -> absente, jamais inventée.
Format des textes : voir `tests/test_etape2_v3.py` (textes recopiés des captures `docs/essais/composition/poc_*_ja.png`).
`integrer` rattache le résultat à `obs` (observations de `builds.observer`) ; tout est facultatif, jamais compté dans le statut."""
import re

import noms

NOMBRE = r"\d[\d,.\s]*"
RE_PCT = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%\s*(?:[(（]\s*(" + NOMBRE + r")\s*[)）])?")
RE_ENTIER = re.compile(r"(?<![\d.,])(\d{1,3}(?:[,.\s]\d{3})+|\d+)(?![\d.,]*\s*%)")
LANG = "ja"


def _n(t):
    return re.sub(r"\s+", "", str(t or "")).replace("　", "")


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


def lire_stats(texte, db, cfg):
    """Écran `stats` (onglet 全体). Retourne {"stats": {id: valeur}, "nom_lu": texte | None, "candidats": [lignes de nom]}."""
    e = cfg["ecrans"]["stats"]
    table = sorted(e["stats"][LANG].items(), key=lambda kv: -len(_n(kv[0])))
    stats, candidats = {}, []
    for ligne in _lignes(texte):
        l = _n(ligne)
        trouve = False
        for lib, ident in table:
            i = l.find(_n(lib))
            if i < 0:
                continue
            if ident == "defense" and "貫通" in l[i:i + 8]:
                continue
            affichage = (db.get("stats", {}).get(ident) or {}).get("display", "raw")
            v = _valeur_stat(l[i + len(_n(lib)):], affichage)
            if v is not None and ident not in stats:
                stats[ident] = v
            trouve = True
            break
        if not trouve and not re.search(r"\d", ligne) and len(l) >= 3 and l not in {_n(x) for x in e["ignorer"]}:
            candidats.append(ligne)
    return {"stats": stats, "nom_lu": None, "candidats": candidats}


def lire_attributs(texte, cfg):
    """Fiche de SJW : 5 attributs. La valeur suit le libellé sur la même ligne ou, sinon, sur la ligne suivante."""
    table = cfg["ecrans"]["attributs"][LANG]
    lignes = _lignes(texte)
    sortie = {}
    for i, ligne in enumerate(lignes):
        for lib, ident in table.items():
            if lib in ligne and ident not in sortie:
                v = entier(ligne.split(lib, 1)[1]) if re.search(r"\d", ligne.split(lib, 1)[1]) else None
                if v is None:
                    for suite in lignes[i + 1:i + 3]:
                        if re.fullmatch(r"[\d,.\s]+", suite):
                            v = entier(suite)
                            break
                if v is not None:
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
    for ecran, texte in lectures:
        if ecran == "gemmes":
            g = lire_gemmes(texte, cfg)
            if g["colors"] or g["bonuses"]:
                obs["gems"] = g
        elif ecran == "statues":
            s = lire_statues(texte, cfg)
            if s:
                obs["statues"] = s
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
    return notes
