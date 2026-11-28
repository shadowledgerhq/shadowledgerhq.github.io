"""Planification des relances du PC (Planificateur de tâches Windows) et veille — extrait de pc.py le 28/11 sans changement de comportement.
`pc.py` ré-exporte ces noms (`pc.programmer_relance`, `pc.relance_manquee`, `pc.programmer_report`, `pc.empecher_veille`…)."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from donnees import RACINE
from semaine import PARIS


FICHIER_RELANCE = RACINE / "logs" / "relance.json"
NOM_TACHE_RELANCE = "ShadowLedger PC relance"


def planifier_windows(quand, commande_bat, nom=NOM_TACHE_RELANCE):
    """Tâche ponctuelle du Planificateur de tâches (PowerShell, indépendant de la langue de Windows) : `quand` = datetime
    naïf (heure de Paris = heure du PC) ; la tâche lance `lancer_pc.bat daily relance`. Retourne None ou le message d'erreur."""
    if sys.platform != "win32":
        return "planification possible seulement sous Windows"
    bat = str(commande_bat).replace("'", "''")
    ps = (f"$a = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c \"{bat}\" daily relance'; "
          f"$t = New-ScheduledTaskTrigger -Once -At ([datetime]'{quand:%Y-%m-%dT%H:%M:%S}'); "
          "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
          "-MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 6); "
          f"Register-ScheduledTask -TaskName '{nom}' -Force -Action $a -Trigger $t -Settings $s | Out-Null")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:]


def programmer_relance(instant, jour, planifier=None, fichier=None, delai_h=2):
    """Anti-bot : une seule relance par soir (`jour` = date de Paris du passage), 2 h plus tard. Retourne un texte pour le
    rapport : heure de la relance, ou la raison pour laquelle il n'y en a pas."""
    fichier = Path(fichier or FICHIER_RELANCE)
    try:
        etat = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    except (OSError, ValueError):
        etat = {}
    # BOITE 27/11 (Tâche planifiée) : seule une relance programmée par un passage du SOIR (dès 18:00 Paris) compte dans la limite ;
    # celle du weekly de 01:15 (relance 03:15) ne doit pas empêcher la relance du soir du même jour.
    deja = etat.get("jour") if etat.get("soir") else None
    soir = instant.astimezone(PARIS).hour >= 18
    if deja == jour:
        return "aucune (une relance anti-bot a déjà été programmée aujourd'hui) : prochain passage normal"
    quand = (instant.astimezone(PARIS) + timedelta(hours=delai_h)).replace(tzinfo=None, second=0, microsecond=0)
    err = (planifier or planifier_windows)(quand, RACINE / "pipeline" / "pc" / "lancer_pc.bat")
    if err:
        return f"non programmée ({err})"
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(json.dumps({"jour": jour, "a": quand.isoformat(), "soir": soir}), encoding="utf-8")
    return f"{quand:%d/%m/%Y %H:%M} (relance anti-bot, 2 h après le passage ; une par jour)"


def relance_manquee(instant, fichiers, max_h=2):
    """Relance (tâche ponctuelle) lancée trop longtemps après son heure (PC éteint, relance de nuit) : texte du bloc « Relance annulée », sinon None.
    L'heure prévue = la plus récente des heures programmées (`a`, heure de Paris) antérieure à l'instant, dans `relance.json` / `report.json`."""
    maintenant_ = instant.astimezone(PARIS).replace(tzinfo=None)
    prevues = []
    for f in fichiers:
        try:
            a = datetime.fromisoformat(json.loads(Path(f).read_text(encoding="utf-8")).get("a"))
        except (OSError, ValueError, TypeError):
            continue
        if a <= maintenant_:
            prevues.append(a)
    if not prevues:
        return None
    a = max(prevues)
    if maintenant_ - a > timedelta(hours=max_h):
        return f"prévue à {a:%d/%m %H:%M}, lancée à {maintenant_:%d/%m %H:%M} (plus de {max_h} h de retard)"
    return None


FICHIER_REPORT = RACINE / "logs" / "report.json"


def programmer_report(instant, jour, planifier=None, fichier=None, delai_min=30, maximum=2):
    """v42 : passage daily lancé avant le passage GitHub du jour : relance 30 min plus tard, 2 fois au plus par soir. Retourne le texte du bloc."""
    fichier = Path(fichier or FICHIER_REPORT)
    try:
        etat = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    except (OSError, ValueError):
        etat = {}
    n = etat.get("n", 0) if etat.get("jour") == jour else 0
    if n >= maximum:
        return f"aucune ({maximum} relances déjà programmées ce soir) : prochain passage normal"
    quand = (instant.astimezone(PARIS) + timedelta(minutes=delai_min)).replace(tzinfo=None, second=0, microsecond=0)
    err = (planifier or planifier_windows)(quand, RACINE / "pipeline" / "pc" / "lancer_pc.bat")
    if err:
        return f"non programmée ({err})"
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(json.dumps({"jour": jour, "n": n + 1, "a": quand.isoformat()}), encoding="utf-8")
    return f"{quand:%d/%m/%Y %H:%M} (relance {n + 1} sur {maximum})"


def empecher_veille():
    """28/11 : le passage du 27/11 a duré 666 min (PC en veille au milieu d'une vidéo : l'horloge continue, le budget de 100 min ne
    s'applique qu'au réveil). Windows : demande au système de ne pas se mettre en veille tant que le processus tourne (l'écran peut
    s'éteindre) ; levée automatiquement à la fin du processus. Sans effet ailleurs. Retourne True si la demande est faite."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        return bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))
    except Exception:
        return False
