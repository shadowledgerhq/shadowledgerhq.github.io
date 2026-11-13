"""Compétences et bénédictions de Sung Jin Woo (mode player du HOTM).

sjw.skills = 6 objets {"slot", "id", "level"} ; level = None si aucun niveau affiché
(cas vu : QTE 01). Complétude du mode player : 6 emplacements + 8 bénédictions.
"""
SKILL_SLOTS = ("skill_1", "skill_2", "ultimate", "qte_1", "qte_2", "qte_3")
NB_BLESSINGS = 8
# Slide PowerPoint « Compétences SJW / SJW Skills » : grille 3 + 3.
GRILLE_SLIDE = (SKILL_SLOTS[:3], SKILL_SLOTS[3:])  # haut : compétences, bas : QTE


def verifier_sjw(sjw):
    """Liste de problèmes ; vide = SJW complet. Ne devine rien."""
    pb = []
    skills = sjw.get("skills") or []
    slots = [s.get("slot") for s in skills]
    for slot in SKILL_SLOTS:
        n = slots.count(slot)
        if n == 0:
            pb.append(f"emplacement manquant : {slot}")
        elif n > 1:
            pb.append(f"emplacement en double : {slot}")
    pb += [f"emplacement inconnu : {x}" for x in slots if x not in SKILL_SLOTS]
    for s in skills:
        if not s.get("id"):
            pb.append(f"id manquant : {s.get('slot')}")
        lv = s.get("level")
        if lv is not None and not isinstance(lv, int):
            pb.append(f"niveau invalide : {s.get('slot')}")
    nb = len(sjw.get("blessings") or [])
    if nb != NB_BLESSINGS:
        pb.append(f"bénédictions : {nb}/{NB_BLESSINGS}")
    return pb


def sjw_complet(sjw):
    return not verifier_sjw(sjw)
