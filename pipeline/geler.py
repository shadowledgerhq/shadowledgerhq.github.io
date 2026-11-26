"""Gèle une semaine terminée à la demande (décision d'Alexis, 26/11/2026 : semaine 2026-11-19).

Même opérations que le passage `weekly` quand `pc.geler` est vrai (pc.py) : recalcul du classement, vidéos sans score après le tri 4
-> `pas_de_score`, lignes provisoires annotées « non vérifié », `_meta.json` `frozen: true`. Sans lecture de vidéo, sans git.
Usage : python3 pipeline/geler.py AAAA-MM-JJ [--maintenant ISO]
Refuse : semaine courante, semaine déjà gelée, semaine dont toutes les lignes sont provisoires (SPEC_ETAPE1 §6)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classement
import pc
from donnees import Donnees, charger_config
from semaine import PARIS, id_semaine, iso_utc, maintenant, parse_iso


def geler(week, d=None, config=None, instant=None):
    d, config, instant = d or Donnees(), config or charger_config(), instant or maintenant()
    jour = instant.astimezone(PARIS).date().isoformat()
    if week == id_semaine(instant):
        return f"refusé : {week} est la semaine courante"
    meta = pc.ouvrir_semaine(d, week)
    if meta.get("frozen"):
        return f"déjà gelée le {meta.get('frozen_at')}"
    res = classement.calculer(week, d, config, instant)
    lignes, provisoires = sum(res["fichiers"].values()), len(res["a_verifier"])
    if lignes and provisoires == lignes:
        return f"refusé : toutes les lignes de {week} sont provisoires (SPEC_ETAPE1 §6)"
    n = pc.rejeter_sans_score(d, week, jour)
    pc.annoter_non_verifies(d, week)
    meta["frozen"], meta["frozen_at"] = True, iso_utc(instant)
    d.ecrire(f"runs/{week}/_meta.json", meta)
    classement.calculer(week, d, config, instant)
    return f"{week} gelée ({lignes} ligne(s), {provisoires} provisoire(s) « non vérifié », {n} vidéo(s) rejetée(s) pas_de_score)"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("semaine")
    ap.add_argument("--maintenant")
    a = ap.parse_args()
    print(geler(a.semaine, instant=parse_iso(a.maintenant) if a.maintenant else None))
