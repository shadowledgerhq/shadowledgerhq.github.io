"""Semaine de jeu : de jeudi 01:00 (Europe/Paris) au jeudi suivant 01:00 exclu.
Référence : docs/SPEC_ETAPE1.md §0, §1.1. Toujours zoneinfo, jamais un décalage fixe."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
JOUR_RESET, HEURE_RESET = 3, 1  # jeudi, 01:00


def maintenant():
    return datetime.now(timezone.utc)


def debut_semaine(instant):
    """Dernier jeudi 01:00 Paris <= instant, en UTC."""
    local = instant.astimezone(PARIS)
    jour = local.date() - timedelta(days=(local.weekday() - JOUR_RESET) % 7)
    debut = datetime(jour.year, jour.month, jour.day, HEURE_RESET, tzinfo=PARIS)
    if debut > local:
        jour -= timedelta(days=7)
        debut = datetime(jour.year, jour.month, jour.day, HEURE_RESET, tzinfo=PARIS)
    return debut.astimezone(timezone.utc)


def id_semaine(instant):
    """Identifiant AAAA-MM-JJ = date (Paris) du jeudi de début."""
    return debut_semaine(instant).astimezone(PARIS).date().isoformat()


def bornes(week):
    """(debut_utc, fin_utc) de la semaine `week` (AAAA-MM-JJ)."""
    a, m, j = map(int, week.split("-"))
    debut = datetime(a, m, j, HEURE_RESET, tzinfo=PARIS)
    suivant = debut.date() + timedelta(days=7)
    fin = datetime(suivant.year, suivant.month, suivant.day, HEURE_RESET, tzinfo=PARIS)
    return debut.astimezone(timezone.utc), fin.astimezone(timezone.utc)


def semaine_precedente(week):
    a, m, j = map(int, week.split("-"))
    return (datetime(a, m, j) - timedelta(days=7)).date().isoformat()


def semaine_de(publie_utc):
    """Semaine d'une date de publication (datetime aware ou ISO)."""
    return id_semaine(parse_iso(publie_utc))


def parse_iso(s):
    if isinstance(s, datetime):
        return s
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso_utc(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_paris(s):
    return parse_iso(s).astimezone(PARIS).isoformat(timespec="seconds")


def dans_creneau(instant, debut_hhmm, fin_hhmm, jour=None):
    """Heure de Paris dans [debut, fin] (et jour de semaine si donné) ?"""
    local = instant.astimezone(PARIS)
    if jour is not None and local.weekday() != jour:
        return False
    hm = local.strftime("%H:%M")
    return debut_hhmm <= hm <= fin_hhmm
