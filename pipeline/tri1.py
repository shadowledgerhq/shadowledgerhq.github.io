"""Tri 1 : score provisoire dans le texte (titre, description, sous-titres).
Référence : docs/SPEC_ETAPE1.md §2. Tout score trouvé ici est provisoire :
exact false, confidence a_verifier ; la vidéo continue aux tris suivants."""
import re
import unicodedata

from hotm_ecran import lire_porte
from scores import NON_GERE, degats_gb, extraire
from bot_saison import NOTE_CHALLENGE, lire_saison_semaine, titre_challenge
from semaine import bornes, parse_iso, semaine_de

SOURCES_TEXTE = ("titre", "description", "sous-titres")


def lecture_vide(meta, mode):
    """Squelette d'une entrée de data/runs/<semaine>/_lectures.json."""
    return {
        "video_id": meta["video_id"],
        "channel_id": meta["channel_id"],
        "channel_title": meta.get("channel_title", ""),
        "published_at": meta["published_at"],
        "lang": meta.get("lang"),
        "mode": mode,
        "regles": None,         # v8 : version des règles du tri 1 qui a produit la lecture (config.tri1_version)
        "bot_season_week": None,  # v9 : `S20-4` lu dans le titre (BOT), contrôle de semaine au classement
        "player_ingame": None,  # v4 : pseudo en jeu (BOT, bandeau du bas), information seulement
        "damage": None,         # v5 : GB, `Final Score` (arrondi si lu sur le Personal Record)
        "gate": None,
        "hunter_mode": None,
        "t": None,
        "stage": None,
        "team": None,
        "score": None,
        "score_source": None,
        "exact": False,
        "confidence": "a_verifier",
        "detail": {},
        "notes": [],
    }


def _mot_entier(mot, texte):
    if mot.isascii():
        return re.search(rf"(?<![a-z0-9]){re.escape(mot)}(?![a-z0-9])", texte) is not None
    return mot in texte


def notes_alerte_reset(meta, config):
    """v8 §2.2 : vidéo publiée moins de `config.reset_alerte_heures` (3) après le reset de sa semaine : note
    d'alerte, sans effet sur le statut. Retourne [] ou la note."""
    heures = config.get("reset_alerte_heures")
    if not heures or not meta.get("published_at"):
        return []
    ecart = parse_iso(meta["published_at"]) - bornes(semaine_de(meta["published_at"]))[0]
    return ["publiée juste après le reset : semaine précédente ?"] if ecart.total_seconds() < heures * 3600 else []


def lectures_texte(meta, textes, config):
    """`textes` : liste de (source, texte) dans l'ordre de priorité.
    Retourne (lectures, modes_non_geres). Une lecture au plus par mode : la première
    source qui donne un score ; les autres valeurs vont dans `notes`."""
    lectures, non_geres = [], []
    for mode in meta.get("mode_guess", []):
        lec = None
        for source, texte in textes:
            r = extraire(texte, mode, config, source)
            if r == NON_GERE:
                non_geres.append(mode)
                break
            if not r:
                continue
            if lec is None:
                lec = lecture_vide(meta, mode)
                lec.update(score=r["valeur"], score_source=source, regles=config.get("tri1_version"))
                lec["notes"] += notes_alerte_reset(meta, config)
                if mode == "gb":  # v8 : dégâts lus dans le même texte (arrondis : exact false)
                    lec["damage"] = degats_gb(texte, config)
                    if lec["damage"] is not None:
                        lec["detail"]["damage_exact"] = False
                lec["notes"].append(f"score provisoire ({source}) : {r['brut']}")
                if r["autres"]:
                    lec["notes"].append("autres candidats : " + ", ".join(r["autres"]))
                if r.get("semaine_passee"):
                    lec["notes"].append("semaine précédente ?")
                if mode == "hotm":  # v3 : porte d'après le titre (l'écran prime dès qu'il est lu)
                    porte = lire_porte(meta.get("title") or "")
                    lec["gate"] = porte["number"] if porte else None
                if mode == "bot":  # v9-v10 : semaine S<n>-<w> du titre ; ancien mode challenge
                    lec["bot_season_week"] = lire_saison_semaine(meta.get("title"), config)
                    if titre_challenge(meta.get("title"), config):
                        lec["notes"].append(NOTE_CHALLENGE)
            elif r["valeur"] != lec["score"]:
                lec["notes"].append(f"{source} : {r['brut']}")
        if lec:
            lectures.append(lec)
    return lectures, sorted(set(non_geres))


def remplacer_lectures(toutes, video_id, nouvelles, sources):
    """Remplace les lectures de `video_id` issues de `sources` (idempotent)."""
    gardees = [l for l in toutes if not (l["video_id"] == video_id and l["score_source"] in sources)]
    return gardees + nouvelles


_HORODATAGE = re.compile(r"\d{1,2}(?::\d{2}){1,2}")


def candidats_en_chapitres(lec):
    """v9 (relecture sans clé) : règle des chapitres (§2.2, ≥ 2 horodatages croissants) appliquée aux
    candidats déjà stockés dans `notes` d'une lecture de description (score + « autres candidats »)."""
    brut = []
    for n in lec.get("notes", []):
        if n.startswith("score provisoire (description) : "):
            brut.append(n.split(" : ", 1)[1])
        elif n.startswith("autres candidats : "):
            brut += n.split(" : ", 1)[1].split(", ")
    secondes = []
    for b in brut:
        if _HORODATAGE.fullmatch(b.strip()):
            t = [int(x) for x in b.strip().split(":")]
            secondes.append(sum(v * 60 ** i for i, v in enumerate(reversed(t))))
    return len(secondes) >= 2 and secondes == sorted(secondes) and len(set(secondes)) == len(secondes)


NOTE_HORS_SUJET = "actualités probables (titre)"


def _sans_accents_minuscules(texte):
    """Minuscules, sans signes diacritiques (NFD sans les marques, puis NFC : le coréen reste composé)."""
    nfd = unicodedata.normalize("NFD", texte or "")
    return unicodedata.normalize("NFC", "".join(c for c in nfd if unicodedata.category(c) != "Mn")).lower()


def mot_hors_sujet(titre, config):
    """v37 §2.3 : premier mot de `config.hors_sujet_mots.mots` trouvé dans le titre (sans accents ni casse ; mot entier pour les mots
    latins, sous-chaîne pour le coréen, le japonais et le chinois), ou None."""
    t = _sans_accents_minuscules(titre)
    for mot in (config.get("hors_sujet_mots") or {}).get("mots") or []:
        m = _sans_accents_minuscules(mot)
        if m and _mot_entier(m, t):
            return mot
    return None


def score_dans_le_texte(lectures, video_id):
    """Une lecture de la vidéo issue du titre, de la description ou des sous-titres porte un score."""
    return any(l.get("video_id") == video_id and l.get("score") is not None and l.get("score_source") in SOURCES_TEXTE for l in lectures)


def titre_hors_sujet_probable(meta, lectures, config):
    """v37 §2.3 : titre avec un mot de `hors_sujet_mots` ET aucun score lu dans le texte. Marquage seulement."""
    return bool(mot_hors_sujet(meta.get("title"), config)) and not score_dans_le_texte(lectures, meta.get("video_id"))


def marquer_hors_sujet(entree, meta, lectures, config):
    """Pose ou retire `entree["hors_sujet_probable"]` (entrée de processed.json) et sa note. Une vidéo dont le tri 3 a vu un écran de jeu
    (`pc.ecran_jeu`) n'est plus jamais marquée. Retourne True si le marquage a changé."""
    vu = bool((entree.get("pc") or {}).get("ecran_jeu"))
    marque = not vu and entree.get("status") == "en_cours" and titre_hors_sujet_probable(meta, lectures, config)
    avant = bool(entree.get("hors_sujet_probable"))
    notes = [n for n in entree.get("notes", []) if n != NOTE_HORS_SUJET]
    if marque:
        entree["hors_sujet_probable"] = True
        notes.append(NOTE_HORS_SUJET)
    else:
        entree.pop("hors_sujet_probable", None)
    if notes:
        entree["notes"] = notes
    else:
        entree.pop("notes", None)
    return marque != avant


def marquer_hors_sujet_semaine(processed, videos, lectures, week, config):
    """Applique `marquer_hors_sujet` à toutes les vidéos de la semaine ; retourne le nombre de marquages changés."""
    return sum(marquer_hors_sujet(p, videos[v], lectures, config) for v, p in processed.items()
               if p.get("week") == week and v in videos)
