"""Classe les `balance_changes` en statut a_verifier : ajoute `verif` selon ce que contient la base.
  db_ancienne_seule : la base a l'ancienne valeur, pas la nouvelle (candidat à appliquer, contexte à lire)
  db_les_deux       : les deux valeurs existent ailleurs dans l'entrée (ambigu, ne rien changer sans lecture)
  db_aucune         : aucune des deux (valeurs structurées/absentes : rien à corriger dans le texte)
  analyse_douteuse  : unité différente ou ligne tronquée (l'ancienne/nouvelle valeur extraite est peut-être fausse)
Usage : python3 tools/classer_a_verifier.py"""
import json, re
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "data" / "db"
motif = lambda v, u: re.compile(r"(?<![\d.\-])" + re.escape(v) + re.escape((" " + u) if u not in ("", "%") else u) + r"(?![\d.\-])")
n = {}
for f in ("hunters", "weapons", "shadows", "artifact_sets", "blessings", "sjw_skills"):
    p = R / f"{f}.json"; d = json.loads(p.read_text(encoding="utf-8")); chg = False
    for e in d:
        blob = json.dumps({k: v for k, v in e.items() if k not in ("balance_history", "values_balance_applied", "balance_changes", "notes")}, ensure_ascii=False)
        for c in e.get("balance_changes", []) or []:
            if c.get("status") != "a_verifier": continue
            co, cn = len(motif(c["old"], c["unit"]).findall(blob)), len(motif(c["new"], c["unit"]).findall(blob))
            douteux = (len(c["line"]) >= 138) or (c["unit"] in ("time", "times") and "%" in c["line"]) or (c["unit"] in ("second", "seconds") and "%" in c["line"].split(c["unit"])[0][-60:] and c["line"].count("%") > 1)
            v = "analyse_douteuse" if douteux else "db_ancienne_seule" if co and not cn else "db_les_deux" if co and cn else "db_aucune"
            if c.get("verif") != v: c["verif"] = v; chg = True
            n[v] = n.get(v, 0) + 1
    if chg: p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(n)
