"""Noms JA des armes exclusives de chasseurs : tableau https://gamewith.jp/sololeveling/448453 (arme | rareté | élément | chasseur).
Rapprochement : chasseur (nom JA déjà en base, slagate) + élément + rareté, appliqué seulement si l'arme est unique. Usage : python3 -I tools/apply_ja_weapons.py <gww.md>"""
import re, sys, json
txt = re.sub(r"!\[[^\]]*\]", "", re.sub(r"\(https[^)]*\)", "", open(sys.argv[1]).read()))
EL = {"風": "wind", "光": "light", "闇": "dark", "火": "fire", "水": "water"}
H = json.load(open("data/db/hunters.json")); W = json.load(open("data/db/weapons.json"))
hj = {h["id"]: h["name"].get("ja", "") for h in H}
n = 0; amb = 0
for l in txt.splitlines():
    m = re.match(r"^\| \[([^\]]+)\] \| (SSR|SR|R) \|[^|]*\| (.)属性 \| \[([^\]]+)\] \|", l)
    if not m: continue
    wn, rar, e, hn = m.groups()
    ids = [i for i, j in hj.items() if j and (j.split("(")[0] == hn)]
    if len(ids) != 1: continue
    c = [w for w in W if w.get("hunter_id") == ids[0] and w.get("element") == EL[e] and w.get("rarity") == rar.lower()]
    if len(c) != 1: amb += 1; continue
    c[0]["name"]["ja"] = wn; c[0]["name_ja_source"] = "https://gamewith.jp/sololeveling/448453 (site tiers ; rapproché par chasseur+élément+rareté ; vérifié le 2026-11-15, à vérifier en jeu)"; n += 1
json.dump(W, open("data/db/weapons.json", "w"), ensure_ascii=False, indent=2)
print("ajoutés", n, "ambigus", amb)
