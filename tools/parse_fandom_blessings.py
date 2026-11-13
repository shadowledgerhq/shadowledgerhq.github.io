"""Lit la page Blessing Stones du wiki Fandom et écrit data/db/blessings.json.
Usage : python3 -I tools/parse_fandom_blessings.py <sortie.json>"""
import json, re, sys, urllib.request
URL = "https://solo-leveling-arise.fandom.com/api.php?action=parse&page=Blessing_Stones&prop=wikitext|revid&format=json"
SRC = "https://solo-leveling-arise.fandom.com/wiki/Blessing_Stones"
RAR = ["rare", "heroic", "legendary", "transcendent"]

def clean(s):
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s or "")
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|", "", s)
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s).replace("{{", "").replace("}}", "")
    s = re.sub(r"</?div>", " ", s)
    return re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", s)).strip()

def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

t = json.load(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "curl/8"})))["parse"]
txt, rev = t["wikitext"]["*"], t["revid"]
sec = txt[txt.find("== List of Blessing Stones =="):]
blocks = re.split(r"^!\s*colspan=\"?\d+\"?\s*\|\s*([^\n]+?)\s*$", sec, flags=re.M)
out = []
for cat, body in zip(blocks[1::2], blocks[2::2]):
    category = re.sub(r"\s*Blessing Stones\s*$", "", clean(cat)).strip().lower()
    for row in re.split(r"\n\|-\s*", body):
        cells = [c for c in re.split(r"\n\|", "\n" + row.strip()) if c.strip()]
        cells = [c.strip().lstrip("|").strip() for c in cells]
        if len(cells) < 3 or "File:" not in cells[0]: continue
        name = clean(re.sub(r"^[^|\[]*align=[^|]*\|", "", re.sub(r"\[\[File:[^\]]*\]\]", "", cells[0])))
        eff = cells[2]
        vals = [[float(x) for x in re.split(r"-", m.group(1))] for m in re.finditer(r"Data\|(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?){3})\b", eff)]
        out.append({"id": slug(name), "name": {"fr": "", "en": name, "ko": ""}, "category": category, "rarity": RAR,
                    "text": {"fr": "", "en": clean(eff)}, "flavor_en": clean(cells[1]), "effects": [], "conditions": [],
                    "values_by_level": {"values_by_rarity_rare_heroic_legendary_transcendent": vals},
                    "icon": None, "source": SRC, "wiki_revid": rev, "verified_at": "2026-11-13", "game_version": None,
                    "notes": "Texte EN du wiki Fandom (CC BY-SA), non vérifié en jeu. Valeurs Rare-Heroic-Legendary-Transcendent. Le wiki ne reflète pas les rééquilibrages de juin/octobre ni les pierres ajoutées le 17/09 (cf. patches.json)."})
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
import collections
print(len(out), collections.Counter(o["category"] for o in out), "sans valeurs:", [o["id"] for o in out if not o["values_by_level"]["values_by_rarity_rare_heroic_legendary_transcendent"]], "restes:", sum(1 for o in out if "{{" in json.dumps(o)))
