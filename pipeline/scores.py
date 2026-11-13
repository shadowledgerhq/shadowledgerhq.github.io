"""Lecture des scores dans du texte (tri 1 : titre, description, sous-titres ; aussi texte OCR).

Référence : docs/SPEC_ETAPE1.md §2.2. Bibliothèque standard uniquement.

- nombres(texte)            -> scores sous forme de nombre (POC, HOTM, GB)
- chronos(texte)            -> chronos en secondes (BOT)
- candidats(texte, mode, plage) -> nombres ou chronos du mode, dans la plage plausible
- extraire(texte, mode, config) -> meilleur candidat + autres, ou None ; NON_GERE si le
                                   mode n'a pas de plage (GB [EN ATTENTE])

Chaque candidat : {"valeur": int|float, "arrondi": bool, "brut": str, "pos": int}.
`arrondi` = forme abrégée (2.1B, 131조 4497억) ou chrono sans millièmes : valeur non exacte.
"""
import re

NON_GERE = "non_gere"

_ESP = "[    ]"  # espace, insécable, fine, fine insécable
_UNITES_CJK = {"만": 10**4, "万": 10**4, "억": 10**8, "億": 10**8, "亿": 10**8,
               "조": 10**12, "兆": 10**12}
_SUFFIXES = {"k": 10**3, "m": 10**6, "b": 10**9, "bn": 10**9, "t": 10**12}
_FIN = r"(?![\d]|[.,]\d)"

_RE_NOMBRE = re.compile(
    r"(?<![A-Za-z\d.,])(?:"
    r"(?P<cjk>(?:\d+(?:[.,]\d+)*\s*[조兆억億亿만万]\s*)+\d*)"
    r"|(?P<latin>\d+(?:[.,]\d+)*\s?(?:bn|[kmbt]))(?![a-z])"
    rf"|(?P<milliers>\d{{1,3}}(?:,\d{{3}})+{_FIN}|\d{{1,3}}(?:\.\d{{3}})+{_FIN}"
    rf"|\d{{1,3}}(?:{_ESP}\d{{3}})+{_FIN})"
    r"|(?P<simple>\d+(?:[.,]\d+)?)"
    r")",
    re.IGNORECASE,
)

_RE_CHRONO = re.compile(
    r"(?<![A-Za-z\d.,:])(?:"
    r"(?P<m3>\d+)\s*(?:m|min|분|分)\s*(?P<s3>\d+)(?:[.,](?P<ms3>\d{1,3}))?\s*(?:s|sec|초|秒)"
    r"|(?:(?P<h1>\d{1,2}):)?(?P<m1>\d{1,2}):(?P<s1>\d{2})(?:[.,](?P<ms1>\d{1,3}))?(?![\d:])"
    r"|(?P<s2>\d+)(?:[.,](?P<ms2>\d{1,3}))?\s*(?:seconds?|secs?|s|초|秒)"
    r")(?![a-z])",
    re.IGNORECASE,
)

_MOIS = (r"(?:jan|feb|fev|fév|mar|apr|avr|may|mai|jun|juin|jul|juil|aug|aoû|aou|sep|oct|nov|dec|déc)"
         r"[a-zéû]*\.?")
_RE_DATES = [
    re.compile(r"(?<![\d.,])\d{4}\s?[-/.年]\s?\d{1,2}\s?[-/.月]\s?\d{1,2}日?(?!\d)"),
    re.compile(r"(?<![\d.,])\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}(?!\d)"),
    re.compile(r"(?<![\d.,])\d{1,2}/\d{1,2}(?![\d/])"),
    re.compile(r"\d{4}\s*년\s*\d{1,2}\s*월(?:\s*\d{1,2}\s*일)?"),
    re.compile(r"\d{1,2}\s*월\s*\d{1,2}\s*일"),
    re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日"),
    re.compile(rf"\b\d{{1,2}}(?:er|st|nd|rd|th)?\s+{_MOIS}(?:\s+\d{{4}})?", re.IGNORECASE),
    re.compile(rf"\b{_MOIS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s*\d{{4}})?", re.IGNORECASE),
    re.compile(r"\b\d{3,4}p\d{0,2}\b|\b[48]k\b|\b\d{2,3}\s?fps\b", re.IGNORECASE),  # 1080p, 4K, 60fps
]
# Contexte qui fait ignorer un nombre : avant (fin du texte qui précède) / après.
_AVANT_IGNORE = re.compile(
    r"(?:\blv|\bniv|\blevel|레벨|\bcp|전투력|투력|戦闘力|\bpower|\bpuissance|제|第|\bgate|\bporte"
    r"|\bseason|\bsaison|\bs|\bep|\bpart|\bvol|#|\btop|\brank)\s*[.:：]?\s*$",
    re.IGNORECASE,
)
_APRES_IGNORE = re.compile(
    r"^\s*(?:(?:cp|power|puissance)\b(?!\s*[:：]?\s*\d)|관문|関門|년|年|월|月|일|日|위|位|성|star|★|lv\b)",
    re.IGNORECASE,
)


def _normaliser(s, abrege):
    """Chaîne de chiffres et séparateurs -> nombre. `abrege` : suivi d'un suffixe (K, 억…)."""
    s = re.sub(_ESP, " ", s.strip())
    seps = re.findall(r"[^\d]", s)
    if not seps:
        return int(s)
    groupes = re.split(r"[^\d]", s)
    if len(set(seps)) == 1:
        sep = seps[0]
        milliers = all(len(g) == 3 for g in groupes[1:]) and 1 <= len(groupes[0]) <= 3
        if sep == " " or (milliers and (len(seps) >= 2 or not abrege)):
            return int("".join(groupes))
        if len(seps) == 1:
            return float(groupes[0] + "." + groupes[1])
        return None  # 1.2.3 : pas un nombre
    # Deux séparateurs différents : le dernier est décimal, les autres des milliers.
    dernier = max(s.rfind(","), s.rfind("."))
    entier = re.sub(r"[^\d]", "", s[:dernier])
    return float(entier + "." + s[dernier + 1:])


def _masquer(texte, motifs):
    for motif in motifs:
        texte = motif.sub(lambda m: " " * len(m.group(0)), texte)
    return texte


def _contexte_ignore(texte, debut, fin):
    return bool(_AVANT_IGNORE.search(texte[max(0, debut - 14):debut])
                or _APRES_IGNORE.search(texte[fin:fin + 8]))


def _valeur_cjk(brut):
    total, ordre_prec = 0, None
    for num, unite in re.findall(r"(\d+(?:[.,]\d+)*)\s*([조兆억億亿만万])", brut):
        mult = _UNITES_CJK[unite]
        if ordre_prec is not None and mult >= ordre_prec:
            return None  # unités non décroissantes : forme inconnue
        v = _normaliser(num, abrege=True)
        if v is None:
            return None
        total += v * mult
        ordre_prec = mult
    reste = re.search(r"[조兆억億亿만万]\s*(\d+)\s*$", brut)
    if reste:
        total += int(reste.group(1))
    return int(round(total))


def nombres(texte):
    """Scores sous forme de nombre (hors chronos, dates, niveaux, puissance, portes)."""
    texte = texte or ""
    propre = _masquer(texte, _RE_DATES + [_RE_CHRONO])
    res = []
    for m in _RE_NOMBRE.finditer(propre):
        brut = m.group(0).rstrip()
        debut, fin = m.start(), m.start() + len(brut)
        if _contexte_ignore(propre, debut, fin):
            continue
        if m.group("cjk"):
            v, arrondi = _valeur_cjk(brut), True
        elif m.group("latin"):
            mm = re.match(r"(.*?)\s?(bn|[kmbt])$", brut, re.IGNORECASE)
            base = _normaliser(mm.group(1), abrege=True)
            v = None if base is None else int(round(base * _SUFFIXES[mm.group(2).lower()]))
            arrondi = True
        else:
            v, arrondi = _normaliser(brut, abrege=False), False
            if isinstance(v, int) and m.group("simple") and 1900 <= v <= 2099 and len(brut) == 4:
                continue  # année
        if v is None:
            continue
        res.append({"valeur": v, "arrondi": arrondi, "brut": brut, "pos": debut})
    return res


def chronos(texte):
    """Chronos en secondes (3 décimales). `arrondi` = pas de millièmes."""
    texte = texte or ""
    propre = _masquer(texte, _RE_DATES)
    res = []
    for m in _RE_CHRONO.finditer(propre):
        g = m.groupdict()
        if g["s3"] is not None:
            h, mi, s, ms = 0, int(g["m3"]), int(g["s3"]), g["ms3"]
        elif g["s1"] is not None:
            h, mi, s, ms = int(g["h1"] or 0), int(g["m1"]), int(g["s1"]), g["ms1"]
        else:
            h, mi, s, ms = 0, 0, int(g["s2"]), g["ms2"]
        if (g["s1"] is not None or g["s3"] is not None) and s >= 60:
            continue
        frac = int(ms.ljust(3, "0")) / 1000 if ms else 0.0
        valeur = round(h * 3600 + mi * 60 + s + frac, 3)
        res.append({"valeur": valeur, "arrondi": not ms or len(ms) < 3,
                    "brut": m.group(0).strip(), "pos": m.start()})
    return res


def plage(mode, config):
    """(min, max) plausible du mode, ou None si non géré."""
    p = (config.get("plausible") or {}).get(mode)
    return tuple(p) if p else None


def candidats(texte, mode, plage_mode):
    trouves = chronos(texte) if mode == "bot" else nombres(texte)
    lo, hi = plage_mode
    return [c for c in trouves if lo <= c["valeur"] <= hi]


def choisir(cands, mode):
    """(meilleur, autres) : le plus fort, ou le plus court au BOT. Doublons de valeur fusionnés."""
    if not cands:
        return None, []
    vus, uniques = set(), []
    for c in cands:
        if c["valeur"] not in vus:
            vus.add(c["valeur"])
            uniques.append(c)
    tri = sorted(uniques, key=lambda c: c["valeur"], reverse=(mode != "bot"))
    return tri[0], tri[1:]


def extraire(texte, mode, config):
    """Meilleur score provisoire du texte pour le mode.
    Retourne NON_GERE (mode sans plage), None (rien) ou
    {"valeur", "arrondi", "brut", "autres": [bruts]}."""
    p = plage(mode, config)
    if p is None:
        return NON_GERE
    meilleur, autres = choisir(candidats(texte, mode, p), mode)
    if meilleur is None:
        return None
    return {**meilleur, "autres": [a["brut"] for a in autres]}
