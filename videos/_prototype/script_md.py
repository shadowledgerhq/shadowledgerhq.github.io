"""Écrit script.md (minutage, storyboard, texte FR/EN, sources) à partir de video.json."""
import json, sys
v = json.load(open(sys.argv[1], encoding="utf-8"))
L = lambda x, l: x.get(l, "") if isinstance(x, dict) else (x or "")
out = [f"# Script et storyboard — {v['mode'].upper()} {v['week']} ({v['boss']}, {v['season_week']}) — {v['status']}", "",
       "Généré depuis `video.json` (source unique ; ne pas modifier ce fichier à la main). Sans voix : la narration s'affiche en sous-titres.", ""]
t0 = 0.0
for i, s in enumerate(v["scenes"], 1):
    t1 = t0 + s["duration"]
    out += [f"## {i}. {s['id']} — {t0:.0f}-{t1:.0f} s ({s['duration']} s, type `{s['type']}`)", "",
            f"**Storyboard** : {s['storyboard']}", ""]
    if s.get("narration"):
        out += ["| t | FR | EN |", "| --- | --- | --- |"]
        out += [f"| {n['t']:.1f} | {n['fr']} | {n['en']} |" for n in s["narration"]]
        out.append("")
    if s.get("points"):
        out += ["Texte à l'écran :", ""] + [f"- {L(p,'fr')} / *{L(p,'en')}*" for p in s["points"]] + [""]
    if s.get("estimates"):
        out += [f"Estimations : {', '.join(s['estimates'])}", ""]
    if s.get("sources"):
        out += ["Sources : " + " ; ".join(s["sources"]), ""]
    t0 = t1
out.append(f"Durée totale : {t0:.0f} s.")
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(out) + "\n")
