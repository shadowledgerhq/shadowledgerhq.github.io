"""Ajoute name.ja et name.ko aux chasseurs d'après la page https://slagate.com/builds affichée en japonais et en coréen
(lecture de page autorisée par Alexis ; format « nom local(nom latin) »). Seuls les chasseurs que slagate a localisés reçoivent un nom.
Usage : python3 -I tools/apply_ja_ko.py <names_ja.json> <names_ko.json>"""
import json, re, sys
norm = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
H = json.load(open("data/db/hunters.json")); idx = {norm(h["name"]["fr"]): h for h in H}
SRC = "https://slagate.com/builds (page affichée en {}) ; lecture de page autorisée par Alexis le 13/11/2026"
res = {}
for lang, f in (("ja", sys.argv[1]), ("ko", sys.argv[2])):
    n = 0
    for t in json.load(open(f)):
        m = re.match(r"^(.+?)\((.+)\)$", t)
        if not m: continue
        h = idx.get(norm(m.group(2)))
        if not h: continue
        h["name"][lang] = m.group(1).strip(); h["name_" + lang + "_source"] = SRC.format("japonais" if lang == "ja" else "coréen"); n += 1
    res[lang] = n
json.dump(H, open("data/db/hunters.json", "w"), ensure_ascii=False, indent=2)
print(res, "sur", len(H), "| sans ja:", [h["id"] for h in H if not h["name"].get("ja")][:80])
