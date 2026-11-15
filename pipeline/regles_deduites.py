"""Éléments autorisés déduits des écrans (SPEC_ETAPE1 v24 §4.5) : `data/rules/<semaine>.json`, jamais saisi à la main.

Un élément (`sjw`, `successor`) est `true` dès qu'UNE run sûre de la semaine le montre à l'écran ; `false` seulement si au moins
5 runs sûres de 5 chaînes différentes le montrent absent (note « déduit, à vérifier ») ; sinon rien n'est écrit (inconnu).
Preuves lues (lectures `confidence: sur` ; builds pour BOT et HOTM) :
  POC  : ligne SJW et ligne successeur de l'écran RESULT (`detail.sjw`, `detail.successor`) ;
  GB   : `Player's Score` (SJW) et ligne `Successor Score` (`detail.player_score`, `detail.successeur_present`) ;
  BOT  : équipement de SJW reconnu dans le build (armes, artefacts ou noyaux du bandeau de gauche) ;
  HOTM : composition : `hunter_mode` false + SJW reconnu = SJW présent ; `hunter_mode` true = sous-mode sans SJW.
Un bloc garde sa source d'origine ; le calcul est ajouté dans `bloc.deduit` (source « écrans », video_ids, date).
Les anciens noms `bot_season` / `bot_challenge` sont migrés vers `bot` (v10 : un seul classement BOT)."""
from pathlib import Path

MODES = ("poc", "bot", "gb", "hotm")
ELEMENTS = ("sjw", "successor")
MIN_RUNS, MIN_CHAINES = 5, 5
NOTE_FAUX = "déduit, à vérifier"
NOTE_CHALLENGE = ("relevé du 05/11 rangé en challenge (mode retiré en mai 2026) : à vérifier, "
                  "peut-être un boss joué en mode chasseur")


def migrer(regles):
    """`bot_season` / `bot_challenge` -> `bot` (sans écraser un bloc `bot` existant). Retourne True si modifié."""
    modes = regles.setdefault("modes", {})
    change = False
    for ancien in ("bot_season", "bot_challenge"):
        if ancien not in modes:
            continue
        bloc = modes.pop(ancien)
        change = True
        if bloc and not modes.get("bot"):
            if ancien == "bot_challenge":
                bloc = {**bloc, "notes": NOTE_CHALLENGE}
            modes["bot"] = bloc
    ordre = {m: modes.get(m) for m in MODES}        # ordre fixe poc, bot, gb, hotm ; autres clés à la suite
    ordre.update({k: v for k, v in modes.items() if k not in ordre})
    if list(ordre) != list(modes):
        change = True
    modes.clear()
    modes.update(ordre)
    return change


def _vide():
    return {m: {e: {"vu": {}, "absent": {}} for e in ELEMENTS} for m in MODES}


def _noter(preuves, mode, element, present, video_id, chaine):
    cle = "vu" if present else "absent"
    preuves[mode][element][cle][video_id] = chaine


def preuves_lectures(lectures):
    """Preuves tirées des lectures d'écran sûres (POC, GB)."""
    p = _vide()
    for l in lectures:
        if l.get("confidence") != "sur" or l.get("score") is None:
            continue
        d, vid, chaine = l.get("detail") or {}, l.get("video_id"), l.get("channel_id")
        if l.get("mode") == "poc":
            if d.get("sjw") is not None:
                _noter(p, "poc", "sjw", True, vid, chaine)
            if d.get("successor") is not None:
                _noter(p, "poc", "successor", True, vid, chaine)
        elif l.get("mode") == "gb" and l.get("score_source") in ("debut-fin", "video-complete") and d.get("player_score") is not None:
            _noter(p, "gb", "sjw", True, vid, chaine)
            if d.get("successeur_present"):
                _noter(p, "gb", "successor", True, vid, chaine)
            elif d.get("hunter_ranks_lus") == 6:         # écran entièrement lu sans ligne successeur
                _noter(p, "gb", "successor", False, vid, chaine)
    return p


def preuves_builds(builds, preuves=None):
    """Preuves tirées des builds (BOT, HOTM) : seulement les builds partiels ou complets."""
    p = preuves or _vide()
    for b in builds:
        if b.get("status") not in ("build_partiel", "build_complet"):
            continue
        mode, vid, chaine = b.get("mode"), b.get("video_id"), b.get("channel_id")
        s = b.get("sjw") or {}
        equipe = any(x.get("id") for x in s.get("weapons") or []) or any(x.get("set_id") for x in s.get("artifacts") or []) \
            or any(x.get("id") for x in s.get("cores") or [])
        if mode == "bot" and equipe:
            _noter(p, "bot", "sjw", True, vid, chaine)
        elif mode == "hotm":
            if b.get("hunter_mode") is True:
                _noter(p, "hotm", "sjw", False, vid, chaine)
            elif b.get("hunter_mode") is False and equipe:
                _noter(p, "hotm", "sjw", True, vid, chaine)
    return p


def valeurs(preuves):
    """{mode: {element: (valeur, [video_id])}} : true dès 1 preuve ; false si ≥ 5 runs de 5 chaînes et aucune preuve contraire."""
    sortie = {}
    for mode, els in preuves.items():
        for el, x in els.items():
            if x["vu"]:
                sortie.setdefault(mode, {})[el] = (True, sorted(x["vu"]))
            elif len(x["absent"]) >= MIN_RUNS and len(set(x["absent"].values())) >= MIN_CHAINES:
                sortie.setdefault(mode, {})[el] = (False, sorted(x["absent"]))
    return sortie


def appliquer(regles, valeurs_deduites, date):
    """Écrit les valeurs déduites dans `regles` (dict d'un fichier `data/rules/<semaine>.json`). Retourne True si modifié.
    Un `true` déduit remplace `null` ou `false` ; un `false` déduit ne remplace jamais une valeur déjà connue."""
    modes = regles.setdefault("modes", {})
    change = migrer(regles)
    for mode, els in valeurs_deduites.items():
        bloc = modes.get(mode)
        nouveau = bloc is None
        bloc = dict(bloc or {})
        deduit = dict(bloc.get("deduit") or {})
        ancien_elements = dict(deduit.get("elements") or {})
        vids = set(deduit.get("video_ids") or [])
        notes = []
        for el, (val, ids) in els.items():
            actuel = bloc.get(el)
            if val is True and actuel is not True:
                bloc[el] = True
                ancien_elements[el] = True
                vids |= set(ids)
            elif val is False and actuel is None:
                bloc[el] = False
                ancien_elements[el] = False
                vids |= set(ids)
                notes.append(f"{el} : {NOTE_FAUX}")
            elif val is True and actuel is True and ancien_elements.get(el) is True:
                vids |= set(ids)
        if not ancien_elements and not notes:
            continue
        deduit.update(source="écrans", video_ids=sorted(vids), elements=ancien_elements)
        if deduit != (bloc.get("deduit") or {}) or nouveau:
            deduit["date"] = date
        else:
            deduit["date"] = (bloc.get("deduit") or {}).get("date", date)
        if notes:
            bloc["notes_deduit"] = sorted(set((bloc.get("notes_deduit") or "").split(" ; ") if bloc.get("notes_deduit") else []) | set(notes))
            bloc["notes_deduit"] = " ; ".join(bloc["notes_deduit"])
        bloc["deduit"] = deduit
        if nouveau:
            bloc["source"] = "écrans"
        if modes.get(mode) != bloc:
            modes[mode] = bloc
            change = True
    return change


def mettre_a_jour(d, week, lectures, date):
    """Point d'entrée du classement : lit `data/rules/<week>.json` (le crée si des preuves existent), applique la déduction,
    écrit seulement si quelque chose change. `d` = `donnees.Donnees`. Retourne True si le fichier a changé."""
    chemin = f"rules/{week}.json"
    regles = d.lire(chemin, None)
    existant = regles is not None
    preuves = preuves_lectures(lectures)
    builds = []
    for mode in ("bot", "hotm"):
        dossier = Path(d.data) / "builds" / week / mode
        for f in sorted(dossier.glob("*.json")) if dossier.exists() else []:
            try:
                builds.append(d.lire(f"builds/{week}/{mode}/{f.name}", {}))
            except Exception:
                continue
    preuves_builds(builds, preuves)
    val = valeurs(preuves)
    if regles is None:
        if not val:
            return False
        regles = {"week": week, "modes": {m: None for m in MODES}, "verified_at": date,
                  "notes": "null = règles du mode pas encore fournies ; blocs déduits des écrans (SPEC v24)."}
    change = appliquer(regles, val, date)
    if change or not existant:
        d.ecrire(chemin, regles)
        return True
    return False
