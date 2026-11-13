"""Lecture de l'écran de composition HOTM : porte affichée et titre du mode.

Entrée : texte OCR (zone « bas gauche » pour la porte, zone « haut » pour le titre).
Sortie : champs ajoutés au JSON de la run, HOTM seulement :
  "gate": {"number": 1, "points": 94600} ou None
  "hunter_mode": False (avec Sung Jin Woo) | True (sans Sung Jin Woo) | None

Référence : docs/REFERENCE_ECRANS_HOTM.md. Aucune dépendance (bibliothèque standard).
Un champ non lisible vaut None, jamais une valeur devinée : la run passe alors en
confidence « a_verifier » (voir hotm_champs_ecran).
"""
import re

# Titres : (motif, hunter_mode). Seules les variantes coréenne et japonaise ont été
# vues sur capture (13/11/2026) ; les autres langues sont des hypothèses non vérifiées.
_TITRES = [
    (r"플레이어\s*모드", False),                # coréen, avec SJW (vu)
    (r"ハンター\s*モード", True),               # japonais, sans SJW (vu)
    (r"プレイヤー\s*モード", False),            # japonais, avec SJW (hypothèse)
    (r"헌터\s*모드", True),                     # coréen, sans SJW (hypothèse)
    (r"\bplayer\s*mode\b", False),              # anglais (hypothèse)
    (r"\bhunter\s*mode\b", True),               # anglais (hypothèse)
]

# Porte : 제 1관문 (ko), 第1関門 (ja), « Gate 1 » (en, hypothèse).
_PORTE = re.compile(
    r"(?:제\s*(\d)\s*관문|第\s*(\d)\s*[関関]|\bgate\s*(\d)\b)", re.IGNORECASE
)
# Points : « 94 600pt », « 94,600 pt », « 94.600PT » (espaces fines/insécables acceptées).
_POINTS = re.compile(r"(\d{1,3}(?:[\s  ,.]\d{3})+|\d+)\s*pt\b", re.IGNORECASE)


def _entier(s):
    return int(re.sub(r"\D", "", s))


def lire_mode(texte):
    """True = sans SJW (ハンターモード), False = avec SJW (플레이어 모드), None = illisible.
    Titres contradictoires dans le même texte : None."""
    trouves = {val for motif, val in _TITRES if re.search(motif, texte or "", re.IGNORECASE)}
    return trouves.pop() if len(trouves) == 1 else None


def lire_porte(texte):
    """{"number": n, "points": p|None} ou None. Les points sont ceux qui suivent la porte."""
    m = _PORTE.search(texte or "")
    if not m:
        return None
    numero = int(next(g for g in m.groups() if g))
    p = _POINTS.search(texte[m.end():])
    return {"number": numero, "points": _entier(p.group(1)) if p else None}


def hotm_champs_ecran(texte_titre, texte_porte, score_total=None):
    """Champs à fusionner dans la run HOTM.
    Retourne (champs, alertes). `alertes` est une liste de textes pour `notes` ;
    s'il y en a, la run doit passer en confidence « a_verifier »."""
    champs = {"gate": lire_porte(texte_porte), "hunter_mode": lire_mode(texte_titre)}
    alertes = []
    if champs["gate"] is None:
        alertes.append("porte HOTM illisible")
    elif champs["gate"]["points"] is None:
        alertes.append("points de la porte illisibles")
    elif score_total is not None and champs["gate"]["points"] != score_total:
        # Les points de la porte sont le record précédent ou le score selon l'écran : ne pas
        # corriger le score, seulement signaler (ex. 94 600 sur l'écran de composition = 이번 기록).
        alertes.append(
            f"points de la porte ({champs['gate']['points']}) différents du score ({score_total})"
        )
    if champs["hunter_mode"] is None:
        alertes.append("titre du mode HOTM illisible")
    return champs, alertes
