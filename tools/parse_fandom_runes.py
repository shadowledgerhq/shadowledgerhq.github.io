"""Lit la page Runes du wiki Fandom (runes de compétences de Sung Jin Woo) et écrit data/db/sjw_skills.json.
Usage : python3 -I tools/parse_fandom_runes.py <sortie.json>"""
import json, re, sys, urllib.request

URL = "https://solo-leveling-arise.fandom.com/api.php?action=parse&page=Runes&prop=wikitext|revid&format=json"
SRC = "https://solo-leveling-arise.fandom.com/wiki/Runes"
RAR = ["rare", "heroic", "legendary", "transcendent"]

def clean(s):
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s or "")
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|", "", s)
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s).replace("{{", "").replace("}}", "")
    return re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", s)).strip()

def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

def params(text):
    d = {}
    for m in re.finditer(r"^\|\s*([A-Za-z0-9_]+)\s*=(.*?)(?=^\|\s*[A-Za-z0-9_]+\s*=|\Z)", text, re.S | re.M):
        d.setdefault(m.group(1).lower(), m.group(2).strip())
    return d

def quad(s, label=None):
    pat = (label + r":[^{]*\{\{[^|}]*\|Type=" if label else "") + r"Data\|([\d.]+(?:-[\d.]+){3})"
    m = re.search(pat, s)
    return [float(x) for x in m.group(1).split("-")] if m else None

t = json.load(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "curl/8"})))["parse"]
txt, rev = t["wikitext"]["*"], t["revid"]
sec = txt[txt.find("==Runes List=="):]
parts = re.split(r"====<span[^>]*>([^<]*)</span>====", sec)
out = []
for h, body in zip(parts[1::2], parts[2::2]):
    skill = re.sub(r"\s*Runes\s*$", "", h).strip()
    sid = slug(skill)
    p = params(body)
    runes = []
    for n in range(1, 5):
        nm = p.get(f"rune{n}_name")
        if not nm: continue
        eff = p.get(f"rune{n}", "")
        cd = re.search(r"Cooldown: \{\{[^|]*\|[^|]*\|([\d.]+)", eff)
        mp = re.search(r"MP Consumption: \{\{[^|]*\|[^|]*\|([\d.\-]+)", eff)
        el = re.search(r"Deals \{\{[^|]*\|Type=(Fire|Water|Wind|Light|Dark)", eff)
        rid = f"{sid}--{slug(clean(nm))}"
        runes.append(rid)
        out.append({"id": rid, "kind": "rune", "parent_skill": sid, "name": {"fr": "", "en": clean(nm), "ko": ""}, "rarity": RAR,
                    "type": None, "element": el.group(1).lower() if el else None,
                    "cooldown": float(cd.group(1)) if cd else None, "mp_cost": mp.group(1) if mp else None,
                    "text": {"fr": "", "en": clean(p.get(f"rune{n}_des", ""))}, "effects": [], "effects_text_en": clean(eff),
                    "values_by_level": {"damage_pct_of_attack_by_rarity": quad(eff, "Damage")},
                    "icon": None, "source": SRC, "wiki_revid": rev, "verified_at": "2026-11-13", "game_version": None,
                    "notes": "Valeurs au niveau min., par rareté Rare-Heroic-Legendary-Transcendent. Forme (rond/losange/triangle/pentagone) non indiquée par le wiki."})
    out.append({"id": sid, "kind": "skill", "name": {"fr": "", "en": skill, "ko": ""}, "rarity": None, "type": None, "runes": runes,
                "cooldown": None, "effects": [], "values_by_level": {}, "icon": None, "source": SRC, "wiki_revid": rev,
                "verified_at": "2026-11-13", "game_version": None,
                "notes": "Compétence de Sung Jin Woo connue seulement par ses runes sur le wiki (type basique/QTE/ultime, niveau de base : non indiqués)."})
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
print(sum(1 for o in out if o["kind"] == "skill"), "compétences,", sum(1 for o in out if o["kind"] == "rune"), "runes ;",
      "sans valeurs:", [o["id"] for o in out if o["kind"] == "rune" and not o["values_by_level"]["damage_pct_of_attack_by_rarity"]], "; restes:", sum(1 for o in out if "{{" in json.dumps(o)))
