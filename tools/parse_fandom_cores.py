"""Lit la page Cores du wiki Fandom (API MediaWiki) et écrit data/db/cores.json.
Usage : python3 -I tools/parse_fandom_cores.py <sortie.json>"""
import json, re, sys, urllib.request

URL = "https://solo-leveling-arise.fandom.com/api.php?action=parse&page=Cores&prop=wikitext|revid&format=json"
SRC = "https://solo-leveling-arise.fandom.com/wiki/Cores"

def clean(s):
    s = re.sub(r"\{\{(?:Text_Color|Text Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    return re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", s)).strip()

def slug(n):
    return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

t = json.load(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "curl/8"})))["parse"]
rev, txt = t["revid"], t["wikitext"]["*"]
MAIN = {"mind": ["Attack", "Attack (%)"], "body": ["Defense", "Defense (%)"], "spirit": ["HP", "HP (%)"]}
out = []
for slot in ("mind", "body", "spirit"):
    nxt = [txt.find(x, txt.find(f"{slot.capitalize()} Cores") + 10) for x in ("====<span", "==Enhancement==")]
    end = min(x for x in nxt if x > 0)
    sec = txt[txt.find(f"{slot.capitalize()} Cores"):end]
    for name, passive in re.findall(r"\[\[File:[^\]]*\]\]\s*([^\n|]+?)\s*\n\|\s*(.+?)(?=\n\|-|\n\|\})", sec, re.S):
        raw = re.search(r"Type=Data\|(\d+(?:[/-]\d+){2})%?", passive)
        vals = [int(x) for x in re.split(r"[/-]", raw.group(1))] if raw else None
        out.append({"id": slug(name), "name": {"fr": "", "en": name.strip(), "ko": ""},
                    "rarity": ["rare", "heroic", "legendary"], "slot": slot,
                    "main_stat": MAIN[slot], "sub_stat_options": None,
                    "effects": [], "text": {"fr": "", "en": clean(passive)},
                    "values_by_rarity": {"rare_heroic_legendary_first_value": vals},
                    "conditions": ["condition d'activation aléatoire : élément du chasseur (Water/Wind/Fire/Light/Dark) ou Sung Jinwoo"],
                    "values_by_level": {"max_level_wiki": 20, "max_level_notes_netmarble": 25},
                    "icon": None, "source": SRC, "wiki_revid": rev, "verified_at": "2026-11-13", "game_version": None,
                    "notes": "Texte EN du wiki Fandom (CC BY-SA), non vérifié en jeu. Niveau max 20 selon le wiki ; passé à 25 au patch du 17/09/2026 (Netmarble). Valeurs de stats par niveau et FR à compléter."})
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
for c in out: print(c["slot"], c["id"], c["values_by_rarity"])
