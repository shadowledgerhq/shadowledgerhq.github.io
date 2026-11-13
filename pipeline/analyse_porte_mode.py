"""Tableau porte × mode (avec/sans SJW) sur les runs HOTM : tranche l'hypothèse
« le mode dépend de la porte ». Usage : python pipeline/analyse_porte_mode.py [data/runs]
Lit data/runs/*/hotm-gate-*.json (gate = entier) ; ignore les runs sans gate ou hunter_mode lisibles."""
import json
import sys
from collections import Counter
from pathlib import Path

racine = Path(sys.argv[1] if len(sys.argv) > 1 else "data/runs")
c, ignorees = Counter(), 0
for f in sorted(racine.glob("*/hotm-gate-*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        g, m = r.get("gate"), r.get("hunter_mode")
        if not isinstance(g, int) or m is None:
            ignorees += 1
            continue
        c[(f.parent.name, g, m)] += 1

print("semaine | porte | mode | runs")
for (sem, porte, mode), n in sorted(c.items()):
    print(f"{sem} | {porte} | {'sans SJW' if mode else 'avec SJW'} | {n}")
modes_par_porte = {}
for (_, porte, mode), n in c.items():
    modes_par_porte.setdefault(porte, set()).add(mode)
if modes_par_porte:
    lies = all(len(v) == 1 for v in modes_par_porte.values())
    print("\nChaque porte n'a qu'un seul mode dans les données." if lies
          else "\nUne même porte apparaît dans les deux modes : le mode ne dépend pas de la porte seule.")
    print("(Échantillon : " + str(sum(c.values())) + " runs, " + str(ignorees) + " ignorées. À lire avec prudence si petit.)")
else:
    print("Aucune run HOTM avec gate et hunter_mode.")
